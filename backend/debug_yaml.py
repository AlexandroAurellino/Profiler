import sys
import os

# Setup path to import app modules
sys.path.append(os.getcwd())

from app.services.knowledge_base import knowledge_base
from app.models.schemas import CriteriaType, ProfileType

print("--- DEBUGGING KNOWLEDGE BASE ---")

# 1. Check if TI5013 is in the mapping
code = "TI5013"
rules = knowledge_base.get_relevance(code)

if not rules:
    print(f"❌ ERROR: {code} is NOT found in the Knowledge Base.")
    print("   Fix: Check indentation in 'relevance_rules.yaml'.")
    print("   Make sure TI5013 is indented under 'COMPETENCY:'.")
else:
    print(f"✅ SUCCESS: {code} found with {len(rules)} rules.")
    for r in rules:
        print(f"   - Profile: {r.profile}, Type: {r.type}, Weight: {r.relevance_weight}")
        if r.profile == ProfileType.PSD and r.type == CriteriaType.COMPETENCY:
            print("     -> This is the rule we need!")

print("\n--- DEBUGGING PARSER (Simulated) ---")
# 2. Check if Regex catches the line
import re
line_from_pdf = "11 TI5013 POLA DESAIN ANTARMUKA PENGGUNA 3 A"
pattern = re.compile(r"([A-Z]{2}\d{4})\s+(.*?)\s+(\d{1,2})\s+([A-E][+-]?)")
match = pattern.findall(line_from_pdf)

if match:
    print(f"✅ REGEX MATCHED: {match}")
else:
    print(f"❌ REGEX FAILED on line: {line_from_pdf}")