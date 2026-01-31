import sys
import os
import yaml
from pprint import pprint

# Setup path
sys.path.append(os.getcwd())

from app.services.knowledge_base import knowledge_base

def check_ground_truth():
    print("--- GROUND TRUTH INSPECTION ---")
    print("This is what the AHP Service actually sees.")
    
    # 1. We will check for the two PSD courses Alexandro took
    psd_courses_to_check = ["TI5013", "TI5033"]
    found_count = 0
    
    for code in psd_courses_to_check:
        if code in knowledge_base._mapping:
            print(f"\n✅ FOUND '{code}' in the final mapping:")
            pprint(knowledge_base._mapping[code])
            found_count += 1
        else:
            print(f"\n❌ CRITICAL ERROR: '{code}' is MISSING from the final mapping.")

    if found_count == len(psd_courses_to_check):
        print("\nCONCLUSION: The Knowledge Base is loading correctly.")
        print("The error is likely in the AHP calculation logic or the parsed course codes.")
    else:
        print("\nCONCLUSION: The Knowledge Base is NOT loading these keys.")
        print("This points to a subtle syntax error (like a Tab char) in 'relevance_rules.yaml'.")
        print("Please delete the TI5013 and TI5033 lines and re-type them manually.")

    print("\n--- DUMP OF ALL COMPETENCY KEYS LOADED ---")
    competency_keys = []
    for code, rules in knowledge_base._mapping.items():
        for rule in rules:
            if rule.type.value == "COMPETENCY":
                competency_keys.append(code)
                break # Avoid adding the same code multiple times
    
    print(f"Total Competency keys loaded: {len(competency_keys)}")
    pprint(sorted(competency_keys))


if __name__ == "__main__":
    check_ground_truth()