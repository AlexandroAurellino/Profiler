import yaml
import os
import logging
from typing import List, Dict, Any
from app.models.schemas import (
    CourseRelevance, 
    ProfileType, 
    CriteriaType, 
    PrerequisiteRule, 
    PrerequisiteType
)

# Initialize logger
logger = logging.getLogger("ahp_profiler")

class KnowledgeBase:
    """
    Acts as the In-Memory Database.
    Loads rules from YAML files in app/data/ instead of hardcoding them.
    """

    def __init__(self):
        # Determine path to app/data/
        self.base_path = os.path.join(os.path.dirname(__file__), "../data")
        
        # 1. Load the Raw YAML Data
        self._relevance_data = self._load_yaml("relevance_rules.yaml")
        self._prereq_data = self._load_yaml("prerequisites.yaml")

        # 2. Build the Logical Mappings
        self._mapping: Dict[str, List[CourseRelevance]] = self._build_knowledge_map()
        self._prereqs: Dict[str, List[PrerequisiteRule]] = self._build_prerequisites()
        
        logger.info(f"Knowledge Base Loaded. Mapped {len(self._mapping)} courses.")

    def _load_yaml(self, filename: str) -> Any:
        path = os.path.join(self.base_path, filename)
        try:
            if not os.path.exists(path):
                logger.error(f"YAML file not found: {path}")
                return {}
                
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {str(e)}")
            return {}

    def get_relevance(self, course_code: str) -> List[CourseRelevance]:
        return self._mapping.get(course_code.upper(), [])

    def get_prereqs(self, course_code: str) -> List[PrerequisiteRule]:
        return self._prereqs.get(course_code.upper(), [])

    def _build_knowledge_map(self) -> Dict[str, List[CourseRelevance]]:
        mapping = {}

        # The YAML has sections like "FOUNDATION" and "COMPETENCY"
        # We need to map these string keys to our CriteriaType Enum
        section_map = {
            "FOUNDATION": CriteriaType.FOUNDATION,
            "COMPETENCY": CriteriaType.COMPETENCY
        }

        for section_name, c_type in section_map.items():
            if section_name not in self._relevance_data:
                continue
                
            # Iterate through courses in that section
            # Example: TI5013: { PSD: 1.0 }
            for code, rules in self._relevance_data[section_name].items():
                code = code.upper().strip()
                if code not in mapping:
                    mapping[code] = []
                
                for profile_str, weight in rules.items():
                    try:
                        # Convert String "PSD" to Enum ProfileType.PSD
                        profile_enum = ProfileType(profile_str)
                        
                        mapping[code].append(CourseRelevance(
                            profile=profile_enum,
                            relevance_weight=float(weight),
                            type=c_type
                        ))
                    except ValueError:
                        logger.warning(f"Invalid Profile '{profile_str}' in YAML for course {code}")

        return mapping

    def _build_prerequisites(self) -> Dict[str, List[PrerequisiteRule]]:
        rules = {}
        
        if not self._prereq_data:
            return rules

        for target, reqs in self._prereq_data.items():
            target = target.upper().strip()
            if target not in rules:
                rules[target] = []

            # Handle List format (multiple prereqs) or Dict format (single)
            req_list = reqs if isinstance(reqs, list) else [reqs]

            for req in req_list:
                # Check for SKS type
                if "SKS" in req:
                    rules[target].append(PrerequisiteRule(
                        target_course_code=target,
                        req_type=PrerequisiteType.SKS_COUNT,
                        min_sks=int(req["SKS"])
                    ))
                else:
                    # Check for Course Grade type
                    # Format: { TI0243: 2.0 }
                    for req_code, min_grade in req.items():
                        rules[target].append(PrerequisiteRule(
                            target_course_code=target,
                            req_type=PrerequisiteType.COURSE_GRADE,
                            required_course_code=req_code.upper(),
                            min_grade_value=float(min_grade)
                        ))
        return rules

# Singleton Instance
knowledge_base = KnowledgeBase()