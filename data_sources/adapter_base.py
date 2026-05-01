"""Abstract base class for facility data adapters.

This module defines the FacilityAdapter interface that all data source
adapters must implement. It ensures consistent data format across different
source types (CSV, JSON, unstructured text, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class FacilityAdapter(ABC):
    """Abstract base class for loading facility data from various sources.
    
    All adapters must return standardized facility records with the following
    required keys: id, name, lat, lon, type.
    
    Additional keys may be included based on facility type (e.g., specialties
    for hospitals, blood_types for blood banks).
    """
    
    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        """Load and parse facility data from the source.
        
        Returns:
            List of facility dictionaries, each containing at minimum:
                - id (str): Unique identifier
                - name (str): Facility name
                - lat (float): Latitude coordinate
                - lon (float): Longitude coordinate
                - type (str): Facility type (hospital, pharmacy, blood_bank)
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement load()")
    
    @abstractmethod
    def facility_type(self) -> str:
        """Return the type of facility this adapter handles.
        
        Returns:
            Facility type string (e.g., 'hospital', 'pharmacy', 'blood_bank')
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement facility_type()")

# Made with Bob
