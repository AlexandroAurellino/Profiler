# backend/app/services/knowledge_base.py

import yaml
import logging
from typing import List, Dict, Any, Optional

# Import settings for centralized path management
from app.core.config import settings
from app.models.schemas import (
    CourseRelevance, 
    ProfileType, 
    CriteriaType, 
    PrerequisiteRule, 
    PrerequisiteType,
    CourseMetadata
)

# Initialize logger
logger = logging.getLogger("ahp_profiler")

class KnowledgeBase:
    """
    The Central Knowledge Repository for the Expert System.
    
    Responsibilities:
    1. Load raw data from YAML files in the 'data' directory.
    2. Parse and validate the data against Pydantic schemas.
    3. Serve as the 'Source of Truth' for Course Names and SKS (preventing PDF parsing errors).
    4. Provide O(1) lookups for AHP scoring rules and Prerequisite constraints.
    """

    def __init__(self):
        logger.info("Initializing Knowledge Base...")
        
        # 1. Load the Raw YAML Data
        # We use the settings.DATA_DIR defined in core/config.py
        self._raw_courses = self._load_yaml("courses.yaml")
        self._raw_relevance = self._load_yaml("relevance_rules.yaml")
        self._raw_prereqs = self._load_yaml("prerequisites.yaml")

        # 2. Build the Logical Mappings (In-Memory Databases)
        # Map: CourseCode -> CourseMetadata (Name, SKS)
        self._metadata_map: Dict[str, CourseMetadata] = self._build_metadata_map()
        
        # Map: CourseCode -> List[CourseRelevance]
        self._relevance_map: Dict[str, List[CourseRelevance]] = self._build_relevance_map()
        
        # Map: CourseCode -> List[PrerequisiteRule]
        self._prereq_map: Dict[str, List[PrerequisiteRule]] = self._build_prerequisite_map()
        
        logger.info(f"Knowledge Base Ready. Loaded {len(self._metadata_map)} courses, "
                    f"{len(self._relevance_map)} scoring rules, "
                    f"and {len(self._prereq_map)} prerequisite chains.")

    # ==========================================
    # INTERNAL LOADING MECHANISMS
    # ==========================================

    def _load_yaml(self, filename: str) -> Any:
        """
        Safely loads a YAML file from the defined DATA_DIR.
        """
        file_path = settings.DATA_DIR / filename
        try:
            if not file_path.exists():
                logger.critical(f"CRITICAL: Required data file not found: {file_path}")
                return {}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {str(e)}")
            return {}

    def _build_metadata_map(self) -> Dict[str, CourseMetadata]:
        """
        Indexes courses.yaml for O(1) access by Course Code.
        This allows us to correct names/sks from the PDF parser.
        """
        mapping = {}
        if not self._raw_courses:
            logger.warning("courses.yaml is empty or failed to load!")
            return mapping

        # courses.yaml is a List of Dictionaries
        for entry in self._raw_courses:
            try:
                # Normalize code to Uppercase
                code = entry.get('code', '').strip().upper()
                name = entry.get('name', 'Unknown Course').strip()
                sks = entry.get('sks', 0)

                if code:
                    mapping[code] = CourseMetadata(
                        code=code,
                        name=name,
                        sks=sks
                    )
            except Exception as e:
                logger.warning(f"Skipping malformed course entry: {entry} - Error: {e}")

        return mapping

    def _build_relevance_map(self) -> Dict[str, List[CourseRelevance]]:
        """
        Parses relevance_rules.yaml to associate courses with Profiles (AI, PSD, etc.).
        Structure: SECTION -> COURSE_CODE -> PROFILE -> WEIGHT
        """
        mapping = {}
        
        # Map YAML keys to our Enum Logic
        section_map = {
            "FOUNDATION": CriteriaType.FOUNDATION,
            "COMPETENCY": CriteriaType.COMPETENCY
        }

        for section_name, criteria_type in section_map.items():
            # Ensure the section exists in YAML
            if section_name not in self._raw_relevance:
                continue
            
            section_data = self._raw_relevance[section_name]
            if not section_data:
                continue

            # Iterate through courses in this section
            for code_raw, profiles_dict in section_data.items():
                code = code_raw.upper().strip()
                
                # Initialize list if not exists
                if code not in mapping:
                    mapping[code] = []

                # Handle cases where a course might be listed but has no weights (None)
                if not profiles_dict:
                    continue

                # Iterate through { PROFILE: WEIGHT }
                for profile_str, weight in profiles_dict.items():
                    try:
                        # Validate Profile Enum (AI, DMS, etc.)
                        profile_enum = ProfileType(profile_str)
                        
                        rule = CourseRelevance(
                            profile=profile_enum,
                            relevance_weight=float(weight),
                            type=criteria_type
                        )
                        mapping[code].append(rule)
                    except ValueError:
                        logger.warning(f"Invalid Profile '{profile_str}' in YAML for course {code}")
                    except Exception as e:
                        logger.error(f"Error parsing rule for {code}: {e}")

        return mapping

    def _build_prerequisite_map(self) -> Dict[str, List[PrerequisiteRule]]:
        """
        Parses prerequisites.yaml.
        Handles the complex structure where requirements can be:
        1. A Dictionary (Single constraint)
        2. A List of Dictionaries (Multiple constraints)
        3. A mix of 'SKS' constraints and 'Course' constraints.
        """
        rules = {}
        
        if not self._raw_prereqs:
            return rules

        for target_raw, requirements in self._raw_prereqs.items():
            target_code = target_raw.upper().strip()
            
            if target_code not in rules:
                rules[target_code] = []

            # 1. Normalize input to always be a List of items
            # If it's a single dict {TI001: 2.0}, wrap it in a list -> [{TI001: 2.0}]
            req_list = requirements if isinstance(requirements, list) else [requirements]

            # 2. Iterate through each requirement item
            for req_item in req_list:
                try:
                    # Case A: SKS Prerequisite -> { "SKS": 100 }
                    if "SKS" in req_item:
                        rules[target_code].append(PrerequisiteRule(
                            target_course_code=target_code,
                            req_type=PrerequisiteType.SKS_COUNT,
                            min_sks=int(req_item["SKS"])
                        ))
                    
                    # Case B: Course Prerequisite -> { "TI0123": 2.0 }
                    else:
                        # Iterate keys in the dict (usually just one, e.g. TI0123)
                        for req_code_raw, min_grade in req_item.items():
                            req_code = req_code_raw.upper().strip()
                            rules[target_code].append(PrerequisiteRule(
                                target_course_code=target_code,
                                req_type=PrerequisiteType.COURSE_GRADE,
                                required_course_code=req_code,
                                min_grade_value=float(min_grade)
                            ))
                            
                except Exception as e:
                    logger.error(f"Failed to parse prerequisite for {target_code}: {req_item}. Error: {e}")

        return rules

    # ==========================================
    # PUBLIC ACCESSORS (The API)
    # ==========================================

    def get_course_metadata(self, code: str) -> Optional[CourseMetadata]:
        """
        Retrieves the official Name and SKS for a given course code.
        Returns None if the course is not in the database.
        """
        return self._metadata_map.get(code.upper().strip())

    def get_relevance_rules(self, code: str) -> List[CourseRelevance]:
        """
        Retrieves the AHP scoring weights for a course.
        Example: TI6043 -> [ {AI: 1.0, Type: COMPETENCY}, ... ]
        """
        return self._relevance_map.get(code.upper().strip(), [])

    def get_prerequisites(self, code: str) -> List[PrerequisiteRule]:
        """
        Retrieves the list of requirements to take a specific course.
        """
        return self._prereq_map.get(code.upper().strip(), [])
    
    def get_all_mapping_keys(self) -> List[str]:
        """
        Helper for iteration or debugging. Returns all course codes that have scoring rules.
        """
        return list(self._relevance_map.keys())

# ==========================================
# SINGLETON INSTANCE
# ==========================================
knowledge_base = KnowledgeBase()