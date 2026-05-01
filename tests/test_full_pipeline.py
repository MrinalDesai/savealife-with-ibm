"""End-to-end test for the complete SaveAlife pipeline orchestrator.

This test demonstrates the full pipeline: load facilities → triage → find hospital →
first-aid → ER handoff. It uses a realistic P1-level trauma scenario near Bandra.
"""

import os
import sys
import json

# Add parent directory to path to import pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline import run_pipeline


def progress_callback(stage: str, step: int, total: int):
    """Print progress updates as the pipeline runs."""
    print(f"[{step}/{total}] {stage}...")


def test_full_pipeline_e2e():
    """Test the complete SaveAlife pipeline end-to-end."""
    
    # Check if watsonx credentials are configured
    if not os.getenv("WATSONX_API_KEY"):
        print("=" * 80)
        print("⚠️  SKIPPING TEST — WATSONX_API_KEY not configured")
        print("=" * 80)
        print()
        print("To run this test:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your IBM watsonx.ai credentials")
        print("  3. Run this test again")
        print()
        return
    
    print("=" * 80)
    print("SaveAlife Complete Pipeline End-to-End Test")
    print("=" * 80)
    print()
    
    # Sample bystander report - P1 level scenario (life-threatening)
    bystander_report = (
        "A motorcycle hit a divider near Bandra. The rider is on the ground, not moving. "
        "He's breathing but barely conscious. There's blood near his head."
    )
    
    # Incident location near Bandra
    incident_lat = 19.0590
    incident_lon = 72.8295
    
    print("📝 BYSTANDER REPORT:")
    print(f"   {bystander_report}")
    print()
    print(f"📍 INCIDENT LOCATION:")
    print(f"   Latitude: {incident_lat}")
    print(f"   Longitude: {incident_lon}")
    print()
    
    print("-" * 80)
    print("🚀 RUNNING PIPELINE")
    print("-" * 80)
    print()
    
    # Run the complete pipeline
    try:
        result = run_pipeline(
            bystander_report=bystander_report,
            incident_lat=incident_lat,
            incident_lon=incident_lon,
            progress_callback=progress_callback
        )
        print()
        print("✅ Pipeline completed successfully")
        print()
    except Exception as e:
        print()
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Pretty-print the complete result
    print("=" * 80)
    print("📊 COMPLETE PIPELINE RESULT")
    print("=" * 80)
    print()
    
    # Use json.dumps with default=str to handle any non-serializable objects
    print(json.dumps(result, indent=2, default=str))
    print()
    
    # Print summary
    print("=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print()
    
    triage = result.get("triage", {})
    hospital = result.get("hospital")
    first_aid = result.get("first_aid", {})
    handoff = result.get("handoff", {})
    pharmacy = result.get("nearest_pharmacy")
    blood_bank = result.get("nearest_blood_bank")
    warnings = result.get("warnings", [])
    agent_log = result.get("agent_log", [])
    
    print(f"⏱️  Total Duration:")
    if agent_log:
        total_duration = sum(log.get("duration_sec", 0) for log in agent_log)
        print(f"   {total_duration:.2f} seconds")
    print()
    
    print(f"🚨 Triage Assessment:")
    print(f"   Priority: {triage.get('priority', 'unknown')}")
    print(f"   Victim count: {triage.get('victim_count', 'unknown')}")
    print(f"   Consciousness: {triage.get('consciousness', 'unknown')}")
    print(f"   Bleeding: {triage.get('bleeding', 'unknown')}")
    print(f"   Confidence: {triage.get('confidence', 0):.2f}")
    print()
    
    print(f"🏥 Hospital Assignment:")
    if hospital:
        print(f"   Name: {hospital.get('name', 'unknown')}")
        print(f"   Distance: {hospital.get('distance_km', 0):.1f} km")
        print(f"   ETA: {hospital.get('eta_min', '?')} minutes")
        print(f"   Match score: {hospital.get('match_score', 0):.3f}")
        print(f"   Reason: {hospital.get('match_reason', 'N/A')}")
        alternatives = hospital.get('alternatives', [])
        if alternatives:
            print(f"   Alternatives: {len(alternatives)} other hospitals")
    else:
        print("   ⚠️  No suitable hospital found")
    print()
    
    print(f"🩹 First-Aid Instructions:")
    steps = first_aid.get('steps', [])
    print(f"   Steps provided: {len(steps)}")
    if steps:
        for i, step in enumerate(steps[:3], 1):  # Show first 3 steps
            print(f"   {i}. {step[:60]}{'...' if len(step) > 60 else ''}")
    print()
    
    print(f"📞 ER Handoff Brief:")
    print(f"   Alert: {handoff.get('incoming_alert', 'N/A')}")
    print(f"   Preparation items: {len(handoff.get('preparation_checklist', []))}")
    print(f"   Specialists to page: {len(handoff.get('specialist_pages', []))}")
    print(f"   Anticipated interventions: {len(handoff.get('anticipated_interventions', []))}")
    print()
    
    print(f"💊 Nearest Pharmacy:")
    if pharmacy:
        print(f"   Name: {pharmacy.get('name', 'unknown')}")
        print(f"   Distance: {pharmacy.get('distance_km', 0):.1f} km")
        print(f"   ETA: {pharmacy.get('eta_min', '?')} minutes")
    else:
        print("   ⚠️  No pharmacy data available")
    print()
    
    print(f"🩸 Nearest Blood Bank:")
    if blood_bank:
        print(f"   Name: {blood_bank.get('name', 'unknown')}")
        print(f"   Distance: {blood_bank.get('distance_km', 0):.1f} km")
        print(f"   ETA: {blood_bank.get('eta_min', '?')} minutes")
    else:
        priority = triage.get('priority', 'unknown')
        if priority in ['P1', 'P2']:
            print("   ⚠️  No blood bank data available (needed for P1/P2)")
        else:
            print("   N/A (not needed for this priority)")
    print()
    
    if warnings:
        print(f"⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
        print()
    
    print("=" * 80)
    print("✅ END-TO-END TEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    test_full_pipeline_e2e()


# Made with Bob