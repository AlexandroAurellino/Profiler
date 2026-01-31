# backend/app/models/schemas.py

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict

import math

# ==========================================
# 1. DOMAIN ENUMS (The Vocabulary)
# ==========================================

class ProfileType(str, Enum):
    """The 4 Professional Paths defined by the Campus."""
    AI = "AI"         # Artificial Intelligence
    DMS = "DMS"       # Database Management System
    PSD = "PSD"       # Programming & Software Development
    INFRA = "INFRA"   # Network & Infrastructure

class CriteriaType(str, Enum):
    """The AHP Hierarchy Level 1 Nodes."""
    FOUNDATION = "FOUNDATION"   # Semantic: Sem 1-4 Mandatory Classes
    COMPETENCY = "COMPETENCY"   # Semantic: Sem 5+ Elective Profile Classes
    DENSITY = "DENSITY"         # Semantic: Ratio of classes taken vs available

class GradeLetter(str, Enum):
    """Standardized Academic Grade Scale."""
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    D = "D"
    E = "E"

# ==========================================
# 2. INPUT MODELS (Data Ingestion)
# ==========================================

class ParsedCourse(BaseModel):
    """
    Represents a raw row extracted from the PDF Transcript.
    Acts as the 'Evidence' for the Inference Engine.
    """
    code: str = Field(..., description="The unique Course Code (e.g., TI6043). Primary Key for mapping.")
    name: str = Field(..., description="The human-readable name of the course.")
    sks: int = Field(..., ge=1, le=6, description="Credit Units (Weight of the course).")
    grade_letter: str = Field(..., description="Original grade from PDF.")
    grade_value: float = Field(..., ge=0.0, le=4.0, description="Converted numeric value (0.0 - 4.0).")

    # Strict config to forbid extra fields that might confuse the logic
    model_config = ConfigDict(extra='forbid')

class StudentTranscript(BaseModel):
    """
    The complete collection of a student's academic history.
    """
    student_id: Optional[str] = Field(None, description="NIM extracted from PDF if available.")
    student_name: Optional[str] = Field(None, description="Name extracted from PDF.")
    courses: List[ParsedCourse]
    gpa_raw: Optional[float] = None

# ==========================================
# 3. KNOWLEDGE BASE MODELS (The Expert Rules)
# ==========================================

class CourseRelevance(BaseModel):
    """
    Defines the relationship between a Course and a Profile.
    Example: TI6043 (Machine Learning) -> AI Profile (High Relevance).
    """
    profile: ProfileType
    relevance_weight: float = Field(..., ge=0.0, le=1.0, description="How strong is the link? 1.0 = Critical, 0.1 = Weak.")
    type: CriteriaType = Field(..., description="Is this a Foundation builder or a Competency builder?")

class AHPConfig(BaseModel):
    """
    The 'Hyperparameters' of the AHP Engine.
    These are the Eigenvector weights derived from the Pairwise Comparison Matrix.
    """
    w_foundation: float = Field(0.3, description="Weight for Foundation Criteria")
    w_competency: float = Field(0.5, description="Weight for Competency Criteria")
    w_density: float = Field(0.2, description="Weight for Density Criteria")

    @model_validator(mode='after')
    def check_weights_sum_to_one(self) -> 'AHPConfig':
        # 1. Sum the weights
        total = self.w_foundation + self.w_competency + self.w_density
        
        # 2. Robust Floating Point Comparison
        # We never use '==' with floats because 0.1 + 0.2 != 0.3 in computers (it's 0.30000000004)
        # We check if the difference is negligible (e.g., smaller than 0.001)
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ValueError(
                f"AHP Weights must sum to 1.0. Current sum: {total:.4f} "
                f"(F={self.w_foundation}, C={self.w_competency}, D={self.w_density})"
            )
        
        return self
    
class PrerequisiteType(str, Enum):
    COURSE_GRADE = "COURSE_GRADE" # Requires a specific grade in another course
    SKS_COUNT = "SKS_COUNT"       # Requires total SKS passed

class PrerequisiteRule(BaseModel):
    """
    Defines a constraint to take a course.
    Example: To take 'Deep Learning', you need 'AI' > C.
    """
    target_course_code: str
    req_type: PrerequisiteType
    
    # Optional fields based on type
    required_course_code: Optional[str] = None
    min_grade_value: Optional[float] = None # 2.0 for C, 3.0 for B
    min_sks: Optional[int] = None

    model_config = ConfigDict(extra='ignore')

# ==========================================
# 4. OUTPUT MODELS (The Explainable Result)
# ==========================================

class AHPScoreset(BaseModel):
    """
    The mathematical breakdown of a specific profile's score.
    Crucial for XAI (Explainable AI).
    """
    foundation_score: float = Field(..., description="Normalized weighted average of Foundation classes.")
    competency_score: float = Field(..., description="Normalized weighted average of Profile classes.")
    density_score: float = Field(..., description="Ratio of classes taken.")
    
    # The final calculation: (F * Wf) + (C * Wc) + (D * Wd)
    final_ahp_score: float 

class ProfileRecommendation(BaseModel):
    """
    The final recommendation for a specific path.
    """
    profile: ProfileType
    rank: int = Field(..., description="1 = Best Match, 4 = Worst Match.")
    score: float = Field(..., description="The Final AHP Score (0.0 to 1.0).")
    details: AHPScoreset
    explanation: str = Field(..., description="Generated text explaining WHY this profile was chosen.")

class AnalysisResponse(BaseModel):
    """
    The JSON payload returned to the Laravel Backend.
    """
    status: str = "success"
    student_metadata: dict
    total_credits: int
    recommendations: List[ProfileRecommendation]