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
    CourseRelevance
)
from app.services.knowledge_base import knowledge_base

logger = logging.getLogger("ahp_profiler")

class AHPService:
    """
    The Core Inference Engine.
    Performs Absolute AHP (Ratings Mode) calculation.
    
    Methodology:
    1. Score Quality (Foundation & Competency): Weighted Average of Grades.
    2. Score Density (Foundation): Linear Percentage (Must take all).
    3. Score Density (Competency): Saturation/Capped Logic (Taking 4 electives = 100%).
    4. Synthesis: Weighted Sum of components.
    """

    def analyze_transcript(self, transcript: StudentTranscript, config: AHPConfig) -> AnalysisResponse:
        logger.info(f"Starting AHP Analysis for: {transcript.student_name} ({transcript.student_id})")
        
        # 1. Index student grades for O(1) lookup
        # Map: "TI6043" -> 4.0 (Float Value)
        student_grades: Dict[str, float] = {
            c.code.upper(): c.grade_value
            for c in transcript.courses
        }
        
        recommendations = []
        
        # 2. Iterate through all 4 Profiles (AI, DMS, PSD, INFRA)
        for profile in ProfileType:
            
            # --- A. FOUNDATION ANALYSIS ---
            # Retrieve all rules for this Profile + Foundation
            # (Note: This involves iterating the KB; for 100 courses it's negligible)
            foundation_score = self._calculate_weighted_quality(
                profile, CriteriaType.FOUNDATION, student_grades
            )
            foundation_density = self._calculate_density(
                profile, CriteriaType.FOUNDATION, student_grades
            )

            # --- B. COMPETENCY ANALYSIS (ELECTIVES) ---
            competency_score = self._calculate_weighted_quality(
                profile, CriteriaType.COMPETENCY, student_grades
            )
            competency_density = self._calculate_density(
                profile, CriteriaType.COMPETENCY, student_grades
            )
            
            # --- C. SYNTHESIS (AHP FORMULA) ---
            # We average the density scores into a single component or keep separate?
            # Based on Schema: w_density applies to the "Concept of Density".
            # We will average the F-Density and C-Density into one D-Score for the final formula.
            # OR: Usually Density is heavily weighted on Electives (Interest). 
            # Let's average them: (Found_Dens + Comp_Dens) / 2
            
            # Refined Approach: 
            # Foundation Density is usually 1.0 if they are a senior student. 
            # Competency Density varies.
            # Let's treat 'Density' in the Config as the Competency Density (Interest Saturation).
            # Foundation completion is technically a prerequisite, but we'll include it in the Quality check implicitly.
            
            # Final Decision for this iteration:
            # Foundation Score = Quality of Foundation
            # Competency Score = Quality of Competency
            # Density Score    = Saturation of Competency (How "deep" they went into electives)
            
            final_score = (
                (foundation_score * config.w_foundation) +
                (competency_score * config.w_competency) +
                (competency_density * config.w_density)
            )
            
            # --- D. EXPLANATION GENERATION ---
            explanation = self._generate_explanation(
                profile, foundation_score, competency_score, competency_density
            )
            
            recommendations.append(ProfileRecommendation(
                profile=profile,
                rank=0, # Will sort later
                score=round(final_score, 4),
                details=AHPScoreset(
                    foundation_score=round(foundation_score, 4),
                    competency_score=round(competency_score, 4),
                    density_score=round(competency_density, 4),
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

    def _calculate_weighted_quality(
        self, 
        profile: ProfileType, 
        c_type: CriteriaType, 
        student_grades: Dict[str, float]
    ) -> float:
        """
        Calculates the Weighted Average Grade for Relevant courses.
        Formula: Sum(Grade * RelevanceWeight) / Sum(RelevanceWeights)
        Range: 0.0 to 1.0 (Normalized from 4.0)
        """
        total_weighted_points = 0.0
        total_max_weight = 0.0

        # Scan KB for relevant courses
        # Optimization: KB could have a pre-index by Profile, but linear scan is fine for <500 items.
        for code in knowledge_base.get_all_mapping_keys():
            rules = knowledge_base.get_relevance_rules(code)
            
            # Find rule matching current Profile & Criteria Type
            rule = next((r for r in rules if r.profile == profile and r.type == c_type), None)
            
            if rule:
                # We found a relevant course (e.g., TI6043 for AI)
                weight = rule.relevance_weight
                
                # Did the student take it?
                if code in student_grades:
                    grade_val = student_grades[code]
                    
                    # Normalize Grade: 4.0 -> 1.0, 2.0 -> 0.5
                    normalized_grade = grade_val / 4.0
                    
                    total_weighted_points += (normalized_grade * weight)
                    total_max_weight += weight
                else:
                    # If not taken, it doesn't contribute to Quality Score (Average of TAKEN courses).
                    # Alternatively, if you want to penalize not taking it, add 0 to numerator but weight to denominator.
                    # Standard AHP usually rates "Alternatives" based on attributes present.
                    # We will NOT penalize Quality for missing courses; that is what DENSITY is for.
                    pass
        
        if total_max_weight == 0:
            return 0.0
            
        return total_weighted_points / total_max_weight

    def _calculate_density(
        self, 
        profile: ProfileType, 
        c_type: CriteriaType, 
        student_grades: Dict[str, float]
    ) -> float:
        """
        Calculates Saturation/Exposure.
        
        Logic:
        - Foundation: Simple Percentage (Taken / Total Available).
        - Competency: Saturation Threshold. If student takes >= 4 electives, Score = 1.0.
        """
        available_count = 0
        taken_count = 0

        for code in knowledge_base.get_all_mapping_keys():
            rules = knowledge_base.get_relevance_rules(code)
            rule = next((r for r in rules if r.profile == profile and r.type == c_type), None)
            
            if rule:
                available_count += 1
                if code in student_grades:
                    taken_count += 1
        
        if available_count == 0:
            return 0.0
            
        # --- SATURATION LOGIC ---
        if c_type == CriteriaType.FOUNDATION:
            # Linear calculation for Foundation
            return taken_count / available_count
        else:
            # Capped calculation for Competency (Electives)
            # Threshold: 4 Electives = "Full Interest"
            SATURATION_THRESHOLD = 4.0
            score = taken_count / SATURATION_THRESHOLD
            return min(score, 1.0)

    def _generate_explanation(self, profile: ProfileType, f_score: float, c_score: float, d_score: float) -> str:
        """
        Generates a human-readable string explaining the mathematical result.
        """
        # Interpretation thresholds
        HIGH = 0.75
        MID = 0.5
        
        p_name = profile.value

        if c_score > HIGH and d_score == 1.0:
            return f"Excellent Candidate. High grades in {p_name} electives and strong interest shown."
        
        if c_score > HIGH and d_score < MID:
            return f"Strong Potential. Good grades in the few {p_name} courses taken, but low exposure."
        
        if f_score > HIGH and c_score < MID:
            return f"Solid Foundation. Good performance in basic courses, but struggling with advanced {p_name} topics."
        
        if d_score > 0.8 and c_score < MID:
            return f"High Interest, Low Performance. Has taken many {p_name} courses but grades are below average."
        
        if f_score < MID and c_score < MID:
            return f"Weak Match. Current academic history suggests difficulties with {p_name} concepts."

        return f"Moderate Match. Steady performance in {p_name} related subjects."

# Singleton Instance
ahp_service = AHPService()