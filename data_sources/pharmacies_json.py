"""JSON adapter for pharmacy facility data.

This adapter reads pharmacy data from JSON files and converts it into the
standardized facility format. It handles both flat and nested coordinate
structures and supports multiple JSON shapes.
"""

import os
import json
from typing import List, Dict, Any
from .adapter_base import FacilityAdapter


class PharmaciesJsonAdapter(FacilityAdapter):
    """Adapter for loading pharmacy data from JSON files.
    
    Supports two JSON structures:
    1. Direct array: [{"id": "P001", ...}, ...]
    2. Wrapped array: {"pharmacies": [{"id": "P001", ...}, ...]}
    
    Handles nested coordinates in two formats:
    - Nested: {"location": {"latitude": 19.0, "longitude": 72.8}}
    - Flat: {"lat": 19.0, "lon": 72.8}
    
    Output always uses flat lat/lon keys.
    """
    
    def __init__(self, json_path: str = "data/pharmacies.json"):
        """Initialize the adapter with a JSON file path.
        
        Args:
            json_path: Path to the pharmacies JSON file
        """
        self.json_path = json_path
    
    def facility_type(self) -> str:
        """Return the facility type handled by this adapter.
        
        Returns:
            "pharmacy"
        """
        return "pharmacy"
    
    def load(self) -> List[Dict[str, Any]]:
        """Load and parse pharmacy data from JSON.
        
        Returns:
            List of pharmacy dictionaries with standardized keys:
            - id (str): Pharmacy identifier
            - name (str): Pharmacy name
            - lat (float): Latitude coordinate
            - lon (float): Longitude coordinate
            - type (str): Always "pharmacy"
            - Plus any additional JSON keys (hours, services, etc.)
        
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON is invalid or required fields are missing
        """
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"Pharmacy JSON file not found: {self.json_path}")
        
        # Read and parse JSON file
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in pharmacy file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to read pharmacy JSON file: {e}")
        
        # Handle both direct array and wrapped object shapes
        if isinstance(data, list):
            pharmacies_data = data
        elif isinstance(data, dict) and 'pharmacies' in data:
            pharmacies_data = data['pharmacies']
            if not isinstance(pharmacies_data, list):
                raise ValueError("'pharmacies' key must contain a list")
        else:
            raise ValueError(
                "JSON must be either a list of pharmacies or an object with a 'pharmacies' key"
            )
        
        if not pharmacies_data:
            raise ValueError("Pharmacy JSON contains no data")
        
        # Process each pharmacy
        facilities = []
        for idx, pharmacy in enumerate(pharmacies_data):
            try:
                if not isinstance(pharmacy, dict):
                    raise ValueError(f"Pharmacy at index {idx} is not an object")
                
                # Extract coordinates - handle both nested and flat formats
                lat, lon = self._extract_coordinates(pharmacy)
                
                # Build facility dict with required fields
                facility = {
                    'id': str(pharmacy.get('id', f'P{idx+1:03d}')),
                    'name': str(pharmacy.get('name', 'Unknown Pharmacy')),
                    'lat': lat,
                    'lon': lon,
                    'type': self.facility_type()
                }
                
                # Add all other keys from JSON (except location if it was nested)
                for key, value in pharmacy.items():
                    if key not in ['id', 'name', 'lat', 'lon', 'type', 'location']:
                        facility[key] = value
                
                facilities.append(facility)
                
            except (KeyError, ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid pharmacy data at index {idx}: {e}"
                )
        
        return facilities
    
    def _extract_coordinates(self, pharmacy: Dict[str, Any]) -> tuple[float, float]:
        """Extract and normalize latitude/longitude from pharmacy data.
        
        Handles multiple coordinate formats:
        - Flat: {"lat": 19.0, "lon": 72.8}
        - Nested with lat/lon: {"location": {"lat": 19.0, "lon": 72.8}}
        - Nested with latitude/longitude: {"location": {"latitude": 19.0, "longitude": 72.8}}
        
        Args:
            pharmacy: Pharmacy data dictionary
        
        Returns:
            Tuple of (latitude, longitude) as floats
        
        Raises:
            ValueError: If coordinates are missing or invalid
        """
        lat = None
        lon = None
        
        # Check for nested location object
        if 'location' in pharmacy and isinstance(pharmacy['location'], dict):
            location = pharmacy['location']
            # Try latitude/longitude keys
            if 'latitude' in location and 'longitude' in location:
                lat = location['latitude']
                lon = location['longitude']
            # Try lat/lon keys
            elif 'lat' in location and 'lon' in location:
                lat = location['lat']
                lon = location['lon']
        
        # Check for flat lat/lon keys
        if lat is None and 'lat' in pharmacy:
            lat = pharmacy['lat']
        if lon is None and 'lon' in pharmacy:
            lon = pharmacy['lon']
        
        # Check for flat latitude/longitude keys
        if lat is None and 'latitude' in pharmacy:
            lat = pharmacy['latitude']
        if lon is None and 'longitude' in pharmacy:
            lon = pharmacy['longitude']
        
        # Validate we found both coordinates
        if lat is None or lon is None:
            raise ValueError(
                "Missing coordinates - pharmacy must have lat/lon or location.lat/lon"
            )
        
        # Convert to float
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate values: {e}")
        
        return lat, lon


# Made with Bob
