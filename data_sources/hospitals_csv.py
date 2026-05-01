"""CSV adapter for hospital facility data.

This adapter reads hospital data from CSV files and converts it into the
standardized facility format. It handles data validation, type conversion,
and special processing for fields like specialties.
"""

import os
import pandas as pd
from typing import List, Dict, Any
from .adapter_base import FacilityAdapter


class HospitalsCsvAdapter(FacilityAdapter):
    """Adapter for loading hospital data from CSV files.
    
    Expects a CSV file with at minimum: id, name, lat, lon columns.
    Additional columns like specialties, beds, emergency_available are
    preserved in the output.
    
    Special handling:
    - Converts lat/lon to floats
    - Converts numeric fields to numbers
    - Strips whitespace from strings
    - Splits comma-separated specialties into a list
    """
    
    def __init__(self, csv_path: str = "data/hospitals.csv"):
        """Initialize the adapter with a CSV file path.
        
        Args:
            csv_path: Path to the hospitals CSV file
        """
        self.csv_path = csv_path
    
    def facility_type(self) -> str:
        """Return the facility type handled by this adapter.
        
        Returns:
            "hospital"
        """
        return "hospital"
    
    def load(self) -> List[Dict[str, Any]]:
        """Load and parse hospital data from CSV.
        
        Returns:
            List of hospital dictionaries with standardized keys:
            - id (str): Hospital identifier
            - name (str): Hospital name
            - lat (float): Latitude coordinate
            - lon (float): Longitude coordinate
            - type (str): Always "hospital"
            - Plus any additional CSV columns (specialties, beds, etc.)
        
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If required columns are missing or data is invalid
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Hospital CSV file not found: {self.csv_path}")
        
        # Read CSV file
        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}")
        
        # Check if CSV is empty
        if df.empty:
            raise ValueError("Hospital CSV file is empty")
        
        # Validate required columns
        required_columns = ['id', 'name', 'lat', 'lon']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(
                f"Missing required columns in hospital CSV: {', '.join(missing_columns)}"
            )
        
        # Process each row
        facilities = []
        for idx, row in df.iterrows():
            try:
                # Build facility dict with required fields
                facility = {
                    'id': str(row['id']).strip(),
                    'name': str(row['name']).strip(),
                    'lat': float(row['lat']),
                    'lon': float(row['lon']),
                    'type': self.facility_type()
                }
                
                # Add all other columns from CSV
                for col in df.columns:
                    if col not in ['id', 'name', 'lat', 'lon', 'type']:
                        value = row[col]
                        
                        # Skip NaN values
                        if pd.isna(value):
                            continue
                        
                        # Handle specialties - split comma-separated string into list
                        if col == 'specialties' and isinstance(value, str):
                            facility[col] = [s.strip() for s in value.split(',')]
                        # Convert numeric strings to numbers
                        elif isinstance(value, str):
                            # Try to convert to number
                            try:
                                # Try int first
                                if '.' not in value:
                                    facility[col] = int(value)
                                else:
                                    facility[col] = float(value)
                            except ValueError:
                                # Keep as string, but strip whitespace
                                facility[col] = value.strip()
                        # Handle boolean strings
                        elif isinstance(value, str) and value.lower() in ['true', 'false']:
                            facility[col] = value.lower() == 'true'
                        else:
                            # Keep the value as-is (already a number or other type)
                            facility[col] = value
                
                facilities.append(facility)
                
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid data in hospital CSV at row {idx + 2}: {e}"
                )
        
        return facilities


# Made with Bob
