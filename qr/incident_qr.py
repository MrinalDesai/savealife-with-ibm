"""
QR code generation for SaveAlife incident handoff.

Generates compact QR codes encoding structured trauma briefs that paramedics
or receiving hospitals can scan to instantly get critical incident information.
"""

import json
import io
from typing import Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def build_incident_summary(result: dict) -> dict:
    """
    Build a compact JSON-serializable summary from a pipeline result.
    
    Extracts only the most critical fields to keep QR code size manageable
    while preserving essential information for paramedic handoff.
    
    Args:
        result: Full pipeline result dict containing triage, handoff, hospital, etc.
        
    Returns:
        Compact dict with schema version, timestamp, priority, hospital info,
        injuries, vitals, specialists, prep checklist (top 3), interventions,
        and truncated bystander report.
    """
    # Derive priority label from numeric priority
    priority = result.get("triage", {}).get("priority", 4)
    priority_labels = {1: "IMMEDIATE", 2: "URGENT", 3: "DELAYED", 4: "MINOR"}
    priority_label = priority_labels.get(priority, "UNKNOWN")
    
    # Extract hospital info if present
    hospital_data = result.get("hospital")
    hospital_summary = None
    if hospital_data:
        hospital_summary = {
            "name": hospital_data.get("name", "Unknown"),
            "eta_min": hospital_data.get("eta_min"),
            "distance_km": round(hospital_data.get("distance_km", 0), 1),
            "match_reason": hospital_data.get("match_reason", "")
        }
    
    # Get handoff data
    handoff = result.get("handoff", {})
    prep_checklist = handoff.get("preparation_checklist", [])
    
    # Truncate bystander report if too long
    bystander_report = result.get("bystander_report", "")
    if len(bystander_report) > 200:
        report_excerpt = bystander_report[:200] + "..."
    else:
        report_excerpt = bystander_report
    
    # Build compact summary
    summary = {
        "v": 1,
        "ts": result.get("completed_at"),
        "priority": priority,
        "priority_label": priority_label,
        "alert": handoff.get("incoming_alert", ""),
        "hospital": hospital_summary,
        "injuries": result.get("triage", {}).get("primary_injuries", []),
        "consciousness": result.get("triage", {}).get("consciousness", ""),
        "bleeding": result.get("triage", {}).get("bleeding", ""),
        "specialists": handoff.get("specialist_pages", []),
        "prep_top3": prep_checklist[:3] if len(prep_checklist) > 3 else prep_checklist,
        "interventions": handoff.get("anticipated_interventions", []),
        "report_excerpt": report_excerpt
    }
    
    return summary


def render_qr_png(summary: dict, box_size: int = 8, border: int = 4) -> bytes:
    """
    Render a QR code as PNG bytes from an incident summary dict.
    
    Uses error correction level M (medium) for good balance of resilience
    and data density. Implements graceful degradation if the JSON payload
    exceeds QR code capacity by progressively truncating less critical fields.
    
    Args:
        summary: Incident summary dict from build_incident_summary()
        box_size: Size of each QR code box in pixels (default: 8)
        border: Border size in boxes (default: 4)
        
    Returns:
        PNG image as bytes, suitable for st.image() or file writing
    """
    # Maximum chars for QR v40 with error correction M (approximate)
    MAX_CHARS = 2900
    
    # Make a working copy to avoid mutating the original
    working_summary = summary.copy()
    
    # Serialize to compact JSON
    json_str = json.dumps(working_summary, separators=(",", ":"))
    
    # Graceful degradation if too large
    if len(json_str) > MAX_CHARS:
        # Step 1: Truncate report_excerpt further
        if len(working_summary.get("report_excerpt", "")) > 100:
            working_summary["report_excerpt"] = working_summary["report_excerpt"][:100] + "..."
            json_str = json.dumps(working_summary, separators=(",", ":"))
        
        # Step 2: Truncate interventions if still too large
        if len(json_str) > MAX_CHARS:
            interventions = working_summary.get("interventions", [])
            if len(interventions) > 3:
                working_summary["interventions"] = interventions[:3]
                json_str = json.dumps(working_summary, separators=(",", ":"))
        
        # Step 3: Reduce prep_top3 to top 2 if still too large
        if len(json_str) > MAX_CHARS:
            prep = working_summary.get("prep_top3", [])
            if len(prep) > 2:
                working_summary["prep_top3"] = prep[:2]
                json_str = json.dumps(working_summary, separators=(",", ":"))
        
        # Step 4: Last resort - truncate report_excerpt to 50 chars
        if len(json_str) > MAX_CHARS:
            working_summary["report_excerpt"] = working_summary.get("report_excerpt", "")[:50] + "..."
            json_str = json.dumps(working_summary, separators=(",", ":"))
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-select version based on data
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(json_str)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to PNG bytes
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    png_bytes = buffer.getvalue()
    
    return png_bytes

# Made with Bob
