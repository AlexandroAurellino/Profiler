import logging
from typing import List, Dict, Set
from app.models.schemas import (
    StudentTranscript, 
    AHPConfig, 
    ProfileRecommendation, 
    AHPScoreset, 
    AnalysisResponse,
    ProfileType,
    CriteriaType,
    GradeLetter
)
from app.services.knowledge_base import knowledge_base

logger = logging.getLogger("ahp_profiler")

class AHPService:
    """
    The Core Inference Engine.
    Performs Absolute AHP (Ratings Mode) calculation.
    """

    def analyze_transcript(self, transcript: StudentTranscript, config: AHPConfig) -> AnalysisResponse:
        logger.info(f"Starting AHP Analysis for: {transcript.student_name} ({transcript.student_id})")
        
        # 1. Index student grades for O(1) lookup
        # Map: "TI6043" -> {value: 4.0, sks: 3}
        student_history = {
            c.code.upper(): {"val": c.grade_value, "sks": c.sks} 
            for c in transcript.courses
        }
        
        recommendations = []
        
        # 2. Iterate Profiles
        for profile in ProfileType:
            # A. Calculate Sub-Scores
            f_score = self._calculate_quality_score(profile, CriteriaType.FOUNDATION, student_history)
            c_score = self._calculate_quality_score(profile, CriteriaType.COMPETENCY, student_history)
            d_score = self._calculate_density_score(profile, CriteriaType.COMPETENCY, student_history)
            
            # B. Synthesis
            final_score = (
                (f_score * config.w_foundation) +
                (c_score * config.w_competency) +
                (d_score * config.w_density)
            )
            
            # C. Explain
            explanation = self._generate_explanation(profile, f_score, c_score, d_score)
            
            recommendations.append(ProfileRecommendation(
                profile=profile,
                rank=0, 
                score=round(final_score, 4),
                details=AHPScoreset(
                    foundation_score=round(f_score, 4),
                    competency_score=round(c_score, 4),
                    density_score=round(d_score, 4),
                    final_ahp_score=round(final_score, 4)
                ),
                explanation=explanation
            ))

        # 3. Sort & Rank
        recommendations.sort(key=lambda x: x.score, reverse=True)
        for i, rec in enumerate(recommendations):
            rec.rank = i + 1

        return AnalysisResponse(
            student_metadata={
                "name": transcript.student_name,
                "id": transcript.student_id,
                "gpa": transcript.gpa_raw
            },
            total_credits=sum(c.sks for c in transcript.courses),
            recommendations=recommendations
        )

    def _calculate_quality_score(self, profile: ProfileType, c_type: CriteriaType, student_history: Dict) -> float:
        """
        Calculates the weighted average grade of RELEVANT courses taken.
        Returns: 0.0 to 1.0
        """
        total_weighted_points = 0.0
        total_max_points = 0.0

        # Iterate through the Knowledge Base to find relevant courses
        # We assume knowledge_base._mapping is accessible. 
        # Ideally we'd use a getter, but direct access is faster for this loop.
        
        for code, rules in knowledge_base._mapping.items():
            # Check if this course is relevant to the Profile & Criteria
            # Each course has a list of rules (e.g. TI6113 -> AI, PSD, DMS)
            relevant_rule = next((r for r in rules if r.profile == profile and r.type == c_type), None)
            
            if relevant_rule:
                # The student MUST have taken this course to contribute to Quality Score
                if code in student_history:
                    grade_val = student_history[code]["val"]
                    norm_grade = grade_val / 4.0 # Normalize 4.0 -> 1.0
                    
                    weight = relevant_rule.relevance_weight
                    
                    total_weighted_points += (norm_grade * weight)
                    total_max_points += weight
        
        # Avoid division by zero
        if total_max_points == 0:
            return 0.0
            
        return total_weighted_points / total_max_points

    def _calculate_density_score(self, profile: ProfileType, c_type: CriteriaType, student_history: Dict) -> float:
        """
        Calculates saturation: Count(Taken Relevant) / Count(Total Available Relevant)
        """
        available_courses = set()
        taken_matches = set()

        for code, rules in knowledge_base._mapping.items():
            relevant_rule = next((r for r in rules if r.profile == profile and r.type == c_type), None)
            
            if relevant_rule:
                available_courses.add(code)
                if code in student_history:
                    taken_matches.add(code)
        
        if not available_courses:
            return 0.0
            
        return len(taken_matches) / len(available_courses)

    def _generate_explanation(self, profile: ProfileType, f: float, c: float, d: float) -> str:
        # Simplified logic for brevity
        if c > 0.7:
            return f"Highly recommended due to strong grades in {profile.value} electives."
        if f > 0.7 and d < 0.2:
            return f"High Potential based on Foundation, but lacks specialized {profile.value} classes."
        if d > 0.3:
            return f"Good match due to high interest (number of classes taken) in {profile.value}."
        return f"Moderate match based on current academic history."

ahp_service = AHPService()