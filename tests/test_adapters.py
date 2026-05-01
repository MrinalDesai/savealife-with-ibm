"""Simple test script for data source adapters.

This script tests the three facility data adapters:
- HospitalsCsvAdapter
- PharmaciesJsonAdapter
- BloodBanksTextAdapter (requires watsonx.ai credentials)

Run with: python tests/test_adapters.py
"""

import os
import sys

# Add parent directory to path so we can import from data_sources
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources.hospitals_csv import HospitalsCsvAdapter
from data_sources.pharmacies_json import PharmaciesJsonAdapter
from data_sources.bloodbanks_text import BloodBanksTextAdapter


def test_hospitals():
    """Test the HospitalsCsvAdapter."""
    print("=" * 60)
    print("Testing HospitalsCsvAdapter")
    print("=" * 60)
    
    try:
        adapter = HospitalsCsvAdapter()
        hospitals = adapter.load()
        
        print(f"✓ Successfully loaded {len(hospitals)} hospitals")
        print(f"✓ Facility type: {adapter.facility_type()}")
        
        if hospitals:
            print("\nFirst hospital:")
            first = hospitals[0]
            for key, value in first.items():
                print(f"  {key}: {value}")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Error loading hospitals: {e}")
        print()
        return False


def test_pharmacies():
    """Test the PharmaciesJsonAdapter."""
    print("=" * 60)
    print("Testing PharmaciesJsonAdapter")
    print("=" * 60)
    
    try:
        adapter = PharmaciesJsonAdapter()
        pharmacies = adapter.load()
        
        print(f"✓ Successfully loaded {len(pharmacies)} pharmacies")
        print(f"✓ Facility type: {adapter.facility_type()}")
        
        if pharmacies:
            print("\nFirst pharmacy:")
            first = pharmacies[0]
            for key, value in first.items():
                print(f"  {key}: {value}")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Error loading pharmacies: {e}")
        print()
        return False


def test_bloodbanks():
    """Test the BloodBanksTextAdapter (requires watsonx.ai credentials)."""
    print("=" * 60)
    print("Testing BloodBanksTextAdapter")
    print("=" * 60)
    
    # Check if watsonx.ai credentials are configured
    if not os.getenv("WATSONX_API_KEY"):
        print("⊘ Skipping blood banks test - WATSONX_API_KEY not set")
        print("  To test this adapter, configure watsonx.ai credentials in .env")
        print()
        return None
    
    try:
        adapter = BloodBanksTextAdapter()
        bloodbanks = adapter.load()
        
        print(f"✓ Successfully loaded {len(bloodbanks)} blood banks")
        print(f"✓ Facility type: {adapter.facility_type()}")
        
        if bloodbanks:
            print("\nFirst blood bank:")
            first = bloodbanks[0]
            for key, value in first.items():
                print(f"  {key}: {value}")
        
        print()
        return True
        
    except RuntimeError as e:
        if "credentials not configured" in str(e):
            print(f"⊘ Skipping blood banks test - {e}")
            print()
            return None
        else:
            print(f"✗ Runtime error: {e}")
            print()
            return False
    except Exception as e:
        print(f"✗ Error loading blood banks: {e}")
        print()
        return False


def main():
    """Run all adapter tests."""
    print("\n" + "=" * 60)
    print("ADAPTER TESTS")
    print("=" * 60)
    print()
    
    results = {
        'hospitals': test_hospitals(),
        'pharmacies': test_pharmacies(),
        'bloodbanks': test_bloodbanks()
    }
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}")
    print()
    
    if failed > 0:
        print("Some tests failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("All tests passed or skipped!")
        sys.exit(0)


if __name__ == "__main__":
    main()


# Made with Bob