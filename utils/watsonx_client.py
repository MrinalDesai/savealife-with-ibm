"""IBM watsonx.ai SDK wrapper for LLM inference.

This module provides a simple interface to IBM's watsonx.ai foundation models,
specifically designed for the SaveAlife emergency response system. It handles
credential management and provides convenient functions for both text and JSON
responses.
"""

import os
import json
import re
from typing import Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_credentials() -> tuple[str, str, str]:
    """Get watsonx.ai credentials from environment variables.
    
    Returns:
        Tuple of (api_key, project_id, url)
    
    Raises:
        RuntimeError: If any required credentials are missing
    """
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    
    if not api_key or not project_id:
        raise RuntimeError(
            "watsonx.ai credentials not configured — see .env.example. "
            "Required: WATSONX_API_KEY and WATSONX_PROJECT_ID"
        )
    
    return api_key, project_id, url


def _get_model_client(model_id: str = "ibm/granite-4-h-small"):
    """Create and return a watsonx.ai model inference client.
    
    Args:
        model_id: The model identifier to use
    
    Returns:
        ModelInference client instance
    
    Raises:
        RuntimeError: If credentials are not configured
    """
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    
    api_key, project_id, url = _get_credentials()
    
    credentials = Credentials(
        api_key=api_key,
        url=url
    )
    
    model = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={
            # "decoding_method": "greedy",
            "max_new_tokens": 1500,
            "temperature": 0.1
        }
    )
    
    return model


# def watsonx_chat(
#     prompt: str,
#     system: str = "",
#     model_id: Optional[str] = None
# ) -> str:
#     """Send a prompt to watsonx.ai and return the raw text response.
    
#     Args:
#         prompt: The user prompt/question
#         system: Optional system message to guide model behavior
#         model_id: Optional model identifier (defaults to granite-4-h-small)
    
#     Returns:
#         Raw text response from the model
    
#     Raises:
#         RuntimeError: If watsonx.ai credentials are not configured
#     """
#     if model_id is None:
#         model_id = "ibm/granite-4-h-small"
    
#     model = _get_model_client(model_id)
    
#     # Construct the full prompt with system message if provided
#     full_prompt = prompt
#     if system:
#         full_prompt = f"{system}\n\n{prompt}"
    
#     response = model.generate_text(prompt=full_prompt)
#     return response

def watsonx_chat(
    prompt: str,
    system: str = "",
    model_id: Optional[str] = None
) -> str:
    """Send a prompt to watsonx.ai and return the raw text response.
    
    Uses the chat completions API for instruction-tuned chat models like
    Granite 4 H Small.
    """
    if model_id is None:
        model_id = "ibm/granite-4-h-small"
    
    model = _get_model_client(model_id)
    
    # Build chat-format messages
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    # Use chat API (correct shape for Granite 4 H Small)
    response = model.chat(messages=messages)
    
    # Extract text from chat response structure
    if isinstance(response, dict):
        choices = response.get("choices", [])
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if content:
                return content
    
    return str(response) if response else ""

def watsonx_json(
    prompt: str,
    system: str = "",
    model_id: Optional[str] = None
) -> Any:
    """Send a prompt to watsonx.ai and return parsed JSON response.
    
    This function is tolerant of common LLM output issues:
    - Strips markdown code fences (```json ... ```)
    - Finds the first [ or { and last ] or } if there's prefix/suffix text
    - Handles both JSON objects and arrays
    
    Args:
        prompt: The user prompt/question
        system: Optional system message to guide model behavior
        model_id: Optional model identifier (defaults to granite-3-8b-instruct)
    
    Returns:
        Parsed JSON (dict, list, or other JSON-compatible type)
    
    Raises:
        RuntimeError: If watsonx.ai credentials are not configured
        json.JSONDecodeError: If response cannot be parsed as JSON
    """
    response_text = watsonx_chat(prompt, system, model_id)
    
    # Strip markdown code fences if present
    response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'\n?```\s*$', '', response_text, flags=re.MULTILINE)
    
    # Find the first [ or { and last ] or }
    # This handles cases where the model adds explanatory text before/after JSON
    start_array = response_text.find('[')
    start_object = response_text.find('{')
    
    # Determine which comes first (or if only one exists)
    if start_array == -1 and start_object == -1:
        # No JSON structure found, try parsing as-is
        return json.loads(response_text.strip())
    
    if start_array == -1:
        start_pos = start_object
        end_char = '}'
    elif start_object == -1:
        start_pos = start_array
        end_char = ']'
    else:
        # Both exist, use whichever comes first
        if start_array < start_object:
            start_pos = start_array
            end_char = ']'
        else:
            start_pos = start_object
            end_char = '}'
    
    # Find the last occurrence of the closing character
    end_pos = response_text.rfind(end_char)
    
    if end_pos == -1 or end_pos < start_pos:
        # Malformed JSON, try parsing as-is
        return json.loads(response_text.strip())
    
    # Extract and parse the JSON portion
    json_text = response_text[start_pos:end_pos + 1]
    return json.loads(json_text)


# Made with Bob
