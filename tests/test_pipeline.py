"""Integration test for the SaveAlife AI agent pipeline.

This test demonstrates the complete flow: bystander report → triage → first-aid → ER handoff.
It uses a realistic P1-level trauma scenario to verify all three agents work together.
"""

import os
import sys
import json

# Add parent directory to path to import agents
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.triage_agent import TriageAgent
from agents.first_aid_agent import FirstAidAgent
from agents.handoff_agent import ERHandoffAgent


def test_full_pipeline():
    """Test the complete SaveAlife pipeline with all three agents."""
    
    # Check if watsonx credentials are configured
    if not os.getenv("WATSONX_API_KEY"):
        print("⚠️  WATSONX_API_KEY not set — skipping pipeline test")
        print("   Set credentials in .env to run this test")
        return
    
    print("=" * 80)
    print("SaveAlife AI Pipeline Integration Test")
    print("=" * 80)
    print()
    
    # Sample bystander report - P1 level scenario (life-threatening)
    bystander_report = (
        "A motorcycle hit a divider near Bandra. The rider is on the ground, not moving. "
        "He's breathing but barely conscious. There's blood near his head."
    )
    
    print("📝 BYSTANDER REPORT:")
    print(f"   {bystander_report}")
    print()
    
    # Step 1: Triage Agent
    print("-" * 80)
    print("🔍 STEP 1: TRIAGE ASSESSMENT")
    print("-" * 80)
    
    triage_agent = TriageAgent()
    try:
        triage_result = triage_agent.run(bystander_report)
        print("✅ Triage completed successfully")
        print()
        print("Triage Result:")
        print(json.dumps(triage_result, indent=2))
        print()
    except Exception as e:
        print(f"❌ Triage failed: {e}")
        return
    
    # Step 2: First-Aid Agent
    print("-" * 80)
    print("🩹 STEP 2: FIRST-AID INSTRUCTIONS")
    print("-" * 80)
    
    first_aid_agent = FirstAidAgent()
    try:
        first_aid_result = first_aid_agent.run(triage_result, bystander_report)
        print("✅ First-aid guidance generated successfully")
        print()
        print("First-Aid Result:")
        print(json.dumps(first_aid_result, indent=2))
        print()
    except Exception as e:
        print(f"❌ First-aid generation failed: {e}")
        return
    
    # Step 3: ER Handoff Agent
    print("-" * 80)
    print("🏥 STEP 3: ER HANDOFF BRIEF")
    print("-" * 80)
    
    # Mock hospital data
    hospital = {
        "name": "KEM Hospital",
        "eta_min": 7
    }
    
    handoff_agent = ERHandoffAgent()
    try:
        handoff_result = handoff_agent.run(triage_result, hospital)
        print("✅ ER handoff brief generated successfully")
        print()
        print("Handoff Result:")
        print(json.dumps(handoff_result, indent=2))
        print()
    except Exception as e:
        print(f"❌ ER handoff generation failed: {e}")
        return
    
    # Summary
    print("=" * 80)
    print("✅ PIPELINE TEST COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Priority: {triage_result.get('priority', 'unknown')}")
    print(f"  • Victim count: {triage_result.get('victim_count', 'unknown')}")
    print(f"  • First-aid steps: {len(first_aid_result.get('steps', []))}")
    print(f"  • Specialists to page: {len(handoff_result.get('specialist_pages', []))}")
    print()


if __name__ == "__main__":
    test_full_pipeline()


# Made with Bob