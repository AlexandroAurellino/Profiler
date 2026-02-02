# backend/app/api/v1/endpoints/admin.py

import logging
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict

from app.services.knowledge_base import knowledge_base
from app.models.schemas import (
    CourseMetadata, 
    CourseUpdate, 
    RelevanceUpdate, 
    AdminActionResponse,
    ParsedCourse
)

logger = logging.getLogger("ahp_profiler")
router = APIRouter()

@router.get("/courses", response_model=List[CourseMetadata])
async def get_all_courses():
    """Get the full list of defined courses."""
    # Convert dict values to list
    return list(knowledge_base._metadata_map.values())

@router.post("/courses", response_model=AdminActionResponse)
async def upsert_course(payload: CourseUpdate):
    """Add or Update a Course (Name/SKS)."""
    try:
        new_meta = CourseMetadata(
            code=payload.code.upper(),
            name=payload.name,
            sks=payload.sks
        )
        knowledge_base.add_or_update_course(new_meta)
        return {"status": "success", "message": f"Course {new_meta.code} saved."}
    except Exception as e:
        logger.error(f"Error saving course: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/courses/{code}", response_model=AdminActionResponse)
async def delete_course(code: str):
    """Delete a course from the database."""
    success = knowledge_base.delete_course(code.upper())
    if not success:
        raise HTTPException(status_code=404, detail="Course not found.")
    return {"status": "success", "message": f"Course {code} deleted."}

@router.post("/rules", response_model=AdminActionResponse)
async def update_rule(payload: RelevanceUpdate):
    """
    Update AHP Weights for a course.
    Example payload:
    {
      "code": "TI6043",
      "type": "COMPETENCY",
      "weights": {"AI": 1.0, "DMS": 0.5}
    }
    """
    try:
        # Convert Enum keys to string for YAML storage
        clean_weights = {k.value: v for k, v in payload.weights.items()}
        
        knowledge_base.update_relevance_rules(
            payload.code.upper(),
            payload.type,
            clean_weights
        )
        return {"status": "success", "message": f"Rules updated for {payload.code}"}
    except Exception as e:
        logger.error(f"Error saving rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reload", response_model=AdminActionResponse)
async def reload_data():
    """Force the server to re-read all YAML files from disk."""
    try:
        knowledge_base.reload()
        return {"status": "success", "message": "Knowledge Base reloaded from disk."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))