import sys
import os
import yaml
from pprint import pprint

# Setup path
sys.path.append(os.getcwd())

# Import your Schema
from app.models.schemas import ProfileType

def test_enum_conversion():
    print("\n=== DEBUGGING ENUM CONVERSION ===")
    
    # 1. Simulate reading from YAML
    yaml_data = {'PSD': 1.0}
    print(f"Data from YAML: {yaml_data}")
    
    # 2. Iterate like the code does
    for profile_str, weight in yaml_data.items():
        print(f"Testing Profile String: '{profile_str}'")
        
        try:
            # 3. Try to convert to Enum (This is where it likely fails)
            enum_val = ProfileType(profile_str)
            print(f"✅ Conversion Success: {enum_val}")
        except ValueError as e:
            print(f"❌ Conversion FAILED!")
            print(f"   Input: '{profile_str}'")
            print(f"   Error: {e}")
            print(f"   Allowed Enum Values: {[e.value for e in ProfileType]}")

if __name__ == "__main__":
    test_enum_conversion()