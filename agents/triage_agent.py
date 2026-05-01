"""Triage agent for assessing accident severity and extracting clinical information.

This agent analyzes bystander accident reports and produces structured triage
assessments using established emergency protocols (ESI and START).
"""

from utils.watsonx_client import watsonx_json
from prompts import TRIAGE_SYSTEM, TRIAGE_PROMPT_TEMPLATE


class TriageAgent:
    """AI agent that classifies accident severity and extracts clinical indicators.
    
    The agent processes free-text bystander reports and returns structured
    triage data including priority level (P1-P4), victim count, injuries,
    consciousness level, bleeding status, and other clinical indicators.
    """
    
    def run(self, bystander_report: str) -> dict:
        """Analyze a bystander accident report and produce a triage assessment.
        
        Args:
            bystander_report: Free-text description of the accident from a bystander
        
        Returns:
            Dictionary containing structured triage assessment with fields:
            - priority: P1/P2/P3/P4 classification
            - priority_reason: Clinical reasoning for the classification
            - victim_count: Number of victims
            - primary_injuries: List of observed injuries
            - consciousness: ALERT/DISORIENTED/UNCONSCIOUS/UNKNOWN
            - bleeding: NONE/MINOR/MODERATE/SEVERE/UNKNOWN
            - mobility: WALKING/LIMITED/IMMOBILE/UNKNOWN
            - suspected_systems: List of affected body systems
            - special_considerations: List of special factors (age, pregnancy, etc.)
            - specialty_needed: List of medical specialties that may be needed
            - confidence: Float 0.0-1.0 indicating assessment confidence
            - missing_information: List of information gaps
        """
        # Format the prompt with the bystander report
        prompt = TRIAGE_PROMPT_TEMPLATE.format(bystander_report=bystander_report)
        
        # Call watsonx.ai to get structured JSON response
        try:
            result = watsonx_json(prompt=prompt, system=TRIAGE_SYSTEM)
        except Exception as e:
            # If LLM call fails, return safe defaults
            return self._get_default_response(f"LLM error: {str(e)}")
        
        # Apply defaults for any missing fields
        return self._apply_defaults(result)
    
    def _apply_defaults(self, result: dict) -> dict:
        """Apply sensible defaults for any missing fields in the LLM response.
        
        Args:
            result: Raw response from watsonx.ai
        
        Returns:
            Complete triage assessment with all required fields
        """
        # Default to P2 (urgent) if priority is missing - safer to over-triage
        if "priority" not in result or result["priority"] not in ["P1", "P2", "P3", "P4"]:
            result["priority"] = "P2"
        
        # Default priority reason
        if "priority_reason" not in result or not result["priority_reason"]:
            result["priority_reason"] = "Insufficient information; defaulting to urgent."
        
        # Default victim count
        if "victim_count" not in result or not isinstance(result["victim_count"], int):
            result["victim_count"] = 1
        
        # Default list fields to empty lists
        if "primary_injuries" not in result or not isinstance(result["primary_injuries"], list):
            result["primary_injuries"] = []
        
        if "suspected_systems" not in result or not isinstance(result["suspected_systems"], list):
            result["suspected_systems"] = []
        
        if "special_considerations" not in result or not isinstance(result["special_considerations"], list):
            result["special_considerations"] = []
        
        if "specialty_needed" not in result or not isinstance(result["specialty_needed"], list):
            result["specialty_needed"] = []
        
        if "missing_information" not in result or not isinstance(result["missing_information"], list):
            result["missing_information"] = []
        
        # Default enum fields to UNKNOWN
        valid_consciousness = ["ALERT", "DISORIENTED", "UNCONSCIOUS", "UNKNOWN"]
        if "consciousness" not in result or result["consciousness"] not in valid_consciousness:
            result["consciousness"] = "UNKNOWN"
        
        valid_bleeding = ["NONE", "MINOR", "MODERATE", "SEVERE", "UNKNOWN"]
        if "bleeding" not in result or result["bleeding"] not in valid_bleeding:
            result["bleeding"] = "UNKNOWN"
        
        valid_mobility = ["WALKING", "LIMITED", "IMMOBILE", "UNKNOWN"]
        if "mobility" not in result or result["mobility"] not in valid_mobility:
            result["mobility"] = "UNKNOWN"
        
        # Default confidence to 0.5 if missing or invalid
        if "confidence" not in result or not isinstance(result["confidence"], (int, float)):
            result["confidence"] = 0.5
        else:
            # Clamp confidence to 0.0-1.0 range
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        
        return result
    
    def _get_default_response(self, reason: str) -> dict:
        """Return a safe default response when LLM call fails.
        
        Args:
            reason: Explanation of why defaults are being used
        
        Returns:
            Complete triage assessment with safe default values
        """
        return {
            "priority": "P2",
            "priority_reason": f"Insufficient information; defaulting to urgent. {reason}",
            "victim_count": 1,
            "primary_injuries": [],
            "consciousness": "UNKNOWN",
            "bleeding": "UNKNOWN",
            "mobility": "UNKNOWN",
            "suspected_systems": [],
            "special_considerations": [],
            "specialty_needed": [],
            "confidence": 0.5,
            "missing_information": ["Unable to process report"]
        }


# Made with Bob
