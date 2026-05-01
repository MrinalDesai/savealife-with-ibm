"""Facility matching logic based on distance and capability requirements.

This module provides functions for finding the best hospital, pharmacy, and blood bank
for an incident based on location, trauma capability, and other factors.
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Specialty matching helpers
# ---------------------------------------------------------------------------
# Clinically-equivalent or related specialty terms that should match each
# other. This avoids loose substring matching which would incorrectly equate
# 'surgery' with 'neurosurgery' (a hospital with general surgery is NOT a
# substitute for one with neurosurgical capability).
_SPECIALTY_ALIASES = {
    "neurosurgery": {"neurosurgery", "neurology"},
    "neurology": {"neurology", "neurosurgery"},
    "orthopedics": {"orthopedics", "orthopaedics", "ortho"},
    "orthopaedics": {"orthopaedics", "orthopedics", "ortho"},
    "ortho": {"ortho", "orthopedics", "orthopaedics"},
    "trauma": {"trauma"},
    "pediatric": {"pediatric", "pediatrics", "paediatric", "paediatrics"},
    "pediatrics": {"pediatrics", "pediatric", "paediatric", "paediatrics"},
    "paediatric": {"paediatric", "pediatric", "pediatrics", "paediatrics"},
    "paediatrics": {"paediatrics", "pediatric", "pediatrics", "paediatric"},
    "cardiology": {"cardiology", "cardiac"},
    "cardiac": {"cardiac", "cardiology"},
    "burns": {"burns", "burn"},
    "burn": {"burn", "burns"},
}


def _specialties_match(needed: str, hospital_spec: str) -> bool:
    """Whether a needed specialty matches what a hospital offers.

    Uses exact equality first, then alias group membership. Avoids loose
    substring matching (which would incorrectly count 'surgery' as a match
    for 'neurosurgery').
    """
    if needed == hospital_spec:
        return True
    aliases = _SPECIALTY_ALIASES.get(needed, {needed})
    return hospital_spec in aliases


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers between two coordinates.

    Uses the Haversine formula with Earth radius of 6371 km.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in kilometers (float)
    """
    R = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def estimate_eta_minutes(distance_km: float, avg_speed_kmh: float = 30) -> int:
    """Estimate Mumbai-traffic-realistic ETA in minutes.

    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average speed in km/h (default 30 for Mumbai traffic)

    Returns:
        Estimated time in minutes (at least 1, rounded to nearest int)
    """
    if distance_km <= 0:
        return 1

    time_hours = distance_km / avg_speed_kmh
    time_minutes = time_hours * 60

    return max(1, round(time_minutes))


def find_best_hospital(
    triage_result: dict,
    hospitals: list[dict],
    incident_lat: float,
    incident_lon: float,
) -> Optional[dict]:
    """Pick the most appropriate hospital for the incident.

    Filters hospitals by trauma capability and bed availability, then scores
    candidates based on distance, specialty match, beds, and trauma team status.
    Priority-aware scoring: P1 prioritizes closeness + hard specialty requirement,
    P2 balances factors, P3/P4 emphasize closeness.

    Args:
        triage_result: Triage assessment with priority and specialty_needed
        hospitals: List of hospital facility dicts
        incident_lat: Incident latitude
        incident_lon: Incident longitude

    Returns:
        Top hospital dict augmented with distance_km, eta_min, match_score,
        match_reason, and alternatives (list of next 2 best). Returns None
        if no hospitals qualify.
    """
    if not hospitals:
        return None

    priority = triage_result.get("priority", "P2")
    specialty_needed = triage_result.get("specialty_needed", [])

    # Filter by trauma capability based on priority
    candidates = []
    for hospital in hospitals:
        trauma_level = hospital.get("trauma_level")

        if priority == "P1":
            if trauma_level is not None and trauma_level > 1:
                continue
        elif priority in ["P2", "P3"]:
            if trauma_level is not None and trauma_level > 2:
                continue
        # P4 accepts all hospitals

        # Bed filter (skip for P1 — every Level 1 trauma center should accept)
        if priority != "P1":
            beds_available = hospital.get("beds_available")
            if beds_available is not None and beds_available < 1:
                continue

        candidates.append(hospital)

    if not candidates:
        return None

    # P1 hard specialty requirement (uses strict alias matching)
    match_warning = None
    if priority == "P1" and specialty_needed:
        specialty_matched_candidates = []
        for hospital in candidates:
            hospital_specialties = hospital.get("specialties", [])
            if not isinstance(hospital_specialties, list):
                hospital_specialties = []

            has_match = False
            for needed in specialty_needed:
                needed_lower = str(needed).lower()
                for hosp_spec in hospital_specialties:
                    hosp_spec_lower = str(hosp_spec).lower()
                    if _specialties_match(needed_lower, hosp_spec_lower):
                        has_match = True
                        break
                if has_match:
                    break

            if has_match:
                specialty_matched_candidates.append(hospital)

        if not specialty_matched_candidates:
            match_warning = (
                "No specialty-matched hospital available — "
                "routing to closest Level 1 trauma center."
            )
        else:
            candidates = specialty_matched_candidates

    # Score each candidate
    scored_candidates = []
    for hospital in candidates:
        distance_km = haversine_km(incident_lat, incident_lon, hospital["lat"], hospital["lon"])
        eta_min = estimate_eta_minutes(distance_km)

        closeness_score = 1.0 / (distance_km + 1)

        hospital_specialties = hospital.get("specialties", [])
        if not isinstance(hospital_specialties, list):
            hospital_specialties = []

        specialty_match_count = 0
        matched_specialties = []
        for needed in specialty_needed:
            needed_lower = str(needed).lower()
            for hosp_spec in hospital_specialties:
                hosp_spec_lower = str(hosp_spec).lower()
                if _specialties_match(needed_lower, hosp_spec_lower):
                    specialty_match_count += 1
                    matched_specialties.append(hosp_spec)
                    break

        specialty_score = (
            specialty_match_count / max(1, len(specialty_needed))
            if specialty_needed
            else 0
        )

        beds_available = hospital.get("beds_available", 0)
        bed_score = min(1.0, beds_available / 10.0) if beds_available else 0

        trauma_team_status = hospital.get("trauma_team_status", "")
        trauma_ready_bonus = 1.0 if trauma_team_status == "READY" else 0

        # Priority-aware weighting
        if priority == "P1":
            # P1: 70% closeness, 20% specialty bonus, 10% trauma ready
            match_score = (
                0.7 * closeness_score
                + 0.2 * specialty_score
                + 0.1 * trauma_ready_bonus
            )
        elif priority == "P2":
            # P2: 50% closeness, 30% specialty, 10% beds, 10% ready
            match_score = (
                0.5 * closeness_score
                + 0.3 * specialty_score
                + 0.1 * bed_score
                + 0.1 * trauma_ready_bonus
            )
        else:  # P3 / P4
            # 60% closeness, 20% specialty, 10% beds, 10% ready
            match_score = (
                0.6 * closeness_score
                + 0.2 * specialty_score
                + 0.1 * bed_score
                + 0.1 * trauma_ready_bonus
            )

        # Build match reason string
        reason_parts = []
        trauma_level = hospital.get("trauma_level")
        if priority == "P1" and trauma_level == 1:
            reason_parts.append("Level 1 trauma center")
        elif trauma_level is not None:
            reason_parts.append(f"Level {trauma_level} trauma center")

        reason_parts.append(f"{distance_km:.1f} km")
        reason_parts.append(f"ETA {eta_min} min")

        if matched_specialties:
            reason_parts.append(f"{matched_specialties[0].lower()} match")

        if priority != "P1" and beds_available:
            reason_parts.append(f"{beds_available} beds available")

        if trauma_ready_bonus:
            reason_parts.append("trauma team READY")

        match_reason = " · ".join(reason_parts)

        augmented = hospital.copy()
        augmented["distance_km"] = distance_km
        augmented["eta_min"] = eta_min
        augmented["match_score"] = match_score
        augmented["match_reason"] = match_reason

        scored_candidates.append(augmented)

    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    best_hospital = scored_candidates[0]
    alternatives = scored_candidates[1:3]
    best_hospital["alternatives"] = alternatives

    if match_warning:
        best_hospital["match_warning"] = match_warning

    return best_hospital


def find_nearest_pharmacy(
    pharmacies: list[dict],
    lat: float,
    lon: float,
) -> Optional[dict]:
    """Find the nearest pharmacy by Haversine distance.

    Args:
        pharmacies: List of pharmacy facility dicts
        lat: Incident latitude
        lon: Incident longitude

    Returns:
        Nearest pharmacy dict augmented with distance_km and eta_min.
        Returns None if list is empty.
    """
    if not pharmacies:
        return None

    nearest = None
    min_distance = float("inf")

    for pharmacy in pharmacies:
        distance_km = haversine_km(lat, lon, pharmacy["lat"], pharmacy["lon"])
        if distance_km < min_distance:
            min_distance = distance_km
            nearest = pharmacy

    if nearest is None:
        return None

    result = nearest.copy()
    result["distance_km"] = min_distance
    result["eta_min"] = estimate_eta_minutes(min_distance)

    return result


def find_nearest_blood_bank(
    blood_banks: list[dict],
    lat: float,
    lon: float,
    priority: str,
) -> Optional[dict]:
    """Find the nearest blood bank for P1/P2 priorities only.

    Args:
        blood_banks: List of blood bank facility dicts
        lat: Incident latitude
        lon: Incident longitude
        priority: Triage priority (P1/P2/P3/P4)

    Returns:
        Nearest blood bank dict augmented with distance_km and eta_min.
        Returns None for P3/P4 priorities or if list is empty.
    """
    if priority not in ["P1", "P2"]:
        return None

    if not blood_banks:
        return None

    nearest = None
    min_distance = float("inf")

    for blood_bank in blood_banks:
        distance_km = haversine_km(lat, lon, blood_bank["lat"], blood_bank["lon"])
        if distance_km < min_distance:
            min_distance = distance_km
            nearest = blood_bank

    if nearest is None:
        return None

    result = nearest.copy()
    result["distance_km"] = min_distance
    result["eta_min"] = estimate_eta_minutes(min_distance)

    return result