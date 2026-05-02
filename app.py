import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from datetime import datetime
from pipeline import run_pipeline
from data_sources.clinics_text import ClinicsTextAdapter
from qr.incident_qr import build_incident_summary, render_qr_png
from streamlit_mic_recorder import mic_recorder
from voice.speech_input import transcribe_audio_bytes

# ============================================================
# Page configuration
# ============================================================
st.set_page_config(
    page_title="SaveAlife with IBM",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Constants
# ============================================================
APP_NAME = "SaveAlife with IBM"
APP_TAGLINE = "AI-coordinated trauma response for the Golden Hour"
APP_VERSION = "0.1.0"

DEFAULT_INCIDENT_LAT = 19.0590
DEFAULT_INCIDENT_LON = 72.8295
DEFAULT_INCIDENT_ADDRESS = "Bandra West, Mumbai, Maharashtra"

PRIORITY_INFO = {
    "P1": {"label": "IMMEDIATE", "color": "#EF4444", "bg": "#7F1D1D",
           "description": "Life-threatening. Immediate intervention required.",
           "pulse": True},
    "P2": {"label": "URGENT", "color": "#F97316", "bg": "#7C2D12",
           "description": "Serious. Treatment within 10 minutes.",
           "pulse": False},
    "P3": {"label": "DELAYED", "color": "#EAB308", "bg": "#713F12",
           "description": "Stable. Treatment within 60 minutes.",
           "pulse": False},
    "P4": {"label": "MINOR", "color": "#22C55E", "bg": "#14532D",
           "description": "Minor. May not require hospital transport.",
           "pulse": False},
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

SAMPLE_REPORTS = [
    {
        "id": "p1_head_trauma",
        "title": "🔴 P1 — Severe head trauma",
        "report": "There's been a really bad accident on the highway. Two cars crashed head-on. One driver is bleeding badly from the head and isn't responding when I call out to him. I can't tell if he's breathing properly."
    },
    {
        "id": "p1_motorcycle_spinal",
        "title": "🔴 P1 — Motorcycle spinal",
        "report": "A motorcycle hit a divider near Bandra. The rider is on the ground, not moving. He's breathing but barely conscious. There's blood near his head. He has a helmet on but it's cracked."
    },
    {
        "id": "p2_pedestrian_fracture",
        "title": "🟠 P2 — Pedestrian fracture",
        "report": "A man was hit by a car while crossing the road. He's awake and talking but his right leg is twisted in a really bad way — looks broken. He's in a lot of pain. He's saying his back doesn't hurt and he can move his arms fine."
    },
    {
        "id": "p4_minor_fender",
        "title": "🟢 P4 — Minor fender-bender",
        "report": "Two cars had a small accident at a parking exit, very low speed. Both drivers are out of the cars, both look completely fine, just arguing about whose fault it was. Just minor scratches."
    }
]

# ============================================================
# Custom CSS — dark professional theme + subtle pulse for P1
# ============================================================
CUSTOM_CSS = """
<style>
    /* ============================================================
       BLACK MEDICAL DASHBOARD THEME — UI ONLY
       ============================================================ */

    /* Full app background */
    .stApp,
    .main,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }

    /* Main content block */
    .block-container {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {
        background-color: #050505 !important;
        color: #FFFFFF !important;
        border-right: 1px solid #222222;
    }

    /* Global text visibility */
    h1, h2, h3, h4, h5, h6,
    p, span, label, div, small,
    .stMarkdown, .stText, .stCaption,
    [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"] {
        color: #FFFFFF !important;
    }

    /* Softer captions */
    .stCaption,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] {
        color: #D1D5DB !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background-color: #111111 !important;
        border: 1px solid #2A2A2A !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricDelta"] {
        color: #D1D5DB !important;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    /* Text areas / inputs */
    textarea,
    input {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #3A3A3A !important;
        border-radius: 10px !important;
    }

    textarea::placeholder,
    input::placeholder {
        color: #A3A3A3 !important;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #111111, #1A1A1A) !important;
        color: #FFFFFF !important;
        border: 1px solid #3A3A3A !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    .stButton button:hover {
        border: 1px solid #38BDF8 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.45) !important;
    }

    /* Primary button */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #DC2626, #7F1D1D) !important;
        border: 1px solid #EF4444 !important;
        color: #FFFFFF !important;
    }

    /* Dropdown / selectbox dark grey */
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border-color: #3A3A3A !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #FFFFFF !important;
    }

    div[data-baseweb="select"] svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }

    /* Dropdown popup menu */
    ul[role="listbox"],
    div[role="listbox"] {
        background-color: #1A1A1A !important;
        border: 1px solid #3A3A3A !important;
        color: #FFFFFF !important;
    }

    li[role="option"],
    div[role="option"] {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
    }

    li[role="option"] span,
    div[role="option"] span {
        color: #FFFFFF !important;
    }

    li[role="option"]:hover,
    div[role="option"]:hover {
        background-color: #2A2A2A !important;
        color: #38BDF8 !important;
    }

    li[aria-selected="true"],
    div[aria-selected="true"] {
        background-color: #333333 !important;
        color: #FFFFFF !important;
    }

    /* Radio buttons */
    div[role="radiogroup"] label,
    div[role="radiogroup"] span,
    div[role="radiogroup"] p {
        color: #FFFFFF !important;
    }

    /* Expanders */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #2A2A2A !important;
        border-radius: 10px !important;
    }

    [data-testid="stExpander"] details {
        background-color: #111111 !important;
        color: #FFFFFF !important;
    }

    /* Alert boxes */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        color: #FFFFFF !important;
    }

    [data-testid="stAlert"] div,
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span {
        color: #FFFFFF !important;
    }

    /* Dataframes and code */
    [data-testid="stDataFrame"],
    .stCodeBlock,
    code,
    pre {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #2A2A2A !important;
    }

    /* Progress bar */
    [data-testid="stProgress"] > div > div {
        background-color: #38BDF8 !important;
    }

    /* P1 pulse animation */
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.75); }
        50% { box-shadow: 0 0 0 16px rgba(239, 68, 68, 0); }
    }

    .priority-banner-p1 {
        animation: pulse-red 2s ease-in-out infinite;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 9px;
        height: 9px;
    }

    ::-webkit-scrollbar-track {
        background: #000000;
    }

    ::-webkit-scrollbar-thumb {
        background: #333333;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #4B5563;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================================================
# Session state
# ============================================================
if "er_queue" not in st.session_state:
    st.session_state.er_queue = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "user_facilities" not in st.session_state:
    st.session_state.user_facilities = {}
if "last_transcribed_audio_id" not in st.session_state:
    st.session_state.last_transcribed_audio_id = None

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown(f"## 🚑 {APP_NAME}")
    st.caption(APP_TAGLINE)
    st.markdown("---")
    view = st.radio(
        "View",
        ["🆘 Bystander", "🏥 ER Trauma Bay"],
        index=0,
        label_visibility="collapsed"
    )
    st.markdown("---")

    queue = st.session_state.er_queue
    p1_count = sum(1 for r in queue if r.get("triage", {}).get("priority") == "P1")
    st.metric("🚨 Incoming Traumas", len(queue))
    if p1_count > 0:
        st.error(f"🔴 {p1_count} P1 in queue")

    st.markdown("---")
    st.caption(f"v{APP_VERSION}")
    st.caption("⚡ Powered by IBM Bob + watsonx.ai")


# ============================================================
# Bystander result rendering
# ============================================================
def render_priority_banner(priority: str):
    info = PRIORITY_INFO.get(priority, PRIORITY_INFO["P3"])
    pulse_class = "priority-banner-p1" if info["pulse"] else ""
    banner_html = f"""
    <div class="{pulse_class}" style="
        background: linear-gradient(135deg, {info['color']} 0%, {info['bg']} 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 12px;
        margin-bottom: 24px;
        border: 1px solid {info['color']};
    ">
        <div style="font-size: 0.85rem; opacity: 0.85; letter-spacing: 0.1em; text-transform: uppercase;">
            Priority Assessment
        </div>
        <h2 style="margin: 4px 0 8px 0; color: white; font-size: 2.2rem;">
            {priority} — {info['label']}
        </h2>
        <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 1rem;">
            {info['description']}
        </p>
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)


def render_incident_location_card(result):
    """Display the human-readable accident location and coordinates."""
    incident_loc = result.get("incident_location", {})
    address = incident_loc.get("address", "Location not specified")
    lat = incident_loc.get("lat", "?")
    lon = incident_loc.get("lon", "?")
    st.markdown(
        f"""<div style="
            background-color: #111111;
            border-left: 4px solid #38BDF8;
            padding: 12px 18px;
            margin-bottom: 18px;
            border-radius: 8px;
        ">
            <div style="color: #94A3B8; font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase;">
                📍 Incident Location
            </div>
            <div style="color: #F1F5F9; font-size: 1.05rem; font-weight: 600; margin-top: 4px;">
                {address}
            </div>
            <div style="color: #64748B; font-size: 0.8rem; margin-top: 2px;">
                {lat}, {lon}
            </div>
        </div>""",
        unsafe_allow_html=True
    )


def render_map_with_pins(result):
    """Pydeck map with labeled pins and hover tooltips."""
    incident_loc = result.get("incident_location", {})
    if not incident_loc:
        return

    pins = []

    # Incident
    pins.append({
        "lat": incident_loc.get("lat"),
        "lon": incident_loc.get("lon"),
        "name": "🚨 Accident Site",
        "kind": "Incident",
        "detail": incident_loc.get("address", "Bystander-reported location"),
        "color": [239, 68, 68, 230],
        "radius": 200,
    })

    # Hospital
    hospital = result.get("hospital")
    if hospital:
        pins.append({
            "lat": hospital.get("lat"),
            "lon": hospital.get("lon"),
            "name": hospital.get("name", "Hospital"),
            "kind": "Hospital",
            "detail": (
                f"{hospital.get('distance_km', 0):.1f} km · "
                f"ETA {hospital.get('eta_min', '?')} min"
            ),
            "color": [59, 130, 246, 230],
            "radius": 150,
        })

    # Pharmacy
    pharmacy = result.get("nearest_pharmacy")
    if pharmacy:
        pins.append({
            "lat": pharmacy.get("lat"),
            "lon": pharmacy.get("lon"),
            "name": pharmacy.get("name", "Pharmacy"),
            "kind": "Pharmacy",
            "detail": (
                f"{pharmacy.get('distance_km', 0):.1f} km · "
                f"ETA {pharmacy.get('eta_min', '?')} min"
            ),
            "color": [34, 197, 94, 220],
            "radius": 100,
        })

    # Blood bank
    blood_bank = result.get("nearest_blood_bank")
    if blood_bank:
        pins.append({
            "lat": blood_bank.get("lat"),
            "lon": blood_bank.get("lon"),
            "name": blood_bank.get("name", "Blood Bank"),
            "kind": "Blood Bank",
            "detail": (
                f"{blood_bank.get('distance_km', 0):.1f} km · "
                f"ETA {blood_bank.get('eta_min', '?')} min"
            ),
            "color": [168, 85, 247, 220],
            "radius": 100,
        })

    # User-uploaded facilities (clinics)
    for facility_type, facilities in st.session_state.user_facilities.items():
        for facility in facilities:
            pins.append({
                "lat": facility.get("lat"),
                "lon": facility.get("lon"),
                "name": facility.get("name", "Clinic"),
                "kind": "Clinic (uploaded)",
                "detail": facility.get("hours", "Urgent care"),
                "color": [14, 165, 233, 220],
                "radius": 80,
            })

    pins = [p for p in pins if p["lat"] is not None and p["lon"] is not None]
    if not pins:
        return

    df = pd.DataFrame(pins)

    view_state = pdk.ViewState(
        latitude=incident_loc.get("lat"),
        longitude=incident_loc.get("lon"),
        zoom=12,
        pitch=0,
    )

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius="radius",
        radius_min_pixels=8,
        radius_max_pixels=24,
        pickable=True,
        opacity=0.9,
        stroked=True,
        get_line_color=[255, 255, 255, 200],
        line_width_min_pixels=1,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="name",
        get_size=14,
        get_color=[241, 245, 249, 255],
        get_pixel_offset=[14, -14],
        get_text_anchor='"start"',
        get_alignment_baseline='"bottom"',
        background=True,
        get_background_color=[15, 23, 42, 200],
        get_border_color=[100, 116, 139, 180],
        get_border_width=1,
        background_padding=[6, 4, 6, 4],
    )

    deck = pdk.Deck(
        layers=[scatter_layer, text_layer],
        initial_view_state=view_state,
        map_style="dark",
        tooltip={
            "html": "<b>{name}</b><br/>{kind}<br/>{detail}",
            "style": {
                "backgroundColor": "#0F172A",
                "color": "#F1F5F9",
                "border": "1px solid #334155",
                "padding": "8px 12px",
                "borderRadius": "6px",
                "fontSize": "0.85rem",
            },
        },
    )

    st.markdown("##### 🗺️ Coordination Map")
    st.pydeck_chart(deck, use_container_width=True)

    caption_parts = ["🔴 Incident · 🔵 Hospital · 🟢 Pharmacy · 🟣 Blood bank"]
    if st.session_state.user_facilities:
        caption_parts.append("🩵 Clinic (uploaded)")
    st.caption(" · ".join(caption_parts) + " · _hover any pin for details_")


def render_bystander_result(result):
    """Render the result of a bystander report submission."""
    triage = result.get("triage", {})
    priority = triage.get("priority", "P3")

    render_priority_banner(priority)
    render_incident_location_card(result)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🩺📋 What to do right now")
        first_aid = result.get("first_aid", {})
        steps = first_aid.get("steps", [])

        if steps:
            steps_md = "\n".join([f"{i}. {step}" for i, step in enumerate(steps, 1)])
            st.markdown(steps_md)
        else:
            st.info("No specific first-aid steps available.")

        do_not_do = first_aid.get("do_not_do", [])
        if do_not_do:
            do_not_md = "**🚫 Do NOT:**\n" + "\n".join([f"- {item}" for item in do_not_do])
            st.warning(do_not_md)

    with col2:
        st.markdown("### 🏥🚨 Hospital being alerted")
        hospital = result.get("hospital")

        if hospital:
            st.markdown(f"#### {hospital.get('name', 'Unknown Hospital')}")
            eta_min = hospital.get("eta_min")
            distance = hospital.get("distance_km", 0)

            mcols = st.columns(2)
            with mcols[0]:
                if eta_min is not None:
                    st.metric("⏱ ETA", f"{eta_min} min")
            with mcols[1]:
                st.metric("📏 Distance", f"{distance:.1f} km")

            match_reason = hospital.get("match_reason", "")
            if match_reason:
                st.caption(f"📌 {match_reason}")

            alternatives = hospital.get("alternatives", [])
            if alternatives:
                with st.expander(f"View {len(alternatives)} backup hospitals"):
                    for alt in alternatives:
                        st.markdown(
                            f"**{alt.get('name', 'Unknown')}** · "
                            f"{alt.get('distance_km', 0):.1f} km · "
                            f"ETA {alt.get('eta_min', '?')} min"
                        )
        else:
            st.error("No suitable hospital available.")

    st.markdown("---")
    render_map_with_pins(result)

    st.markdown("##### 🚨🧭 Supporting facilities")
    metrics_cols = st.columns(3)
    with metrics_cols[0]:
        pharmacy = result.get("nearest_pharmacy")
        if pharmacy:
            st.metric(
                "💊 Nearest Pharmacy",
                f"{pharmacy.get('distance_km', 0):.1f} km",
                f"ETA {pharmacy.get('eta_min', '?')} min"
            )
    with metrics_cols[1]:
        blood_bank = result.get("nearest_blood_bank")
        if blood_bank:
            st.metric(
                "🩸 Blood Bank",
                f"{blood_bank.get('distance_km', 0):.1f} km",
                f"ETA {blood_bank.get('eta_min', '?')} min"
            )
        else:
            st.caption("Blood bank not required for this priority")
    with metrics_cols[2]:
        agent_log = result.get("agent_log", [])
        if agent_log:
            total_time = sum(entry.get("duration_sec", 0) for entry in agent_log)
            st.metric("⚡ Processing Time", f"{total_time:.1f}s")

    st.markdown("---")
    decisions_html = f"""
    <div style="
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 16px 0;
    ">
        <div style="font-size: 0.85rem; color: #94A3B8; letter-spacing: 0.1em; text-transform: uppercase;">
            🤖 Decisions made by AI in seconds
        </div>
        <div style="display: flex; gap: 32px; margin-top: 12px; flex-wrap: wrap;">
            <div>
                <div style="color: #F1F5F9; font-size: 1.5rem; font-weight: 600;">{priority}</div>
                <div style="color: #64748B; font-size: 0.85rem;">Triage priority</div>
            </div>
            <div>
                <div style="color: #F1F5F9; font-size: 1.5rem; font-weight: 600;">{len(steps)}</div>
                <div style="color: #64748B; font-size: 0.85rem;">First-aid steps</div>
            </div>
            <div>
                <div style="color: #F1F5F9; font-size: 1.5rem; font-weight: 600;">{len(result.get('handoff', {}).get('preparation_checklist', []))}</div>
                <div style="color: #64748B; font-size: 0.85rem;">ER prep items</div>
            </div>
            <div>
                <div style="color: #F1F5F9; font-size: 1.5rem; font-weight: 600;">{len(result.get('handoff', {}).get('specialist_pages', []))}</div>
                <div style="color: #64748B; font-size: 0.85rem;">Specialists paged</div>
            </div>
        </div>
    </div>
    """
    st.markdown(decisions_html, unsafe_allow_html=True)

    # QR Code Section
    st.markdown("---")
    qr_col1, qr_col2 = st.columns([1, 1])

    with qr_col1:
        st.markdown("##### 📲 Paramedic Handoff QR")
        st.markdown("""
        Scan with any phone camera to get the full structured brief on the receiving device.

        **Encoded information:**
        - Priority & triage assessment
        - Hospital assignment & ETA
        - Vital signs & injuries
        - Preparation checklist (top 3)
        - Specialist calls
        - Anticipated interventions

        _Fully offline — no internet required_
        """)

    with qr_col2:
        try:
            summary = build_incident_summary(result)
            qr_png_bytes = render_qr_png(summary)
            st.image(qr_png_bytes, width=280, caption="Scan to get structured trauma brief")
        except Exception as e:
            st.error(f"Failed to generate QR code: {str(e)}")

    with st.expander("🤖 Triage details (auto-generated by watsonx.ai)"):
        st.json(triage)

    with st.expander("⏱ Pipeline timing"):
        agent_log = result.get("agent_log", [])
        if agent_log:
            df = pd.DataFrame(agent_log)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No timing information available.")


def render_bystander_view():
    """Render the bystander view for submitting accident reports."""
    st.markdown("# 🚑🆘 Report a Road Accident")
    st.warning(BYSTANDER_DISCLAIMER)

    with st.expander("🔌 Add New Data Source", expanded=False):
        st.markdown("**🏥 Upload new healthcare facility data**")
        st.caption("Add urgent-care clinics or other facilities that will appear on the coordination map")

        upload_cols = st.columns([1, 1])

        with upload_cols[0]:
            if st.button("📂 Load sample clinics", use_container_width=True):
                try:
                    adapter = ClinicsTextAdapter(text_path="data/clinics.txt")
                    clinics = adapter.load()
                    st.session_state.user_facilities["clinic"] = clinics
                    st.success(f"✅ Successfully ingested {len(clinics)} clinics")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load clinics: {str(e)}")

        with upload_cols[1]:
            if st.session_state.user_facilities:
                total_count = sum(len(facilities) for facilities in st.session_state.user_facilities.values())
                if st.button(f"🗑 Clear uploaded data ({total_count})", use_container_width=True):
                    st.session_state.user_facilities = {}
                    st.success("Cleared uploaded facilities")
                    st.rerun()

        st.markdown("**📝 Or paste raw facility data:**")
        raw_text = st.text_area(
            "Paste unstructured text with facility information",
            height=120,
            placeholder="Example: QuickCare Clinic, Bandra West, 19.0654, 72.8302, +91 22-26420789...",
            label_visibility="collapsed"
        )

        if st.button("🤖 Parse with watsonx.ai", use_container_width=True):
            if not raw_text.strip():
                st.warning("Please paste some text to parse")
            else:
                try:
                    with st.spinner("Parsing with watsonx.ai..."):
                        adapter = ClinicsTextAdapter(raw_text=raw_text)
                        clinics = adapter.load()
                        st.session_state.user_facilities["clinic"] = clinics
                        st.success(f"✅ Successfully ingested {len(clinics)} clinics")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to parse text: {str(e)}")

        # Show currently loaded facilities
        if st.session_state.user_facilities:
            for facility_type, facilities in st.session_state.user_facilities.items():
                if facilities:
                    type_label = facility_type.replace("_", " ").title() + "s"
                    st.markdown(f"**🩵 Loaded {type_label} ({len(facilities)})**")
                    for f in facilities:
                        name = f.get("name", "Unknown")
                        lat = f.get("lat", "?")
                        lon = f.get("lon", "?")
                        hours = f.get("hours", "")
                        services = f.get("services", [])
                        services_str = ", ".join(services) if services else ""

                        details = []
                        if hours:
                            details.append(f"🕐 {hours}")
                        if services_str:
                            details.append(f"🏷 {services_str}")
                        details.append(f"📍 {lat}, {lon}")

                        st.markdown(
                            f"- **{name}** — " + " · ".join(details)
                        )

            if not st.session_state.current_result:
                total_count = sum(len(facilities) for facilities in st.session_state.user_facilities.values())
                st.caption(f"📍 {total_count} facilities loaded. They'll appear on the map after you submit a bystander report.")

    with st.expander("🎙 Speak your report (Beta)", expanded=False):
        st.markdown("""
        Click the microphone, describe the accident, click stop. Transcription will fill the textarea below.

        _Runs locally with faster-whisper — no internet required for transcription_
        """)

        audio = mic_recorder(
            start_prompt="🔴 Start recording",
            stop_prompt="⏹ Stop recording",
            just_once=False,
            use_container_width=True,
            format="webm",
            key="bystander_voice_recorder",
        )

        if audio and audio.get("bytes"):
            # Only transcribe if we haven't already transcribed THIS recording
            audio_id = audio.get("id")
            if st.session_state.get("last_transcribed_audio_id") != audio_id:
                try:
                    with st.spinner("🤖 Transcribing locally with faster-whisper..."):
                        transcript = transcribe_audio_bytes(audio["bytes"])
                    if transcript:
                        st.session_state.sample_report = transcript
                        st.session_state.last_transcribed_audio_id = audio_id
                        st.success(f"✅ Transcribed {len(transcript.split())} words. Edit below if needed.")
                        st.rerun()
                    else:
                        st.warning("Audio captured but no speech detected. Try again.")
                except Exception as e:
                    st.error(f"Transcription failed: {e}")

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

    report_text = st.text_area(
        "Describe what you're seeing — be as detailed as you can",
        value=st.session_state.get("sample_report", ""),
        height=180,
        placeholder="Example: There's been a car accident. The driver is unconscious and bleeding from the head..."
    )

    if "sample_report" in st.session_state:
        del st.session_state.sample_report

    if st.button("🆘 Submit Report", type="primary", use_container_width=True):
        if not report_text.strip():
            st.error("Please describe the accident before submitting.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(stage_name, step, total):
            progress = step / total
            progress_bar.progress(progress)
            status_text.markdown(f"**[{step}/{total}]** {stage_name}...")

        try:
            with st.spinner("🤖 watsonx.ai agents processing..."):
                result = run_pipeline(
                    bystander_report=report_text,
                    incident_lat=DEFAULT_INCIDENT_LAT,
                    incident_lon=DEFAULT_INCIDENT_LON,
                    progress_callback=progress_callback
                )

                # Inject human-readable address (UI-side enrichment, doesn't require pipeline changes)
                if "incident_location" in result and isinstance(result["incident_location"], dict):
                    result["incident_location"]["address"] = DEFAULT_INCIDENT_ADDRESS

                st.session_state.current_result = result
                st.session_state.er_queue.append(result)

                progress_bar.empty()
                status_text.empty()

                st.success("✅ Report processed — coordinating response")
                st.rerun()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error processing report: {str(e)}")
            st.code(tb, language="python")
            print("=" * 60)
            print("PIPELINE ERROR:")
            print(tb)
            print("=" * 60)
            return

    if st.session_state.current_result:
        st.markdown("---")
        render_bystander_result(st.session_state.current_result)


def render_er_alert_card(result):
    """Render a single ER alert card for an incoming trauma."""
    triage = result.get("triage", {})
    priority = triage.get("priority", "P3")
    info = PRIORITY_INFO.get(priority, PRIORITY_INFO["P3"])
    handoff = result.get("handoff", {})
    hospital = result.get("hospital") or {}
    incident_loc = result.get("incident_location") or {}

    incoming_alert = handoff.get("incoming_alert", "Incoming trauma patient")
    hospital_name = hospital.get("name", "Unassigned")
    eta_min = hospital.get("eta_min", "?")
    incident_address = incident_loc.get("address", "Unknown location")

    pulse_class = "priority-banner-p1" if info["pulse"] else ""

    card_html = f"""
    <div class="{pulse_class}" style="
        border-left: 6px solid {info['color']};
        background: linear-gradient(90deg, {info['bg']}33 0%, #1E293B 60%);
        padding: 18px 22px;
        margin-bottom: 14px;
        border-radius: 8px;
        border-top: 1px solid #334155;
        border-right: 1px solid #334155;
        border-bottom: 1px solid #334155;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
            <div style="flex: 1;">
                <div style="
                    display: inline-block;
                    background-color: {info['color']};
                    color: white;
                    padding: 2px 10px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.05em;
                    margin-bottom: 8px;
                ">{priority} {info['label']}</div>
                <div style="font-weight: 600; font-size: 1.05rem; color: #F1F5F9; margin-bottom: 6px;">
                    {incoming_alert}
                </div>
                <div style="color: #94A3B8; font-size: 0.85rem;">
                    📍 {incident_address} → 🏥 {hospital_name} · ⏱ ETA {eta_min} min
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    with st.expander("📋 View full briefing"):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**📋 Preparation checklist**")
            for item in handoff.get("preparation_checklist", []) or ["No preparation items listed."]:
                st.markdown(f"- {item}")

            st.markdown("**📞 Specialist pages**")
            for s in handoff.get("specialist_pages", []) or ["No specialists to page."]:
                st.markdown(f"- {s}")

        with col2:
            st.markdown("**💉 Anticipated interventions**")
            for i in handoff.get("anticipated_interventions", []) or ["No interventions listed."]:
                st.markdown(f"- {i}")

            st.markdown("**❓ Information gaps for EMS handover**")
            for g in handoff.get("information_gaps", []) or ["No information gaps identified."]:
                st.markdown(f"- {g}")

        st.markdown("---")
        st.caption("**📝 Original bystander report:**")
        st.caption(f"_{result.get('bystander_report', 'No report available')}_")

        # Paramedic Handoff QR — same as bystander view, for ER scanning
        st.markdown("---")
        qr_cols = st.columns([2, 1])
        with qr_cols[0]:
            st.markdown("**📲 Paramedic / Trauma Team Handoff QR**")
            st.caption(
                "Scan with any phone camera to import the full structured brief — "
                "priority, hospital, vitals, prep checklist, specialist calls. Fully offline."
            )
        with qr_cols[1]:
            try:
                er_summary = build_incident_summary(result)
                er_qr_png = render_qr_png(er_summary)
                st.image(er_qr_png, width=220)
            except Exception as e:
                st.caption(f"_QR generation failed: {e}_")


def render_er_view():
    """Render the ER Trauma Bay view showing incoming patients."""
    st.markdown("# 🏥🚨 ER Trauma Bay — Incoming Patients")
    st.info(ER_DISCLAIMER)

    if not st.session_state.er_queue:
        st.info("No incoming traumas. Submit a bystander report from the Bystander view.")
        return

    priority_sort_key = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}

    sorted_queue = sorted(
        st.session_state.er_queue,
        key=lambda x: (
            priority_sort_key.get(x.get("triage", {}).get("priority", "P3"), 3),
            -datetime.fromisoformat(x.get("completed_at", "2000-01-01T00:00:00")).timestamp()
        )
    )

    counts = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for r in sorted_queue:
        p = r.get("triage", {}).get("priority", "P3")
        if p in counts:
            counts[p] += 1

    summary_cols = st.columns(4)
    for idx, (level, info) in enumerate(PRIORITY_INFO.items()):
        with summary_cols[idx]:
            st.markdown(
                f"""<div style="
                    background-color: {info['bg']};
                    border: 1px solid {info['color']};
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: center;
                ">
                    <div style="color: white; font-size: 1.8rem; font-weight: 700;">{counts[level]}</div>
                    <div style="color: rgba(255,255,255,0.85); font-size: 0.75rem; letter-spacing: 0.1em;">
                        {level} {info['label']}
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

    st.markdown("---")
    for result in sorted_queue:
        render_er_alert_card(result)


# ============================================================
# Router
# ============================================================
if view.startswith("🆘"):
    render_bystander_view()
else:
    render_er_view()