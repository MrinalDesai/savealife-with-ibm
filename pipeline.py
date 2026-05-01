"""Agent orchestration pipeline for SaveAlife with IBM.

This module coordinates the end-to-end processing of bystander accident reports:
loading facilities, running triage, finding the best hospital, generating first-aid
instructions, and creating ER handoff briefs.
"""

import time
from datetime import datetime
from typing import Callable, Optional

from agents.triage_agent import TriageAgent
from agents.first_aid_agent import FirstAidAgent
from agents.handoff_agent import ERHandoffAgent
from data_sources.hospitals_csv import HospitalsCsvAdapter
from data_sources.pharmacies_json import PharmaciesJsonAdapter
from data_sources.bloodbanks_text import BloodBanksTextAdapter
from utils.facility_matcher import (
    find_best_hospital,
    find_nearest_pharmacy,
    find_nearest_blood_bank
)


def run_pipeline(
    bystander_report: str,
    incident_lat: float,
    incident_lon: float,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> dict:
    """Run the complete SaveAlife pipeline end-to-end.
    
    Processes a bystander accident report through all stages:
    1. Load facilities (hospitals, pharmacies, blood banks)
    2. Run triage assessment
    3. Find best hospital
    4. Generate first-aid instructions
    5. Generate ER handoff brief
    
    Args:
        bystander_report: Free-text accident description from bystander
        incident_lat: Incident latitude coordinate
        incident_lon: Incident longitude coordinate
        progress_callback: Optional callback function(stage_name, step, total_steps)
    
    Returns:
        Complete state dictionary with all results, timing, and warnings:
        {
            "bystander_report": str,
            "incident_location": {"lat": float, "lon": float},
            "started_at": str (ISO timestamp),
            "completed_at": str (ISO timestamp),
            "triage": dict,
            "first_aid": dict,
            "hospital": dict or None,
            "nearest_pharmacy": dict or None,
            "nearest_blood_bank": dict or None,
            "handoff": dict,
            "warnings": list[str],
            "agent_log": list[dict]
        }
    """
    # Initialize result structure
    started_at = datetime.utcnow().isoformat()
    warnings = []
    agent_log = []
    total_steps = 5
    
    # Helper to call progress callback
    def report_progress(stage: str, step: int):
        if progress_callback:
            progress_callback(stage, step, total_steps)
    
    # Helper to log stage timing
    def log_stage(stage: str, step: int, duration_sec: float):
        agent_log.append({
            "stage": stage,
            "step": step,
            "duration_sec": round(duration_sec, 3),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # STEP 1: Load facilities
    stage_name = "Load Facilities"
    report_progress(stage_name, 1)
    step_start = time.time()
    
    hospitals = []
    pharmacies = []
    blood_banks = []
    
    try:
        # Load hospitals
        hospitals_adapter = HospitalsCsvAdapter()
        hospitals = hospitals_adapter.load()
    except Exception as e:
        warnings.append(f"Failed to load hospitals: {str(e)}")
    
    try:
        # Load pharmacies
        pharmacies_adapter = PharmaciesJsonAdapter()
        pharmacies = pharmacies_adapter.load()
    except Exception as e:
        warnings.append(f"Failed to load pharmacies: {str(e)}")
    
    try:
        # Load blood banks (may fail if watsonx not configured)
        blood_banks_adapter = BloodBanksTextAdapter()
        blood_banks = blood_banks_adapter.load()
    except RuntimeError as e:
        # Non-fatal: watsonx credentials not configured
        warnings.append(f"Blood banks unavailable: {str(e)}")
    except Exception as e:
        warnings.append(f"Failed to load blood banks: {str(e)}")
    
    step_duration = time.time() - step_start
    log_stage(stage_name, 1, step_duration)
    
    # STEP 2: Run triage
    stage_name = "Triage Agent"
    report_progress(stage_name, 2)
    step_start = time.time()
    
    triage_agent = TriageAgent()
    triage = triage_agent.run(bystander_report)
    
    step_duration = time.time() - step_start
    log_stage(stage_name, 2, step_duration)
    
    # STEP 3: Find best hospital
    stage_name = "Find Best Hospital"
    report_progress(stage_name, 3)
    step_start = time.time()
    
    hospital = None
    if hospitals:
        hospital = find_best_hospital(triage, hospitals, incident_lat, incident_lon)
        if hospital is None:
            warnings.append("No suitable hospital found matching triage requirements")
    else:
        warnings.append("No hospitals available for matching")
    
    step_duration = time.time() - step_start
    log_stage(stage_name, 3, step_duration)
    
    # STEP 4: Generate first-aid instructions
    stage_name = "First Aid Agent"
    report_progress(stage_name, 4)
    step_start = time.time()
    
    first_aid_agent = FirstAidAgent()
    first_aid = first_aid_agent.run(triage, bystander_report)
    
    step_duration = time.time() - step_start
    log_stage(stage_name, 4, step_duration)
    
    # STEP 5: Generate ER handoff brief
    stage_name = "ER Handoff Agent"
    report_progress(stage_name, 5)
    step_start = time.time()
    
    # Use hospital if found, otherwise use placeholder
    handoff_hospital = hospital if hospital else {
        "name": "Unassigned",
        "eta_min": "?"
    }
    
    handoff_agent = ERHandoffAgent()
    handoff = handoff_agent.run(triage, handoff_hospital)
    
    step_duration = time.time() - step_start
    log_stage(stage_name, 5, step_duration)
    
    # Find nearest pharmacy and blood bank (no separate progress steps)
    nearest_pharmacy = find_nearest_pharmacy(pharmacies, incident_lat, incident_lon)
    
    priority = triage.get("priority", "P2")
    nearest_blood_bank = find_nearest_blood_bank(blood_banks, incident_lat, incident_lon, priority)
    
    # Build complete result
    completed_at = datetime.utcnow().isoformat()
    
    result = {
        "bystander_report": bystander_report,
        "incident_location": {
            "lat": incident_lat,
            "lon": incident_lon
        },
        "started_at": started_at,
        "completed_at": completed_at,
        "triage": triage,
        "first_aid": first_aid,
        "hospital": hospital,
        "nearest_pharmacy": nearest_pharmacy,
        "nearest_blood_bank": nearest_blood_bank,
        "handoff": handoff,
        "warnings": warnings,
        "agent_log": agent_log
    }
    
    return result


# Made with Bob
