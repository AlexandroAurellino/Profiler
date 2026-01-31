# backend/app/api/v1/endpoints/profile.py

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from pydantic import ValidationError

# Import Services
from app.services.parser_service import parser_service
from app.services.ahp_service import ahp_service
from app.services.knowledge_base import knowledge_base

# Import Schemas
from app.models.schemas import AnalysisResponse, AHPConfig, StudentTranscript

logger = logging.getLogger("ahp_profiler")
router = APIRouter()

# ==========================================
# DEBUGGING ENDPOINTS
# ==========================================
@router.get(
    "/debug/knowledge-base",
    tags=["Debugging"],
    summary="Inspect the live, in-memory Knowledge Base"
)
async def debug_get_knowledge_base():
    """
    **Development Tool:** 
    Returns a summary of the loaded data to verify 'courses.yaml' and rules are active.
    """
    logger.info("Debug request received for Knowledge Base state.")
    
    return {
        "status": "active",
        "counts": {
            "courses_with_metadata": len(knowledge_base._metadata_map),
            "courses_with_scoring_rules": len(knowledge_base._relevance_map),
            "courses_with_prerequisites": len(knowledge_base._prereq_map)
        },
        "sample_scoring_rules": list(knowledge_base._relevance_map.items())[:5], # Show first 5
        "sample_metadata": list(knowledge_base._metadata_map.items())[:5]        # Show first 5
    }

@router.post(
    "/debug/parse-pdf", 
    response_model=StudentTranscript,
    tags=["Debugging"],
    summary="Parse a PDF and return the raw extracted data"
)
async def debug_parse_transcript(file: UploadFile = File(...)):
    """
    **Development Tool:** 
    Upload a PDF transcript to see exactly what the parser service extracts.
    Useful to check if the Parser is correctly matching Codes from PDF to Names in YAML.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")
    
    logger.info(f"Debug parser endpoint hit. File: {file.filename}")
    
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="File is empty.")
            
        # Call the parser service
        transcript = parser_service.parse_pdf(contents)
        
        logger.info(f"Parser found {len(transcript.courses)} courses.")
        return transcript
        
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.critical(f"Unexpected Debug Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error during parsing.")


# ==========================================
# MAIN ANALYSIS ENDPOINT
# ==========================================
@router.post(
    "/analyze", 
    response_model=AnalysisResponse, 
    tags=["Profiling"],
    summary="Analyze a student transcript and return AHP-based profile recommendations"
)
async def analyze_student_transcript(
    file: UploadFile = File(...),
    w_foundation: float = Query(0.3, description="Weight for Foundation Score"),
    w_competency: float = Query(0.5, description="Weight for Competency Score"),
    w_density: float = Query(0.2, description="Weight for Interest/Density Score")
):
    """
    **Student Profiling Endpoint**
    
    1. Uploads a PDF Transcript.
    2. Extracts Course Codes and Grades.
    3. Enriches data using the Server's Knowledge Base (YAML).
    4. Calculates Profile Matches using AHP (Quality + Density).
    5. Returns ranked recommendations with explanations.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")
    
    logger.info(f"Receiving analysis request. File: {file.filename}")

    try:
        # 1. Configure AHP
        config = AHPConfig(
            w_foundation=w_foundation,
            w_competency=w_competency,
            w_density=w_density
        )
        
        # 2. Read File
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File is empty.")
            
        # 3. Parse PDF
        transcript = parser_service.parse_pdf(contents)
        
        # 4. Validate Extraction
        if not transcript.courses:
            logger.warning("PDF parsed successfully but 0 courses were found.")
            raise HTTPException(
                status_code=422, 
                detail="Could not extract any courses. Please check if the PDF format matches the Campus standard."
            )
            
        # 5. Run Inference
        result = ahp_service.analyze_transcript(transcript, config)
        
        return result

    except ValidationError as ve:
        logger.error(f"AHP Configuration Validation Error: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid AHP Configuration: {ve}")
        
    except ValueError as ve:
        logger.error(f"Data Processing Error: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
        
    except Exception as e:
        logger.critical(f"Unexpected System Error during analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error during profiling.")