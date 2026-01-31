import sys
import os
import yaml
from pprint import pprint

# Setup path
sys.path.append(os.getcwd())

from app.services.knowledge_base import knowledge_base

def check_raw_yaml():
    print("\n=== 1. RAW YAML INSPECTION ===")
    file_path = os.path.join("app", "data", "relevance_rules.yaml")
    
    try:
        with open(file_path, 'r') as f:
            raw_data = yaml.safe_load(f)
            
        if not raw_data:
            print("❌ YAML file appears empty or invalid.")
            return

        # Check COMPETENCY Section
        if "COMPETENCY" not in raw_data:
            print("❌ 'COMPETENCY' key is missing in YAML.")
            print("Found keys:", list(raw_data.keys()))
            return
        
        comp_data = raw_data["COMPETENCY"]
        print(f"✅ Found 'COMPETENCY' section with {len(comp_data)} items.")
        
        # Check specific key
        target = "TI5013"
        if target in comp_data:
            print(f"✅ FOUND '{target}' in raw YAML: {comp_data[target]}")
        else:
            print(f"❌ '{target}' is NOT in 'COMPETENCY' section.")
            print("First 10 keys found in COMPETENCY:")
            print(list(comp_data.keys())[:10])
            
            # Check if it exists elsewhere
            print(f"\nSearching for {target} in other sections...")
            found_anywhere = False
            for section, items in raw_data.items():
                if items and target in items:
                    print(f"   -> FOUND in section: '{section}'")
                    found_anywhere = True
            if not found_anywhere:
                print("   -> Strictly missing from the file structure.")

    except Exception as e:
        print(f"❌ Error reading file: {e}")

def check_loaded_kb():
    print("\n=== 2. KNOWLEDGE BASE CLASS INSPECTION ===")
    target = "TI5013"
    rules = knowledge_base.get_relevance(target)
    
    if rules:
        print(f"✅ KnowledgeBase has rules for {target}:")
        for r in rules:
            print(f"   - {r}")
    else:
        print(f"❌ KnowledgeBase returned [] for {target}")
        
        # Print nearby keys to check for typos
        print("Dumping all keys starting with 'TI5' to check for typos:")
        keys = [k for k in knowledge_base._mapping.keys() if k.startswith("TI5")]
        print(keys)

if __name__ == "__main__":
    check_raw_yaml()
    check_loaded_kb()