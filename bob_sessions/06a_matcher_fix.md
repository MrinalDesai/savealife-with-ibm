**User:**

<task>
Task 6a prompt — Hospital matcher fix
Copy this into Bob:

Task: Improve the hospital matcher to make clinically appropriate choices for high-priority cases.
Context: SaveAlife's utils/facility_matcher.py currently picks Coastal Emergency Hospital (9.3 km away) over Central City Hospital (5.4 km with neurology specialty) for a P1 head trauma case. This is wrong — for the most critical patients, closer is more important, and explicit specialty match should be required. The matcher is too generous with weighting specialty score when many hospitals nominally have "trauma" in their list.
Modify utils/facility_matcher.py so the scoring logic depends on priority:

For P1 (life-threatening):

Closeness is dominant: 70% weight on closeness (1 / (distance_km + 1))
Hard requirement: at least one of triage_result["specialty_needed"] items must appear (case-insensitive substring) in the hospital's specialties list. Hospitals failing this requirement are excluded from candidates entirely (not just penalized).
Bonus only: 20% specialty match score (count of matching specialties / total needed, capped at 1.0)
Bonus: 10% if trauma_team_status == "READY"
Bed availability is no longer in the formula for P1 (every Level 1 trauma center should accept; we'd rather route there + risk overflow than send to a closer non-trauma center).

For P2 (urgent):

50% closeness, 30% specialty match (soft — no hard requirement), 10% bed availability, 10% READY bonus (existing weights — keep these)

For P3/P4:

60% closeness, 20% specialty, 10% beds, 10% READY (slightly more closeness-weighted than current)


Edge cases to handle:

If P1 and no hospital matches the specialty requirement, fall back gracefully: return the closest Level 1 trauma center even without specialty match, and add a match_warning field saying "No specialty-matched hospital available — routing to closest Level 1 trauma center."
If triage_result["specialty_needed"] is empty or missing, treat all hospitals as eligible for the specialty filter (the hard requirement only kicks in if there ARE required specialties).

Update the match_reason string to reflect the priority-aware logic. For P1, it should mention "Level 1 trauma center" prominently when applicable. For all priorities, format remains short and human-readable like:

P1 example: "Level 1 trauma center · 5.4 km · ETA 11 min · neurosurgery match · trauma team READY"
P2 example: "5.4 km · ETA 11 min · trauma match · 8 beds available"


Don't change:

Function signatures (find_best_hospital, find_nearest_pharmacy, find_nearest_blood_bank keep the same args)
The haversine_km and estimate_eta_minutes functions
The alternatives field structure
Any other file in the project

Run no code, install nothing — just edit utils/facility_matcher.py.
After your edit, the same P1 motorcycle accident case should now route to Central City Hospital (5.4 km, has trauma + cardiology + neurology) instead of Coastal Emergency (9.3 km).
</task>
<environment_details>
# VSCode Visible Files
app.py

# VSCode Open Tabs
appv0.py,appv1.py,appv2.py,app.py,prompts.py,agents/triage_agent.py,agents/first_aid_agent.py,agents/handoff_agent.py,tests/test_pipeline.py,utils/watsonx_client.py,utils/facility_matcher.py,pipeline.py,tests/test_full_pipeline.py,data_sources/hospitals_csv.py,data_sources/pharmacies_json.py,data_sources/bloodbanks_text.py,debug_watsonx.py,tests/test_adapters.py,requirements.txt,.env.example

# Current Time
Current time in ISO 8601 UTC format: 2026-05-01T17:42:04.624Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.00

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>code</slug>
<name>💻 Code</name>


# Current Workspace Directory (c:/Users/mrina/Downloads/IBM_HACKATHON) Files
.env
.env.example
.gitignore
app.py
appv0.py
appv1.py
appv2.py
config.py
debug_watsonx.py
pipeline.py
prompts.py
README.md
requirements.txt
agents/
agents/__init__.py
agents/first_aid_agent.py
agents/handoff_agent.py
agents/triage_agent.py
bob_sessions/
bob_sessions/01_scaffold_summary.png
bob_sessions/01_scaffold.md.md
bob_sessions/01.txt
bob_sessions/02_adapters_summary.png.png
bob_sessions/02_adapters.md.md
bob_sessions/02.txt
bob_sessions/03_agents_summary.png
bob_sessions/03_agents.md
bob_sessions/03_agents.md.md
bob_sessions/04_pipeline_summary.png
bob_sessions/04_pipeline.md
bob_sessions/05_streamlit_ui_summary.png
bob_sessions/05_streamlit_ui.md
bob_sessions/demo_proof_adapters.txt.txt
bob_sessions/demo_proof_pipeline.txt.txt
bob_sessions/sample_pipeline_full_output.txt
bob_sessions/Screenshot 2026-05-01 210209.jpg
bob_sessions/ui.png
data/
data/bloodbanks.txt
data/hospitals.csv
data/pharmacies.json
data_sources/
data_sources/__init__.py
data_sources/adapter_base.py
data_sources/bloodbanks_text.py
data_sources/hospitals_csv.py
data_sources/pharmacies_json.py
tests/
tests/test_adapters.py
tests/test_full_pipeline.py
tests/test_pipeline.py
utils/
utils/__init__.py
utils/facility_matcher.py
utils/watsonx_client.py
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll start by reading the current `utils/facility_matcher.py` file to understand the existing implementation before making the required changes.

<read_file>
<args>
<file>
<path>utils/facility_matcher.py</path>
</file>
</args>
</read_file>

---

**User:**

[read_file for 'utils/facility_matcher.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>utils/facility_matcher.py</path>
<content lines="1-294">
  1 | """Facility matching logic based on distance and capability requirements.
  2 | 
  3 | This module provides functions for finding the best hospital, pharmacy, and blood bank
  4 | for an incident based on location, trauma capability, and other factors.
  5 | """
  6 | 
  7 | import math
  8 | from typing import Optional
  9 | 
 10 | 
 11 | def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
 12 |     """Calculate great-circle distance in kilometers between two coordinates.
 13 |     
 14 |     Uses the Haversine formula with Earth radius of 6371 km.
 15 |     
 16 |     Args:
 17 |         lat1: Latitude of first point in decimal degrees
 18 |         lon1: Longitude of first point in decimal degrees
 19 |         lat2: Latitude of second point in decimal degrees
 20 |         lon2: Longitude of second point in decimal degrees
 21 |     
 22 |     Returns:
 23 |         Distance in kilometers (float)
 24 |     """
 25 |     # Earth radius in kilometers
 26 |     R = 6371.0
 27 |     
 28 |     # Convert degrees to radians
 29 |     lat1_rad = math.radians(lat1)
 30 |     lon1_rad = math.radians(lon1)
 31 |     lat2_rad = math.radians(lat2)
 32 |     lon2_rad = math.radians(lon2)
 33 |     
 34 |     # Haversine formula
 35 |     dlat = lat2_rad - lat1_rad
 36 |     dlon = lon2_rad - lon1_rad
 37 |     
 38 |     a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
 39 |     c = 2 * math.asin(math.sqrt(a))
 40 |     
 41 |     distance = R * c
 42 |     return distance
 43 | 
 44 | 
 45 | def estimate_eta_minutes(distance_km: float, avg_speed_kmh: float = 30) -> int:
 46 |     """Estimate Mumbai-traffic-realistic ETA in minutes.
 47 |     
 48 |     Args:
 49 |         distance_km: Distance in kilometers
 50 |         avg_speed_kmh: Average speed in km/h (default 30 for Mumbai traffic)
 51 |     
 52 |     Returns:
 53 |         Estimated time in minutes (at least 1, rounded to nearest int)
 54 |     """
 55 |     if distance_km <= 0:
 56 |         return 1
 57 |     
 58 |     # Calculate time in hours, convert to minutes
 59 |     time_hours = distance_km / avg_speed_kmh
 60 |     time_minutes = time_hours * 60
 61 |     
 62 |     # Round to nearest int, ensure at least 1 minute
 63 |     return max(1, round(time_minutes))
 64 | 
 65 | 
 66 | def find_best_hospital(
 67 |     triage_result: dict,
 68 |     hospitals: list[dict],
 69 |     incident_lat: float,
 70 |     incident_lon: float
 71 | ) -> Optional[dict]:
 72 |     """Pick the most appropriate hospital for the incident.
 73 |     
 74 |     Filters hospitals by trauma capability and bed availability, then scores
 75 |     candidates based on distance, specialty match, beds, and trauma team status.
 76 |     
 77 |     Args:
 78 |         triage_result: Triage assessment with priority and specialty_needed
 79 |         hospitals: List of hospital facility dicts
 80 |         incident_lat: Incident latitude
 81 |         incident_lon: Incident longitude
 82 |     
 83 |     Returns:
 84 |         Top hospital dict augmented with distance_km, eta_min, match_score,
 85 |         match_reason, and alternatives (list of next 2 best). Returns None
 86 |         if no hospitals qualify.
 87 |     """
 88 |     if not hospitals:
 89 |         return None
 90 |     
 91 |     priority = triage_result.get("priority", "P2")
 92 |     specialty_needed = triage_result.get("specialty_needed", [])
 93 |     
 94 |     # Filter by trauma capability based on priority
 95 |     candidates = []
 96 |     for hospital in hospitals:
 97 |         trauma_level = hospital.get("trauma_level")
 98 |         
 99 |         # Apply trauma level filtering
100 |         if priority == "P1":
101 |             # P1 requires Level 1 trauma centers
102 |             if trauma_level is not None and trauma_level > 1:
103 |                 continue
104 |         elif priority in ["P2", "P3"]:
105 |             # P2/P3 require Level 1 or 2
106 |             if trauma_level is not None and trauma_level > 2:
107 |                 continue
108 |         # P4 accepts all hospitals
109 |         
110 |         # Filter out hospitals with no beds available
111 |         beds_available = hospital.get("beds_available")
112 |         if beds_available is not None and beds_available < 1:
113 |             continue
114 |         
115 |         candidates.append(hospital)
116 |     
117 |     if not candidates:
118 |         return None
119 |     
120 |     # Score each candidate
121 |     scored_candidates = []
122 |     for hospital in candidates:
123 |         distance_km = haversine_km(incident_lat, incident_lon, hospital["lat"], hospital["lon"])
124 |         eta_min = estimate_eta_minutes(distance_km)
125 |         
126 |         # Calculate weighted score
127 |         # 50% closeness (1 / (distance_km + 1))
128 |         closeness_score = 1.0 / (distance_km + 1)
129 |         
130 |         # 30% specialty match
131 |         hospital_specialties = hospital.get("specialties", [])
132 |         if not isinstance(hospital_specialties, list):
133 |             hospital_specialties = []
134 |         
135 |         specialty_match_count = 0
136 |         matched_specialties = []
137 |         for needed in specialty_needed:
138 |             needed_lower = str(needed).lower()
139 |             for hosp_spec in hospital_specialties:
140 |                 hosp_spec_lower = str(hosp_spec).lower()
141 |                 if needed_lower in hosp_spec_lower or hosp_spec_lower in needed_lower:
142 |                     specialty_match_count += 1
143 |                     matched_specialties.append(hosp_spec)
144 |                     break
145 |         
146 |         specialty_score = specialty_match_count / max(1, len(specialty_needed)) if specialty_needed else 0
147 |         
148 |         # 10% bed availability (beds_available / 10 capped at 1.0)
149 |         beds_available = hospital.get("beds_available", 0)
150 |         bed_score = min(1.0, beds_available / 10.0) if beds_available else 0
151 |         
152 |         # 10% bonus if trauma_team_status is "READY"
153 |         trauma_team_status = hospital.get("trauma_team_status", "")
154 |         trauma_ready_bonus = 1.0 if trauma_team_status == "READY" else 0
155 |         
156 |         # Calculate total weighted score
157 |         match_score = (
158 |             0.5 * closeness_score +
159 |             0.3 * specialty_score +
160 |             0.1 * bed_score +
161 |             0.1 * trauma_ready_bonus
162 |         )
163 |         
164 |         # Build match reason string
165 |         reason_parts = []
166 |         
167 |         # Trauma level
168 |         trauma_level = hospital.get("trauma_level")
169 |         if trauma_level is not None:
170 |             reason_parts.append(f"Level {trauma_level} trauma center")
171 |         
172 |         # Distance and ETA
173 |         reason_parts.append(f"{distance_km:.1f} km")
174 |         reason_parts.append(f"ETA {eta_min} min")
175 |         
176 |         # Specialty matches
177 |         if matched_specialties:
178 |             reason_parts.append(f"{', '.join(matched_specialties[:2])} match")
179 |         
180 |         # Beds
181 |         if beds_available:
182 |             reason_parts.append(f"{beds_available} beds")
183 |         
184 |         # Trauma team ready
185 |         if trauma_ready_bonus:
186 |             reason_parts.append("trauma team ready")
187 |         
188 |         match_reason = " · ".join(reason_parts)
189 |         
190 |         # Augment hospital dict
191 |         augmented = hospital.copy()
192 |         augmented["distance_km"] = distance_km
193 |         augmented["eta_min"] = eta_min
194 |         augmented["match_score"] = match_score
195 |         augmented["match_reason"] = match_reason
196 |         
197 |         scored_candidates.append(augmented)
198 |     
199 |     # Sort by score descending
200 |     scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
201 |     
202 |     # Get top hospital and alternatives
203 |     best_hospital = scored_candidates[0]
204 |     alternatives = scored_candidates[1:3]  # Next 2 best
205 |     best_hospital["alternatives"] = alternatives
206 |     
207 |     return best_hospital
208 | 
209 | 
210 | def find_nearest_pharmacy(
211 |     pharmacies: list[dict],
212 |     lat: float,
213 |     lon: float
214 | ) -> Optional[dict]:
215 |     """Find the nearest pharmacy by Haversine distance.
216 |     
217 |     Args:
218 |         pharmacies: List of pharmacy facility dicts
219 |         lat: Incident latitude
220 |         lon: Incident longitude
221 |     
222 |     Returns:
223 |         Nearest pharmacy dict augmented with distance_km and eta_min.
224 |         Returns None if list is empty.
225 |     """
226 |     if not pharmacies:
227 |         return None
228 |     
229 |     nearest = None
230 |     min_distance = float('inf')
231 |     
232 |     for pharmacy in pharmacies:
233 |         distance_km = haversine_km(lat, lon, pharmacy["lat"], pharmacy["lon"])
234 |         if distance_km < min_distance:
235 |             min_distance = distance_km
236 |             nearest = pharmacy
237 |     
238 |     if nearest is None:
239 |         return None
240 |     
241 |     # Augment with distance and ETA
242 |     result = nearest.copy()
243 |     result["distance_km"] = min_distance
244 |     result["eta_min"] = estimate_eta_minutes(min_distance)
245 |     
246 |     return result
247 | 
248 | 
249 | def find_nearest_blood_bank(
250 |     blood_banks: list[dict],
251 |     lat: float,
252 |     lon: float,
253 |     priority: str
254 | ) -> Optional[dict]:
255 |     """Find the nearest blood bank for P1/P2 priorities only.
256 |     
257 |     Args:
258 |         blood_banks: List of blood bank facility dicts
259 |         lat: Incident latitude
260 |         lon: Incident longitude
261 |         priority: Triage priority (P1/P2/P3/P4)
262 |     
263 |     Returns:
264 |         Nearest blood bank dict augmented with distance_km and eta_min.
265 |         Returns None for P3/P4 priorities or if list is empty.
266 |     """
267 |     # Only relevant for P1/P2 priorities
268 |     if priority not in ["P1", "P2"]:
269 |         return None
270 |     
271 |     if not blood_banks:
272 |         return None
273 |     
274 |     nearest = None
275 |     min_distance = float('inf')
276 |     
277 |     for blood_bank in blood_banks:
278 |         distance_km = haversine_km(lat, lon, blood_bank["lat"], blood_bank["lon"])
279 |         if distance_km < min_distance:
280 |             min_distance = distance_km
281 |             nearest = blood_bank
282 |     
283 |     if nearest is None:
284 |         return None
285 |     
286 |     # Augment with distance and ETA
287 |     result = nearest.copy()
288 |     result["distance_km"] = min_distance
289 |     result["eta_min"] = estimate_eta_minutes(min_distance)
290 |     
291 |     return result
292 | 
293 | 
294 | # Made with Bob
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
app.py

# VSCode Open Tabs
appv0.py,appv1.py,appv2.py,app.py,prompts.py,agents/triage_agent.py,agents/first_aid_agent.py,agents/handoff_agent.py,tests/test_pipeline.py,utils/watsonx_client.py,utils/facility_matcher.py,pipeline.py,tests/test_full_pipeline.py,data_sources/hospitals_csv.py,data_sources/pharmacies_json.py,data_sources/bloodbanks_text.py,debug_watsonx.py,tests/test_adapters.py,requirements.txt,.env.example

# Current Time
Current time in ISO 8601 UTC format: 2026-05-01T17:42:14.259Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.01

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>code</slug>
<name>💻 Code</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Now I'll modify the `find_best_hospital` function to implement the priority-aware scoring logic as specified. The key changes are:

1. **P1 cases**: 70% closeness, hard specialty requirement, 20% specialty bonus, 10% trauma ready bonus, no bed availability scoring
2. **P2 cases**: Keep existing 50% closeness, 30% specialty, 10% beds, 10% ready
3. **P3/P4 cases**: 60% closeness, 20% specialty, 10% beds, 10% ready
4. Add specialty hard requirement filtering for P1
5. Add fallback logic with warning for P1 when no specialty match
6. Update match_reason formatting

<apply_diff>
<path>utils/facility_matcher.py</path>
<diff>
<<<<<<< SEARCH
:start_line:66
-------
def find_best_hospital(
    triage_result: dict,
    hospitals: list[dict],
    incident_lat: float,
    incident_lon: float
) -> Optional[dict]:
    """Pick the most appropriate hospital for the incident.
    
    Filters hospitals by trauma capability and bed availability, then scores
    candidates based on distance, specialty match, beds, and trauma team status.
    
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
        
        # Apply trauma level filtering
        if priority == "P1":
            # P1 requires Level 1 trauma centers
            if trauma_level is not None and trauma_level > 1:
                continue
        elif priority in ["P2", "P3"]:
            # P2/P3 require Level 1 or 2
            if trauma_level is not None and trauma_level > 2:
                continue
        # P4 accepts all hospitals
        
        # Filter out hospitals with no beds available
        beds_available = hospital.get("beds_available")
        if beds_available is not None and beds_available < 1:
            continue
        
        candidates.append(hospital)
    
    if not candidates:
        return None
    
    # Score each candidate
    scored_candidates = []
    for hospital in candidates:
        distance_km = haversine_km(incident_lat, incident_lon, hospital["lat"], hospital["lon"])
        eta_min = estimate_eta_minutes(distance_km)
        
        # Calculate weighted score
        # 50% closeness (1 / (distance_km + 1))
        closeness_score = 1.0 / (distance_km + 1)
        
        # 30% specialty match
        hospital_specialties = hospital.get("specialties", [])
        if not isinstance(hospital_specialties, list):
            hospital_specialties = []
        
        specialty_match_count = 0
        matched_specialties = []
        for needed in specialty_needed:
            needed_lower = str(needed).lower()
            for hosp_spec in hospital_specialties:
                hosp_spec_lower = str(hosp_spec).lower()
                if needed_lower in hosp_spec_lower or hosp_spec_lower in needed_lower:
                    specialty_match_count += 1
                    matched_specialties.append(hosp_spec)
                    break
        
        specialty_score = specialty_match_count / max(1, len(specialty_needed)) if specialty_needed else 0
        
        # 10% bed availability (beds_available / 10 capped at 1.0)
        beds_available = hospital.get("beds_available", 0)
        bed_score = min(1.0, beds_available / 10.0) if beds_available else 0
        
        # 10% bonus if trauma_team_status is "READY"
        trauma_team_status = hospital.get("trauma_team_status", "")
        trauma_ready_bonus = 1.0 if trauma_team_status == "READY" else 0
        
        # Calculate total weighted score
        match_score = (
            0.5 * closeness_score +
            0.3 * specialty_score +
            0.1 * bed_score +
            0.1 * trauma_ready_bonus
        )
        
        # Build match reason string
        reason_parts = []
        
        # Trauma level
        trauma_level = hospital.get("trauma_level")
        if trauma_level is not None:
            reason_parts.append(f"Level {trauma_level} trauma center")
        
        # Distance and ETA
        reason_parts.append(f"{distance_km:.1f} km")
        reason_parts.append(f"ETA {eta_min} min")
        
        # Specialty matches
        if matched_specialties:
            reason_parts.append(f"{', '.join(matched_specialties[:2])} match")
        
        # Beds
        if beds_available:
            reason_parts.append(f"{beds_available} beds")
        
        # Trauma team ready
        if trauma_ready_bonus:
            reason_parts.append("trauma team ready")
        
        match_reason = " · ".join(reason_parts)
        
        # Augment hospital dict
        augmented = hospital.copy()
        augmented["distance_km"] = distance_km
        augmented["eta_min"] = eta_min
        augmented["match_score"] = match_score
        augmented["match_reason"] = match_reason
        
        scored_candidates.append(augmented)
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Get top hospital and alternatives
    best_hospital = scored_candidates[0]
    alternatives = scored_candidates[1:3]  # Next 2 best
    best_hospital["alternatives"] = alternatives
    
    return best_hospital
=======
def find_best_hospital(
    triage_result: dict,
    hospitals: list[dict],
    incident_lat: float,
    incident_lon: float
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
        
        # Apply trauma level filtering
        if priority == "P1":
            # P1 requires Level 1 trauma centers
            if trauma_level is not None and trauma_level > 1:
                continue
        elif priority in ["P2", "P3"]:
            # P2/P3 require Level 1 or 2
            if trauma_level is not None and trauma_level > 2:
                continue
        # P4 accepts all hospitals
        
        # Filter out hospitals with no beds available (except P1 - they should accept regardless)
        if priority != "P1":
            beds_available = hospital.get("beds_available")
            if beds_available is not None and beds_available < 1:
                continue
        
        candidates.append(hospital)
    
    if not candidates:
        return None
    
    # For P1: Apply hard specialty requirement if specialty_needed is not empty
    match_warning = None
    if priority == "P1" and specialty_needed:
        specialty_matched_candidates = []
        for hospital in candidates:
            hospital_specialties = hospital.get("specialties", [])
            if not isinstance(hospital_specialties, list):
                hospital_specialties = []
            
            # Check if at least one specialty_needed appears in hospital's specialties
            has_match = False
            for needed in specialty_needed:
                needed_lower = str(needed).lower()
                for hosp_spec in hospital_specialties:
                    hosp_spec_lower = str(hosp_spec).lower()
                    if needed_lower in hosp_spec_lower or hosp_spec_lower in needed_lower:
                        has_match = True
                        break
                if has_match:
                    break
            
            if has_match:
                specialty_matched_candidates.append(hospital)
        
        # If no specialty match found, fall back to closest Level 1 trauma center
        if not specialty_matched_candidates:
            match_warning = "No specialty-matched hospital available — routing to closest Level 1 trauma center."
        else:
            candidates = specialty_matched_candidates
    
    # Score each candidate
    scored_candidates = []
    for hospital in candidates:
        distance_km = haversine_km(incident_lat, incident_lon, hospital["lat"], hospital["lon"])
        eta_min = estimate_eta_minutes(distance_km)
        
        # Calculate closeness score
        closeness_score = 1.0 / (distance_km + 1)
        
        # Calculate specialty match
        hospital_specialties = hospital.get("specialties", [])
        if not isinstance(hospital_specialties, list):
            hospital_specialties = []
        
        specialty_match_count = 0
        matched_specialties = []
        for needed in specialty_needed:
            needed_lower = str(needed).lower()
            for hosp_spec in hospital_specialties:
                hosp_spec_lower = str(hosp_spec).lower()
                if needed_lower in hosp_spec_lower or hosp_spec_lower in needed_lower:
                    specialty_match_count += 1
                    matched_specialties.append(hosp_spec)
                    break
        
        specialty_score = specialty_match_count / max(1, len(specialty_needed)) if specialty_needed else 0
        
        # Calculate bed availability score
        beds_available = hospital.get("beds_available", 0)
        bed_score = min(1.0, beds_available / 10.0) if beds_available else 0
        
        # Calculate trauma team ready bonus
        trauma_team_status = hospital.get("trauma_team_status", "")
        trauma_ready_bonus = 1.0 if trauma_team_status == "READY" else 0
        
        # Priority-aware weighted scoring
        if priority == "P1":
            # P1: 70% closeness, 20% specialty bonus, 10% trauma ready, no beds
            match_score = (
                0.7 * closeness_score +
                0.2 * specialty_score +
                0.1 * trauma_ready_bonus
            )
        elif priority == "P2":
            # P2: 50% closeness, 30% specialty, 10% beds, 10% ready
            match_score = (
                0.5 * closeness_score +
                0.3 * specialty_score +
                0.1 * bed_score +
                0.1 * trauma_ready_bonus
            )
        else:  # P3 or P4
            # P3/P4: 60% closeness, 20% specialty, 10% beds, 10% ready
            match_score = (
                0.6 * closeness_score +
                0.2 * specialty_score +
                0.1 * bed_score +
                0.1 * trauma_ready_bonus
            )
        
        # Build match reason string
        reason_parts = []
        
        # For P1, emphasize Level 1 trauma center
        trauma_level = hospital.get("trauma_level")
        if priority == "P1" and trauma_level == 1:
            reason_parts.append("Level 1 trauma center")
        elif trauma_level is not None:
            reason_parts.append(f"Level {trauma_level} trauma center")
        
        # Distance and ETA
        reason_parts.append(f"{distance_km:.1f} km")
        reason_parts.append(f"ETA {eta_min} min")
        
        # Specialty matches
        if matched_specialties:
            # Show first matched specialty
            reason_parts.append(f"{matched_specialties[0].lower()} match")
        
        # Beds (not for P1)
        if priority != "P1" and beds_available:
            reason_parts.append(f"{beds_available} beds available")
        
        # Trauma team ready
        if trauma_ready_bonus:
            reason_parts.append("trauma team READY")
        
        match_reason = " · ".join(reason_parts)
        
        # Augment hospital dict
        augmented = hospital.copy()
        augmented["distance_km"] = distance_km
        augmented["eta_min"] = eta_min
        augmented["match_score"] = match_score
        augmented["match_reason"] = match_reason
        
        scored_candidates.append(augmented)
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Get top hospital and alternatives
    best_hospital = scored_candidates[0]
    alternatives = scored_candidates[1:3]  # Next 2 best
    best_hospital["alternatives"] = alternatives
    
    # Add match warning if applicable
    if match_warning:
        best_hospital["match_warning"] = match_warning
    
    return best_hospital
>>>>>>> REPLACE
</diff>
</apply_diff>

---

**User:**

[apply_diff for 'utils/facility_matcher.py'] Result:
<file_write_result>
<path>utils/facility_matcher.py</path>
<operation>modified</operation>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<notice>Making multiple related changes in a single apply_diff is more efficient. If other changes are needed in this file, please include them as additional SEARCH/REPLACE blocks.</notice>
<environment_details>
# VSCode Visible Files
utils\facility_matcher.py

# VSCode Open Tabs
appv0.py,appv1.py,appv2.py,app.py,utils/facility_matcher.py,prompts.py,agents/triage_agent.py,agents/first_aid_agent.py,agents/handoff_agent.py,tests/test_pipeline.py,utils/watsonx_client.py,pipeline.py,tests/test_full_pipeline.py,data_sources/hospitals_csv.py,data_sources/pharmacies_json.py,data_sources/bloodbanks_text.py,debug_watsonx.py,tests/test_adapters.py,requirements.txt,.env.example

# Recently Modified Files
These files have been modified since you last accessed them (file was just edited so you may need to re-read it before editing):
utils/facility_matcher.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-01T17:42:52.167Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.04

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>code</slug>
<name>💻 Code</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<attempt_completion>
<result>
Successfully modified `utils/facility_matcher.py` with priority-aware hospital matching logic:

**Key Changes:**

1. **P1 (life-threatening) cases:**
   - 70% weight on closeness (dominant factor)
   - Hard requirement: at least one specialty from `specialty_needed` must match hospital's specialties (case-insensitive substring match)
   - Hospitals failing specialty requirement are excluded entirely
   - 20% specialty match bonus (count of matches / total needed)
   - 10% trauma team READY bonus
   - Bed availability removed from scoring (Level 1 trauma centers should accept)
   - Fallback: If no specialty match found, routes to closest Level 1 trauma center with `match_warning` field

2. **P2 (urgent) cases:**
   - Kept existing weights: 50% closeness, 30% specialty, 10% beds, 10% READY

3. **P3/P4 cases:**
   - 60% closeness, 20% specialty, 10% beds, 10% READY (more closeness-weighted)

4. **Match reason formatting:**
   - P1 emphasizes "Level 1 trauma center" prominently
   - Shows distance, ETA, specialty match, and trauma team status
   - Beds shown only for P2/P3/P4
   - Format: "Level 1 trauma center · 5.4 km · ETA 11 min · neurosurgery match · trauma team READY"

5. **Edge cases handled:**
   - Empty/missing `specialty_needed` treats all hospitals as eligible
   - No specialty match for P1 triggers fallback with warning message
   - P1 cases ignore bed availability filtering (trauma centers should accept)

The same P1 motorcycle accident case will now correctly route to Central City Hospital (5.4 km with neurology specialty) instead of Coastal Emergency Hospital (9.3 km away), as closeness is now dominant and specialty match is required for P1 cases.
</result>
</attempt_completion>

