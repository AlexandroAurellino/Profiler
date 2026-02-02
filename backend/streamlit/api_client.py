import streamlit as st
from typing import Dict, Any, List, Optional

# --- DIRECT IMPORTS (Bypassing HTTP/FastAPI) ---
# We import the services directly from the 'app' folder you copied
from app.services.parser_service import parser_service
from app.services.ahp_service import ahp_service
from app.services.knowledge_base import knowledge_base
from app.models.schemas import AHPConfig, CourseMetadata, CriteriaType, ProfileType

# ==========================================
# 1. ANALYSIS FUNCTION
# ==========================================
def analyze_transcript(file, weights: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Directly calls the Parser and AHP Service.
    """
    try:
        # 1. Read bytes from Streamlit UploadedFile
        # Streamlit files behave like open files, so we read the bytes.
        content = file.read()
        
        # 2. Parse (Direct Call to Service)
        transcript = parser_service.parse_pdf(content)
        
        if not transcript.courses:
            st.error("No courses found in PDF. Please check the file format.")
            return None

        # 3. Create Config Object
        config = AHPConfig(
            w_foundation=weights["w_foundation"],
            w_competency=weights["w_competency"],
            w_density=weights["w_density"]
        )

        # 4. Analyze (Direct Call to Service)
        result = ahp_service.analyze_transcript(transcript, config)
        
        # 5. Convert Pydantic Model to Dict for Streamlit to display easily
        return result.model_dump() 
        
    except Exception as e:
        st.error(f"Analysis Failed: {str(e)}")
        # Log error to console for debugging
        print(f"Error during analysis: {e}")
        return None

# ==========================================
# 2. COURSE MANAGEMENT (ADMIN)
# ==========================================
def get_courses() -> List[Dict[str, Any]]:
    """
    Directly gets all courses from the in-memory KnowledgeBase.
    """
    # access internal map -> convert values to list -> dump to dict
    return [c.model_dump() for c in knowledge_base._metadata_map.values()]

def upsert_course(course_data: Dict[str, Any]) -> bool:
    """
    Directly adds or updates a course in the KnowledgeBase and saves to YAML.
    """
    try:
        # Validate data using the Pydantic Schema
        meta = CourseMetadata(
            code=course_data['code'],
            name=course_data['name'],
            sks=course_data['sks']
        )
        
        # Call the service method we added earlier
        knowledge_base.add_or_update_course(meta)
        
        st.toast(f"Saved Course: {meta.code}")
        return True
    except Exception as e:
        st.error(f"Error saving course: {e}")
        return False

# ==========================================
# 3. RULE MANAGEMENT (ADMIN)
# ==========================================
def update_relevance_rules(rule_data: Dict[str, Any]) -> bool:
    """
    Directly updates the AHP weights in the KnowledgeBase and saves to YAML.
    """
    try:
        code = rule_data['code']
        # Convert string "FOUNDATION" to Enum
        c_type = CriteriaType(rule_data['type']) 
        
        # Ensure keys match ProfileType strings (AI, DMS, etc.)
        weights = rule_data['weights'] 
        
        # Call service method
        knowledge_base.update_relevance_rules(code, c_type, weights)
        
        st.toast(f"Updated rules for {code}")
        return True
    except Exception as e:
        st.error(f"Error updating rules: {e}")
        return False