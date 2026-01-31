import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import ValidationError

# Import the singleton instances of our services
from app.services.parser_service import parser_service
from app.services.ahp_service import ahp_service
from app.services.knowledge_base import knowledge_base # <--- NEW IMPORT

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
    **Development Tool:** Returns the entire course-to-profile mapping dictionary
    that is currently loaded in the server's memory.
    
    This is the "ground truth" that the AHP service uses for its calculations.
    Use this to verify that your YAML changes have been loaded correctly after a server restart.
    """
    logger.info("Debug request received for Knowledge Base state.")
    # FastAPI will automatically serialize the Pydantic models within the dictionary
    return knowledge_base._mapping

@router.post(
    "/debug/parse-pdf", 
    response_model=StudentTranscript,
    tags=["Debugging"],
    summary="Parse a PDF and return the raw extracted data"
)
async def debug_parse_transcript(file: UploadFile = File(...)):
    """
    **Development Tool:** Upload a PDF transcript to see exactly what the parser service extracts.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    logger.info(f"Debug parser endpoint hit. File: {file.filename}")
    
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="File is empty.")
        transcript = parser_service.parse_pdf(contents)
        logger.info(f"Parser found {len(transcript.courses)} courses.")
        return transcript
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
    w_foundation: float = 0.2,
    w_competency: float = 0.5,
    w_density: float = 0.3
):
    """
    **Student Profiling Endpoint**
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    logger.info(f"Receiving analysis request. File: {file.filename}")

    try:
        config = AHPConfig(
            w_foundation=w_foundation,
            w_competency=w_competency,
            w_density=w_density
        )
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File is empty.")
        transcript = parser_service.parse_pdf(contents)
        if not transcript.courses:
            raise HTTPException(status_code=422, detail="Could not extract any courses.")
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