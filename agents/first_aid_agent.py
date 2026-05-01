"""First-aid agent for generating safe bystander instructions.

This agent takes triage assessment data and produces clear, evidence-based
first-aid steps appropriate for untrained bystanders while waiting for
emergency services.
"""

from utils.watsonx_client import watsonx_json
from prompts import FIRST_AID_SYSTEM, FIRST_AID_PROMPT_TEMPLATE


class FirstAidAgent:
    """AI agent that generates safe first-aid instructions for bystanders.
    
    The agent produces step-by-step guidance based on triage assessment data,
    strictly adhering to established public first-aid protocols (Red Cross, WHO).
    All instructions are within bystander scope and emphasize calling emergency
    services first.
    """
    
    def run(self, triage_result: dict, bystander_report: str) -> dict:
        """Generate first-aid steps based on triage assessment.
        
        Args:
            triage_result: Structured triage assessment from TriageAgent
            bystander_report: Original free-text accident report
        
        Returns:
            Dictionary containing:
            - steps: List of numbered first-aid instructions (max 6 steps)
            - do_not_do: List of dangerous actions to avoid
            - call_emergency_now: Boolean (always True)
        """
        # Extract and format fields from triage result for the prompt
        priority = triage_result.get("priority", "unknown")
        
        # Format list fields as comma-separated strings
        primary_injuries = ", ".join(triage_result.get("primary_injuries", [])) or "unknown"
        consciousness = triage_result.get("consciousness", "unknown")
        bleeding = triage_result.get("bleeding", "unknown")
        mobility = triage_result.get("mobility", "unknown")
        special_considerations = ", ".join(triage_result.get("special_considerations", [])) or "none"
        
        # Format the prompt with all required fields
        prompt = FIRST_AID_PROMPT_TEMPLATE.format(
            priority=priority,
            primary_injuries=primary_injuries,
            consciousness=consciousness,
            bleeding=bleeding,
            mobility=mobility,
            special_considerations=special_considerations,
            bystander_report=bystander_report
        )
        
        # Call watsonx.ai to get structured JSON response
        try:
            result = watsonx_json(prompt=prompt, system=FIRST_AID_SYSTEM)
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
            Complete first-aid guidance with all required fields
        """
        # Default steps - always include emergency call instruction
        if "steps" not in result or not isinstance(result["steps"], list) or not result["steps"]:
            result["steps"] = ["Call emergency services (112) immediately."]
        
        # Ensure steps is a list of strings
        if isinstance(result["steps"], list):
            result["steps"] = [str(step) for step in result["steps"]]
        
        # Default do_not_do to empty list
        if "do_not_do" not in result or not isinstance(result["do_not_do"], list):
            result["do_not_do"] = []
        
        # Ensure do_not_do is a list of strings
        if isinstance(result["do_not_do"], list):
            result["do_not_do"] = [str(item) for item in result["do_not_do"]]
        
        # Always set call_emergency_now to True (critical safety requirement)
        result["call_emergency_now"] = True
        
        return result
    
    def _get_default_response(self, reason: str) -> dict:
        """Return a safe default response when LLM call fails.
        
        Args:
            reason: Explanation of why defaults are being used
        
        Returns:
            Complete first-aid guidance with safe default values
        """
        return {
            "steps": ["Call emergency services (112) immediately."],
            "do_not_do": [],
            "call_emergency_now": True
        }


# Made with Bob
