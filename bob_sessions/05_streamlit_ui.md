**User:**

<task>
Task 5 prompt — copy this exactly into Bob

Task: Implement the Streamlit UI for SaveAlife — app.py.
Context: SaveAlife has working data adapters, three watsonx.ai agents, and a run_pipeline() orchestrator that takes a bystander report + incident location and returns a complete state dict. This task wires it into a polished two-view Streamlit app:

🆘 Bystander view — submit accident report, see priority + first-aid + hospital alert
🏥 ER Trauma Bay view — see queue of incoming traumas, color-coded by priority, with full pre-arrival briefs

Both views share state via st.session_state.er_queue so submissions from the Bystander view appear in the ER view.

File: app.py at the project root.
Imports & page config

import streamlit as st, pandas, json, from datetime import datetime, from pipeline import run_pipeline
st.set_page_config(page_title="SaveAlife with IBM", page_icon="🚑", layout="wide", initial_sidebar_state="expanded")

Constants at the top
pythonAPP_NAME = "SaveAlife with IBM"
APP_TAGLINE = "AI-coordinated trauma response for the Golden Hour"
APP_VERSION = "0.1.0"

# Default incident location for demo (near Bandra)
DEFAULT_INCIDENT_LAT = 19.0590
DEFAULT_INCIDENT_LON = 72.8295

# Priority color mapping
PRIORITY_INFO = {
    "P1": {"label": "IMMEDIATE", "color": "#DC2626", "color_name": "RED",
           "description": "Life-threatening. Immediate intervention required."},
    "P2": {"label": "URGENT", "color": "#EA580C", "color_name": "ORANGE",
           "description": "Serious. Treatment within 10 minutes."},
    "P3": {"label": "DELAYED", "color": "#CA8A04", "color_name": "YELLOW",
           "description": "Stable. Treatment within 60 minutes."},
    "P4": {"label": "MINOR", "color": "#16A34A", "color_name": "GREEN",
           "description": "Minor. May not require hospital transport."},
}

BYSTANDER_DISCLAIMER = (
    "⚠️ This tool provides general first-aid guidance based on established "
    "public protocols. It does NOT replace emergency services. "
    "Always call 112 (India) or your local emergency number immediately."
)

ER_DISCLAIMER = (
    "ℹ️ Demonstration system. Patient assessments are AI-generated from bystander "
    "reports and require verification by qualified medical staff on arrival."
)
Session state initialization
At the top of the script (after imports, before any rendering):
pythonif "er_queue" not in st.session_state:
    st.session_state.er_queue = []        # list of completed pipeline results
if "current_result" not in st.session_state:
    st.session_state.current_result = None
Sidebar — view toggle
pythonwith st.sidebar:
    st.title(f"🚑 {APP_NAME}")
    st.caption(APP_TAGLINE)
    st.markdown("---")
    view = st.radio("View", ["🆘 Bystander", "🏥 ER Trauma Bay"], index=0, label_visibility="collapsed")
    st.markdown("---")
    st.metric("Incoming Traumas", len(st.session_state.er_queue))
    st.caption(f"Version {APP_VERSION}")
    st.caption("Powered by IBM Bob + watsonx.ai")
Sample reports for demo
Hardcode 4 sample bystander reports inside app.py (don't import — keep file self-contained):

P1 — Severe head trauma: "There's been a really bad accident on the highway. Two cars crashed head-on. One driver is bleeding badly from the head and isn't responding when I call out to him. I can't tell if he's breathing properly."
P1 — Motorcycle spinal: "A motorcycle hit a divider near Bandra. The rider is on the ground, not moving. He's breathing but barely conscious. There's blood near his head. He has a helmet on but it's cracked."
P2 — Pedestrian fracture: "A man was hit by a car while crossing the road. He's awake and talking but his right leg is twisted in a really bad way — looks broken. He's in a lot of pain. He's saying his back doesn't hurt and he can move his arms fine."
P4 — Minor fender-bender: "Two cars had a small accident at a parking exit, very low speed. Both drivers are out of the cars, both look completely fine, just arguing about whose fault it was. Just minor scratches."

Store as a list of {"id", "title", "report"} dicts.
Bystander view — render_bystander_view()

Title: 🆘 Report a Road Accident
Disclaimer: st.warning(BYSTANDER_DISCLAIMER)
Sample selector in expander (expanded=False): dropdown of sample titles, fills the textarea below when selected
Free-text textarea (height=180): "Describe what you're seeing — be as detailed as you can"
Submit button: full-width, type="primary", labeled "🆘 Submit Report"
On submit:

Show st.progress(0) and a status message
Call run_pipeline(report, DEFAULT_INCIDENT_LAT, DEFAULT_INCIDENT_LON, progress_callback=...) — the callback updates the progress bar step/total with stage name
On success: store result in st.session_state.current_result AND append to st.session_state.er_queue
On error: st.error(...) with the exception message


Show result if st.session_state.current_result exists — call render_bystander_result(result)

render_bystander_result(result)
Render in this order:

Priority banner (full width) — colored div using st.markdown(..., unsafe_allow_html=True). Show Priority: P1 — IMMEDIATE and the priority description, with the priority color as background, white text, padding 16px, border-radius 8px.
Two-column layout (st.columns([1, 1])):

Left column — "📋 What to do right now": numbered first-aid steps, then "Do NOT:" warnings if do_not_do is non-empty (use st.warning)
Right column — "🏥 Hospital being alerted": hospital name (bold), location, ETA metric (st.metric("ETA", f"{eta_min} min")), match reason as caption. If hospital is None, st.error("No suitable hospital available.")


Below the columns, a row of 3 small metrics if available: nearest pharmacy distance, blood bank distance, total processing time (from agent_log)
Expander "🤖 Triage details (auto-generated by watsonx.ai)" — st.json(result["triage"])
Expander "⏱ Pipeline timing" — show the agent_log as a small dataframe (pd.DataFrame(result["agent_log"]))

ER Trauma Bay view — render_er_view()

Title: 🏥 ER Trauma Bay — Incoming Patients
Info disclaimer: st.info(ER_DISCLAIMER)
If er_queue is empty: st.info("No incoming traumas. Submit a bystander report from the Bystander view.") and return
Sort the queue: by priority (P1 first), then by completed_at descending. Helper: priority_sort_key = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
For each result in sorted queue, call render_er_alert_card(result)

render_er_alert_card(result)

Card header — colored left-border stripe (8px, priority color), light gray background, padding. Show:

Bold: handoff.incoming_alert (one-line headline)
Below in gray: [priority] [label] · [hospital_name] · ETA [eta_min] min
Use st.markdown(..., unsafe_allow_html=True) for the colored stripe


Expander "View full briefing" — inside, two columns:

Left: "Preparation checklist" (bullets), "Specialist pages" (📞 prefix bullets)
Right: "Anticipated interventions" (bullets), "Information gaps for EMS handover" (❓ prefix bullets)


Below the columns — small caption: "Original bystander report" with result["bystander_report"] shown in italics

Router at the bottom
pythonif view.startswith("🆘"):
    render_bystander_view()
else:
    render_er_view()

Constraints:

Don't run the app, don't install anything — just write app.py
Don't modify any other file — app.py is the only file written/edited in this task
Use Python 3.11+ syntax
Keep all colors as hex strings (don't import any external color libraries)
The progress callback must update both the progress bar AND a text status (e.g., "[2/5] Triage Agent...")
Use st.spinner while the pipeline runs (the progress bar is on top of the spinner is fine)
Don't use deprecated Streamlit APIs (st.experimental_*)
</task>
<environment_details>
# VSCode Visible Files


# VSCode Open Tabs
prompts.py,agents/triage_agent.py,agents/first_aid_agent.py,agents/handoff_agent.py,tests/test_pipeline.py,utils/watsonx_client.py,utils/facility_matcher.py,pipeline.py,tests/test_full_pipeline.py,bob_sessions/03_agents.md,data_sources/hospitals_csv.py,data_sources/pharmacies_json.py,data_sources/bloodbanks_text.py,debug_watsonx.py,tests/test_adapters.py,requirements.txt,.env.example,.env,.gitignore,README.md

# Current Time
Current time in ISO 8601 UTC format: 2026-05-01T17:03:19.037Z
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
bob_sessions/demo_proof_adapters.txt.txt
bob_sessions/demo_proof_pipeline.txt.txt
bob_sessions/sample_pipeline_full_output.txt
bob_sessions/Screenshot 2026-05-01 210209.jpg
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

I'll implement the Streamlit UI for SaveAlife by creating a comprehensive `app.py` file with both the Bystander and ER Trauma Bay views.

<write_to_file>
<path>app.py</path>
<content>
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pipeline import run_pipeline

# Page configuration
st.set_page_config(
    page_title="SaveAlife with IBM",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
APP_NAME = "SaveAlife with IBM"
APP_TAGLINE = "AI-coordinated trauma response for the Golden Hour"
APP_VERSION = "0.1.0"

# Default incident location for demo (near Bandra)
DEFAULT_INCIDENT_LAT = 19.0590
DEFAULT_INCIDENT_LON = 72.8295

# Priority color mapping
PRIORITY_INFO = {
    "P1": {
        "label": "IMMEDIATE",
        "color": "#DC2626",
        "color_name": "RED",
        "description": "Life-threatening. Immediate intervention required."
    },
    "P2": {
        "label": "URGENT",
        "color": "#EA580C",
        "color_name": "ORANGE",
        "description": "Serious. Treatment within 10 minutes."
    },
    "P3": {
        "label": "DELAYED",
        "color": "#CA8A04",
        "color_name": "YELLOW",
        "description": "Stable. Treatment within 60 minutes."
    },
    "P4": {
        "label": "MINOR",
        "color": "#16A34A",
        "color_name": "GREEN",
        "description": "Minor. May not require hospital transport."
    },
}

BYSTANDER_DISCLAIMER = (
    "⚠️ This tool provides general first-aid guidance based on established "
    "public protocols. It does NOT replace emergency services. "
    "Always call 112 (India) or your local emergency number immediately."
)

ER_DISCLAIMER = (
    "ℹ️ Demonstration system. Patient assessments are AI-generated from bystander "
    "reports and require verification by qualified medical staff on arrival."
)

# Sample reports for demo
SAMPLE_REPORTS = [
    {
        "id": "p1_head_trauma",
        "title": "P1 — Severe head trauma",
        "report": "There's been a really bad accident on the highway. Two cars crashed head-on. One driver is bleeding badly from the head and isn't responding when I call out to him. I can't tell if he's breathing properly."
    },
    {
        "id": "p1_motorcycle_spinal",
        "title": "P1 — Motorcycle spinal",
        "report": "A motorcycle hit a divider near Bandra. The rider is on the ground, not moving. He's breathing but barely conscious. There's blood near his head. He has a helmet on but it's cracked."
    },
    {
        "id": "p2_pedestrian_fracture",
        "title": "P2 — Pedestrian fracture",
        "report": "A man was hit by a car while crossing the road. He's awake and talking but his right leg is twisted in a really bad way — looks broken. He's in a lot of pain. He's saying his back doesn't hurt and he can move his arms fine."
    },
    {
        "id": "p4_minor_fender",
        "title": "P4 — Minor fender-bender",
        "report": "Two cars had a small accident at a parking exit, very low speed. Both drivers are out of the cars, both look completely fine, just arguing about whose fault it was. Just minor scratches."
    }
]

# Session state initialization
if "er_queue" not in st.session_state:
    st.session_state.er_queue = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None

# Sidebar
with st.sidebar:
    st.title(f"🚑 {APP_NAME}")
    st.caption(APP_TAGLINE)
    st.markdown("---")
    view = st.radio(
        "View",
        ["🆘 Bystander", "🏥 ER Trauma Bay"],
        index=0,
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.metric("Incoming Traumas", len(st.session_state.er_queue))
    st.caption(f"Version {APP_VERSION}")
    st.caption("Powered by IBM Bob + watsonx.ai")


def render_bystander_result(result):
    """Render the result of a bystander report submission."""
    # Priority banner
    priority = result.get("priority", "P3")
    priority_info = PRIORITY_INFO.get(priority, PRIORITY_INFO["P3"])
    
    banner_html = f"""
    <div style="
        background-color: {priority_info['color']};
        color: white;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
    ">
        <h3 style="margin: 0; color: white;">Priority: {priority} — {priority_info['label']}</h3>
        <p style="margin: 8px 0 0 0; color: white;">{priority_info['description']}</p>
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📋 What to do right now")
        first_aid = result.get("first_aid", {})
        steps = first_aid.get("steps", [])
        
        if steps:
            for i, step in enumerate(steps, 1):
                st.markdown(f"{i}. {step}")
        else:
            st.info("No specific first-aid steps available.")
        
        do_not_do = first_aid.get("do_not_do", [])
        if do_not_do:
            st.warning("**Do NOT:**\n" + "\n".join([f"• {item}" for item in do_not_do]))
    
    with col2:
        st.subheader("🏥 Hospital being alerted")
        hospital = result.get("hospital")
        
        if hospital:
            st.markdown(f"**{hospital.get('name', 'Unknown Hospital')}**")
            st.caption(hospital.get("location", "Location not available"))
            
            eta_min = hospital.get("eta_min")
            if eta_min:
                st.metric("ETA", f"{eta_min} min")
            
            match_reason = hospital.get("match_reason", "")
            if match_reason:
                st.caption(match_reason)
        else:
            st.error("No suitable hospital available.")
    
    # Additional metrics
    metrics_cols = st.columns(3)
    
    with metrics_cols[0]:
        pharmacy = result.get("pharmacy")
        if pharmacy:
            dist = pharmacy.get("distance_km", 0)
            st.metric("Nearest Pharmacy", f"{dist:.1f} km")
    
    with metrics_cols[1]:
        blood_bank = result.get("blood_bank")
        if blood_bank:
            dist = blood_bank.get("distance_km", 0)
            st.metric("Blood Bank", f"{dist:.1f} km")
    
    with metrics_cols[2]:
        agent_log = result.get("agent_log", [])
        if agent_log:
            total_time = sum(entry.get("duration_sec", 0) for entry in agent_log)
            st.metric("Processing Time", f"{total_time:.1f}s")
    
    # Triage details expander
    with st.expander("🤖 Triage details (auto-generated by watsonx.ai)"):
        triage = result.get("triage", {})
        st.json(triage)
    
    # Pipeline timing expander
    with st.expander("⏱ Pipeline timing"):
        agent_log = result.get("agent_log", [])
        if agent_log:
            df = pd.DataFrame(agent_log)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No timing information available.")


def render_bystander_view():
    """Render the bystander view for submitting accident reports."""
    st.title("🆘 Report a Road Accident")
    st.warning(BYSTANDER_DISCLAIMER)
    
    # Sample selector
    with st.expander("📝 Load a sample report", expanded=False):
        sample_titles = ["Select a sample..."] + [s["title"] for s in SAMPLE_REPORTS]
        selected_sample = st.selectbox(
            "Choose a sample report",
            sample_titles,
            label_visibility="collapsed"
        )
        
        if selected_sample != "Select a sample...":
            for sample in SAMPLE_REPORTS:
                if sample["title"] == selected_sample:
                    st.session_state.sample_report = sample["report"]
                    break
    
    # Report textarea
    report_text = st.text_area(
        "Describe what you're seeing — be as detailed as you can",
        value=st.session_state.get("sample_report", ""),
        height=180,
        placeholder="Example: There's been a car accident. The driver is unconscious and bleeding from the head..."
    )
    
    # Clear the sample after it's been loaded
    if "sample_report" in st.session_state:
        del st.session_state.sample_report
    
    # Submit button
    if st.button("🆘 Submit Report", type="primary", use_container_width=True):
        if not report_text.strip():
            st.error("Please describe the accident before submitting.")
            return
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(step, total, stage_name):
            """Update progress bar and status text."""
            progress = step / total
            progress_bar.progress(progress)
            status_text.text(f"[{step}/{total}] {stage_name}...")
        
        try:
            with st.spinner("Processing your report..."):
                result = run_pipeline(
                    bystander_report=report_text,
                    incident_lat=DEFAULT_INCIDENT_LAT,
                    incident_lon=DEFAULT_INCIDENT_LON,
                    progress_callback=progress_callback
                )
                
                # Store result
                st.session_state.current_result = result
                st.session_state.er_queue.append(result)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                st.success("✅ Report processed successfully!")
                st.rerun()
                
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error processing report: {str(e)}")
            return
    
    # Show result if available
    if st.session_state.current_result:
        st.markdown("---")
        st.subheader("📊 Assessment Results")
        render_bystander_result(st.session_state.current_result)


def render_er_alert_card(result):
    """Render a single ER alert card for an incoming trauma."""
    priority = result.get("priority", "P3")
    priority_info = PRIORITY_INFO.get(priority, PRIORITY_INFO["P3"])
    handoff = result.get("handoff", {})
    hospital = result.get("hospital", {})
    
    # Card header with colored stripe
    incoming_alert = handoff.get("incoming_alert", "Incoming trauma patient")
    hospital_name = hospital.get("name", "Unknown Hospital")
    eta_min = hospital.get("eta_min", "N/A")
    
    card_html = f"""
    <div style="
        border-left: 8px solid {priority_info['color']};
        background-color: #F3F4F6;
        padding: 16px;
        margin-bottom: 16px;
        border-radius: 4px;
    ">
        <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 8px;">
            {incoming_alert}
        </div>
        <div style="color: #6B7280; font-size: 0.9em;">
            {priority} {priority_info['label']} · {hospital_name} · ETA {eta_min} min
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Expander with full briefing
    with st.expander("View full briefing"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Preparation checklist:**")
            prep_checklist = handoff.get("preparation_checklist", [])
            if prep_checklist:
                for item in prep_checklist:
                    st.markdown(f"• {item}")
            else:
                st.info("No preparation items listed.")
            
            st.markdown("**Specialist pages:**")
            specialist_pages = handoff.get("specialist_pages", [])
            if specialist_pages:
                for specialist in specialist_pages:
                    st.markdown(f"📞 {specialist}")
            else:
                st.info("No specialists to page.")
        
        with col2:
            st.markdown("**Anticipated interventions:**")
            interventions = handoff.get("anticipated_interventions", [])
            if interventions:
                for intervention in interventions:
                    st.markdown(f"• {intervention}")
            else:
                st.info("No interventions listed.")
            
            st.markdown("**Information gaps for EMS handover:**")
            info_gaps = handoff.get("information_gaps", [])
            if info_gaps:
                for gap in info_gaps:
                    st.markdown(f"❓ {gap}")
            else:
                st.info("No information gaps identified.")
        
        # Original report
        st.caption("**Original bystander report:**")
        original_report = result.get("bystander_report", "No report available")
        st.caption(f"*{original_report}*")


def render_er_view():
    """Render the ER Trauma Bay view showing incoming patients."""
    st.title("🏥 ER Trauma Bay — Incoming Patients")
    st.info(ER_DISCLAIMER)
    
    if not st.session_state.er_queue:
        st.info("No incoming traumas. Submit a bystander report from the Bystander view.")
        return
    
    # Sort queue by priority, then by time
    priority_sort_key = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    
    sorted_queue = sorted(
        st.session_state.er_queue,
        key=lambda x: (
            priority_sort_key.get(x.get("priority", "P3"), 3),
            -datetime.fromisoformat(x.get("completed_at", "2000-01-01T00:00:00")).timestamp()
        )
    )
    
    # Render each alert card
    for result in sorted_queue:
        render_er_alert_card(result)


# Router
if view.startswith("🆘"):
    render_bystander_view()
else:
    render_er_view()
</content>
<line_count>398</line_count>
</write_to_file>

---

**User:**

[write_to_file for 'app.py'] Result:
<file_write_result>
<path>app.py</path>
<operation>modified</operation>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<environment_details>
# VSCode Visible Files
app.py

# VSCode Open Tabs
app.py,prompts.py,agents/triage_agent.py,agents/first_aid_agent.py,agents/handoff_agent.py,tests/test_pipeline.py,utils/watsonx_client.py,utils/facility_matcher.py,pipeline.py,tests/test_full_pipeline.py,data_sources/hospitals_csv.py,data_sources/pharmacies_json.py,data_sources/bloodbanks_text.py,debug_watsonx.py,tests/test_adapters.py,requirements.txt,.env.example,.env,.gitignore,README.md

# Current Time
Current time in ISO 8601 UTC format: 2026-05-01T17:04:05.053Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.02

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
✅ **Streamlit UI Implementation Complete — app.py**

Successfully implemented a polished two-view Streamlit application for SaveAlife:

**🆘 Bystander View:**
- Sample report selector with 4 pre-configured scenarios (P1 head trauma, P1 motorcycle spinal, P2 pedestrian fracture, P4 minor fender-bender)
- Free-text accident report submission with disclaimer
- Real-time progress tracking during pipeline execution
- Comprehensive result display with:
  - Color-coded priority banner (RED/ORANGE/YELLOW/GREEN)
  - First-aid instructions with "Do NOT" warnings
  - Hospital alert with ETA and match reasoning
  - Nearby pharmacy and blood bank distances
  - Expandable triage details and pipeline timing

**🏥 ER Trauma Bay View:**
- Queue of incoming traumas sorted by priority (P1 first) then timestamp
- Color-coded alert cards with left border stripe
- Expandable full briefing for each patient:
  - Preparation checklist
  - Specialist pages needed
  - Anticipated interventions
  - Information gaps for EMS handover
  - Original bystander report

**Key Features:**
- Shared state via `st.session_state.er_queue` — submissions from Bystander view appear in ER view
- Wide layout with sidebar showing trauma count and view toggle
- Progress callback integration for real-time pipeline stage updates
- All colors as hex strings, no external dependencies
- Python 3.11+ compatible, no deprecated Streamlit APIs
- Self-contained file with hardcoded sample reports

The app is ready to run with `streamlit run app.py` and provides a complete demonstration of the SaveAlife AI-coordinated trauma response system.
</result>
</attempt_completion>

