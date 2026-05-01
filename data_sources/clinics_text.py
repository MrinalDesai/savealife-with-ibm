"""Text adapter for urgent-care clinic facility data using AI extraction.

This adapter reads unstructured text containing urgent-care clinic information and
uses IBM watsonx.ai's Granite model to extract structured data. It handles
messy human-written entries with varying formats for locations, hours, and
services. Supports both file-based loading and direct raw text input for
live data ingestion through the UI.
"""

import os
from typing import List, Dict, Any, Optional
from .adapter_base import FacilityAdapter
from utils.watsonx_client import watsonx_json


class ClinicsTextAdapter(FacilityAdapter):
    """Adapter for loading urgent-care clinic data from unstructured text using AI.
    
    Uses IBM watsonx.ai's Granite Instruct model to parse human-written
    clinic entries that may contain:
    - Names and locations (coordinates or neighborhood names)
    - Phone numbers in various formats
    - Operating hours (casual prose or structured)
    - Services offered (x-ray, minor procedures, vaccinations, etc.)
    
    The AI model extracts structured records with standardized fields and can
    estimate coordinates from Mumbai neighborhood names when explicit coordinates
    are not provided.
    """
    
    def __init__(self, raw_text: Optional[str] = None, text_path: str = "data/clinics.txt"):
        """Initialize the adapter with either raw text or a file path.
        
        Args:
            raw_text: Optional raw text content to parse (for UI upload flow)
            text_path: Path to the clinics text file (used if raw_text is None)
        """
        self.raw_text = raw_text
        self.text_path = text_path
    
    def facility_type(self) -> str:
        """Return the facility type handled by this adapter.
        
        Returns:
            "clinic"
        """
        return "clinic"
    
    def load(self) -> List[Dict[str, Any]]:
        """Load and parse clinic data from unstructured text using AI.
        
        Returns:
            List of clinic dictionaries with standardized keys:
            - id (str): Auto-generated identifier (CL001, CL002, ...)
            - name (str): Clinic name
            - lat (float): Latitude coordinate
            - lon (float): Longitude coordinate
            - type (str): Always "clinic"
            - phone (str, optional): Contact phone number
            - hours (str, optional): Operating hours
            - services (list, optional): List of services offered
            - notes (str, optional): Additional information
        
        Raises:
            FileNotFoundError: If text file doesn't exist (when using file path)
            RuntimeError: If watsonx.ai credentials are not configured
            ValueError: If AI extraction fails or returns invalid data
        """
        # Get text content from either raw_text or file
        if self.raw_text is not None:
            text_content = self.raw_text
        else:
            if not os.path.exists(self.text_path):
                raise FileNotFoundError(f"Clinic text file not found: {self.text_path}")
            
            try:
                with open(self.text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read clinic text file: {e}")
        
        if not text_content.strip():
            raise ValueError("Clinic text content is empty")
        
        # Use watsonx.ai to extract structured data
        try:
            extracted_data = self._extract_with_ai(text_content)
        except RuntimeError:
            # Re-raise RuntimeError for missing credentials
            raise
        except Exception as e:
            raise ValueError(f"Failed to extract clinic data with AI: {e}")
        
        # Validate and process the extracted data
        if not isinstance(extracted_data, list):
            raise ValueError("AI extraction did not return a list of clinics")
        
        if not extracted_data:
            raise ValueError("AI extraction returned no clinics")
        
        # Process and standardize each clinic record
        facilities = []
        for idx, clinic in enumerate(extracted_data):
            try:
                facility = self._process_clinic(clinic, idx)
                facilities.append(facility)
            except (KeyError, ValueError, TypeError) as e:
                # Log warning but continue with other records
                print(f"Warning: Skipping invalid clinic at index {idx}: {e}")
                continue
        
        if not facilities:
            raise ValueError("No valid clinic records could be extracted")
        
        return facilities
    
    def _extract_with_ai(self, text_content: str) -> List[Dict[str, Any]]:
        """Use watsonx.ai to extract structured clinic data from text.
        
        Args:
            text_content: Raw text containing clinic information
        
        Returns:
            List of dictionaries with extracted clinic data
        
        Raises:
            RuntimeError: If watsonx.ai credentials are not configured
        """
        system_prompt = """You are a data extraction assistant specializing in healthcare facility data. Extract urgent-care clinic information from unstructured text.

Return ONLY a JSON array of objects. Each object must have these exact keys:
- name: Clinic name (string)
- lat: Latitude as decimal number (float) - if not explicitly provided, estimate from Mumbai neighborhood name using your knowledge of Mumbai geography
- lon: Longitude as decimal number (float) - if not explicitly provided, estimate from Mumbai neighborhood name using your knowledge of Mumbai geography
- phone: Phone number if present (string or null)
- hours: Operating hours if present, normalized to readable format (string or null)
- services: List of services offered like x-ray, minor procedures, vaccinations, etc. (array of strings or null)
- notes: Any additional relevant information (string or null)

For Mumbai neighborhoods without explicit coordinates, use these approximate ranges:
- Latitude: 19.0 to 19.15
- Longitude: 72.82 to 72.88

Common Mumbai neighborhoods and approximate coordinates:
- Bandra West: 19.0596, 72.8295
- Khar West: 19.0728, 72.8345
- Santacruz: 19.0825, 72.8417
- Andheri East: 19.1136, 72.8697
- Juhu: 19.1075, 72.8263
- Vile Parle: 19.1076, 72.8429

Extract coordinates from formats like "19.0654, 72.8302" or "Lat 19.0654 / Long 72.8302" or neighborhood names.
Normalize phone numbers to international format if possible.
Parse casual operating hours like "open 7am to midnight" or "24/7 except Sundays".
Extract services from casual mentions like "x-ray onsite, minor procedures, vaccination available".
Be thorough but only include information explicitly stated in the text.
Return ONLY the JSON array, no explanations or markdown."""

        user_prompt = f"""Extract all urgent-care clinic records from this text:

{text_content}

Return a JSON array of clinic objects with valid coordinates."""

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
    
    def _process_clinic(self, clinic: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process and validate a single clinic record from AI extraction.
        
        Args:
            clinic: Raw clinic data from AI
            idx: Index for generating ID
        
        Returns:
            Standardized facility dictionary
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if 'name' not in clinic or not clinic['name']:
            raise ValueError("Missing or empty 'name' field")
        
        if 'lat' not in clinic or clinic['lat'] is None:
            raise ValueError("Missing 'lat' field")
        
        if 'lon' not in clinic or clinic['lon'] is None:
            raise ValueError("Missing 'lon' field")
        
        # Convert coordinates to float
        try:
            lat = float(clinic['lat'])
            lon = float(clinic['lon'])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate values: {e}")
        
        # Validate coordinate ranges
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude {lat} out of valid range [-90, 90]")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude {lon} out of valid range [-180, 180]")
        
        # Build standardized facility dict
        facility = {
            'id': f'CL{idx+1:03d}',  # CL001, CL002, etc.
            'name': str(clinic['name']).strip(),
            'lat': lat,
            'lon': lon,
            'type': self.facility_type()
        }
        
        # Add optional fields if present and non-empty
        if clinic.get('phone'):
            facility['phone'] = str(clinic['phone']).strip()
        
        if clinic.get('hours'):
            facility['hours'] = str(clinic['hours']).strip()
        
        if clinic.get('services') and isinstance(clinic['services'], list):
            facility['services'] = [str(s).strip() for s in clinic['services'] if s]
        
        if clinic.get('notes'):
            facility['notes'] = str(clinic['notes']).strip()
        
        return facility


# Made with Bob