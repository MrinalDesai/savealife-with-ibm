"""ER handoff agent for generating pre-arrival hospital briefings.

This agent produces structured trauma team briefings based on triage data,
enabling hospitals to prepare appropriate resources before patient arrival.
"""

from utils.watsonx_client import watsonx_json
from prompts import HANDOFF_SYSTEM, HANDOFF_PROMPT_TEMPLATE


# Priority label mapping
PRIORITY_LABELS = {
    "P1": "IMMEDIATE",
    "P2": "URGENT",
    "P3": "DELAYED",
    "P4": "MINOR"
}


class ERHandoffAgent:
    """AI agent that generates pre-arrival briefings for hospital trauma teams.
    
    The agent produces concise, structured information to help emergency
    departments prepare the right bay, equipment, specialists, and blood
    products before the patient arrives.
    """
    
    def run(self, triage_result: dict, hospital: dict) -> dict:
        """Generate a pre-arrival trauma brief for the receiving hospital.
        
        Args:
            triage_result: Structured triage assessment from TriageAgent
            hospital: Hospital information dict with at least 'name' and optionally 'eta_min'
        
        Returns:
            Dictionary containing:
            - incoming_alert: One-line headline for trauma board (under 80 chars)
            - preparation_checklist: List of specific prep items needed
            - specialist_pages: List of specialties to page immediately
            - anticipated_interventions: List of likely first interventions
            - information_gaps: List of critical info to ask EMS crew on handover
        """
        # Extract fields from triage result
        priority = triage_result.get("priority", "P2")
        priority_label = PRIORITY_LABELS.get(priority, "URGENT")
        victim_count = triage_result.get("victim_count", 1)
        
        # Extract hospital information
        hospital_name = hospital.get("name", "Unknown Hospital")
        eta_min = hospital.get("eta_min", "?")
        
        # Format list fields as comma-separated strings
        primary_injuries = ", ".join(triage_result.get("primary_injuries", [])) or "unknown"
        consciousness = triage_result.get("consciousness", "unknown")
        bleeding = triage_result.get("bleeding", "unknown")
        mobility = triage_result.get("mobility", "unknown")
        suspected_systems = ", ".join(triage_result.get("suspected_systems", [])) or "unknown"
        special_considerations = ", ".join(triage_result.get("special_considerations", [])) or "none"
        specialty_needed = ", ".join(triage_result.get("specialty_needed", [])) or "none"
        
        # Format the prompt with all required fields
        prompt = HANDOFF_PROMPT_TEMPLATE.format(
            priority=priority,
            priority_label=priority_label,
            eta_min=eta_min,
            hospital_name=hospital_name,
            victim_count=victim_count,
            primary_injuries=primary_injuries,
            consciousness=consciousness,
            bleeding=bleeding,
            mobility=mobility,
            suspected_systems=suspected_systems,
            special_considerations=special_considerations,
            specialty_needed=specialty_needed
        )
        
        # Call watsonx.ai to get structured JSON response
        try:
            result = watsonx_json(prompt=prompt, system=HANDOFF_SYSTEM)
        except Exception as e:
            # If LLM call fails, return safe defaults
            return self._get_default_response(priority, priority_label)
        
        # Apply defaults for any missing fields
        return self._apply_defaults(result, priority, priority_label)
    
    def _apply_defaults(self, result: dict, priority: str, priority_label: str) -> dict:
        """Apply sensible defaults for any missing fields in the LLM response.
        
        Args:
            result: Raw response from watsonx.ai
            priority: Priority level (P1-P4)
            priority_label: Human-readable priority label
        
        Returns:
            Complete handoff brief with all required fields
        """
        # Default incoming alert
        if "incoming_alert" not in result or not result["incoming_alert"]:
            result["incoming_alert"] = f"{priority} trauma incoming"
        
        # Ensure incoming_alert is a string and not too long
        if isinstance(result["incoming_alert"], str):
            result["incoming_alert"] = result["incoming_alert"][:80]
        else:
            result["incoming_alert"] = f"{priority} trauma incoming"
        
        # Default list fields to empty lists
        if "preparation_checklist" not in result or not isinstance(result["preparation_checklist"], list):
            result["preparation_checklist"] = []
        
        if "specialist_pages" not in result or not isinstance(result["specialist_pages"], list):
            result["specialist_pages"] = []
        
        if "anticipated_interventions" not in result or not isinstance(result["anticipated_interventions"], list):
            result["anticipated_interventions"] = []
        
        if "information_gaps" not in result or not isinstance(result["information_gaps"], list):
            result["information_gaps"] = []
        
        # Ensure all list fields contain strings
        result["preparation_checklist"] = [str(item) for item in result["preparation_checklist"]]
        result["specialist_pages"] = [str(item) for item in result["specialist_pages"]]
        result["anticipated_interventions"] = [str(item) for item in result["anticipated_interventions"]]
        result["information_gaps"] = [str(item) for item in result["information_gaps"]]
        
        return result
    
    def _get_default_response(self, priority: str, priority_label: str) -> dict:
        """Return a safe default response when LLM call fails.
        
        Args:
            priority: Priority level (P1-P4)
            priority_label: Human-readable priority label
        
        Returns:
            Complete handoff brief with safe default values
        """
        return {
            "incoming_alert": f"{priority} trauma incoming",
            "preparation_checklist": [],
            "specialist_pages": [],
            "anticipated_interventions": [],
            "information_gaps": []
        }


# Made with Bob
