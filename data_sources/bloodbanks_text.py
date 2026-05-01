"""Text adapter for blood bank facility data using AI extraction.

This adapter reads unstructured text containing blood bank information and
uses IBM watsonx.ai's Granite model to extract structured data. It handles
messy human-written entries with varying formats for locations, hours, and
contact information.
"""

import os
import re
from typing import List, Dict, Any
from .adapter_base import FacilityAdapter
from utils.watsonx_client import watsonx_json


class BloodBanksTextAdapter(FacilityAdapter):
    """Adapter for loading blood bank data from unstructured text using AI.
    
    Uses IBM watsonx.ai's Granite Instruct model to parse human-written
    blood bank entries that may contain:
    - Names and locations (coordinates or addresses)
    - Phone numbers in various formats
    - Operating hours
    - Inventory notes and special services
    
    The AI model extracts structured records with standardized fields.
    """
    
    def __init__(self, text_path: str = "data/bloodbanks.txt"):
        """Initialize the adapter with a text file path.
        
        Args:
            text_path: Path to the blood banks text file
        """
        self.text_path = text_path
    
    def facility_type(self) -> str:
        """Return the facility type handled by this adapter.
        
        Returns:
            "blood_bank"
        """
        return "blood_bank"
    
    def load(self) -> List[Dict[str, Any]]:
        """Load and parse blood bank data from unstructured text using AI.
        
        Returns:
            List of blood bank dictionaries with standardized keys:
            - id (str): Auto-generated identifier (BB001, BB002, ...)
            - name (str): Blood bank name
            - lat (float): Latitude coordinate
            - lon (float): Longitude coordinate
            - type (str): Always "blood_bank"
            - phone (str, optional): Contact phone number
            - hours (str, optional): Operating hours
            - notes (str, optional): Additional information
        
        Raises:
            FileNotFoundError: If text file doesn't exist
            RuntimeError: If watsonx.ai credentials are not configured
            ValueError: If AI extraction fails or returns invalid data
        """
        if not os.path.exists(self.text_path):
            raise FileNotFoundError(f"Blood bank text file not found: {self.text_path}")
        
        # Read the text file
        try:
            with open(self.text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read blood bank text file: {e}")
        
        if not text_content.strip():
            raise ValueError("Blood bank text file is empty")
        
        # Use watsonx.ai to extract structured data
        try:
            extracted_data = self._extract_with_ai(text_content)
        except RuntimeError:
            # Re-raise RuntimeError for missing credentials
            raise
        except Exception as e:
            raise ValueError(f"Failed to extract blood bank data with AI: {e}")
        
        # Validate and process the extracted data
        if not isinstance(extracted_data, list):
            raise ValueError("AI extraction did not return a list of blood banks")
        
        if not extracted_data:
            raise ValueError("AI extraction returned no blood banks")
        
        # Process and standardize each blood bank record
        facilities = []
        for idx, bank in enumerate(extracted_data):
            try:
                facility = self._process_blood_bank(bank, idx)
                facilities.append(facility)
            except (KeyError, ValueError, TypeError) as e:
                # Log warning but continue with other records
                print(f"Warning: Skipping invalid blood bank at index {idx}: {e}")
                continue
        
        if not facilities:
            raise ValueError("No valid blood bank records could be extracted")
        
        return facilities
    
    def _extract_with_ai(self, text_content: str) -> List[Dict[str, Any]]:
        """Use watsonx.ai to extract structured blood bank data from text.
        
        Args:
            text_content: Raw text containing blood bank information
        
        Returns:
            List of dictionaries with extracted blood bank data
        
        Raises:
            RuntimeError: If watsonx.ai credentials are not configured
        """
        system_prompt = """You are a data extraction assistant. Extract blood bank information from unstructured text.
Return ONLY a JSON array of objects. Each object must have these exact keys:
- name: Blood bank name (string)
- lat: Latitude as decimal number (float)
- lon: Longitude as decimal number (float)
- phone: Phone number if present (string or null)
- hours: Operating hours if present (string or null)
- notes: Any additional relevant information (string or null)

Extract coordinates from formats like "19.0520N, 72.8510E" or "Lat 19.1145 / Long 72.8821".
Normalize phone numbers to a consistent format.
Be thorough but only include information explicitly stated in the text.
Return ONLY the JSON array, no explanations or markdown."""

        user_prompt = f"""Extract all blood bank records from this text:

{text_content}

Return a JSON array of blood bank objects."""

        # Call watsonx.ai
        try:
            result = watsonx_json(user_prompt, system_prompt)
        except RuntimeError as e:
            # Check if it's a credentials error
            if "credentials not configured" in str(e).lower():
                raise RuntimeError(
                    "watsonx.ai credentials not configured — see .env.example. "
                    "Required: WATSONX_API_KEY and WATSONX_PROJECT_ID"
                )
            raise
        
        return result
    
    def _process_blood_bank(self, bank: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process and validate a single blood bank record from AI extraction.
        
        Args:
            bank: Raw blood bank data from AI
            idx: Index for generating ID
        
        Returns:
            Standardized facility dictionary
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if 'name' not in bank or not bank['name']:
            raise ValueError("Missing or empty 'name' field")
        
        if 'lat' not in bank or bank['lat'] is None:
            raise ValueError("Missing 'lat' field")
        
        if 'lon' not in bank or bank['lon'] is None:
            raise ValueError("Missing 'lon' field")
        
        # Convert coordinates to float
        try:
            lat = float(bank['lat'])
            lon = float(bank['lon'])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate values: {e}")
        
        # Validate coordinate ranges
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude {lat} out of valid range [-90, 90]")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude {lon} out of valid range [-180, 180]")
        
        # Build standardized facility dict
        facility = {
            'id': f'BB{idx+1:03d}',  # BB001, BB002, etc.
            'name': str(bank['name']).strip(),
            'lat': lat,
            'lon': lon,
            'type': self.facility_type()
        }
        
        # Add optional fields if present and non-empty
        if bank.get('phone'):
            facility['phone'] = str(bank['phone']).strip()
        
        if bank.get('hours'):
            facility['hours'] = str(bank['hours']).strip()
        
        if bank.get('notes'):
            facility['notes'] = str(bank['notes']).strip()
        
        return facility


# Made with Bob
