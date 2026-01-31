import re
import pdfplumber
import logging
from io import BytesIO
from typing import List, Optional, Set, Tuple

# Import the Knowledge Base to act as Source of Truth
from app.services.knowledge_base import knowledge_base
from app.models.schemas import (
    StudentTranscript,
    ParsedCourse,
    GradeLetter
)

logger = logging.getLogger("ahp_profiler")

class TranscriptParser:
    """
    Service responsible for extracting structured data from raw PDF bytes.
    
    Philosophy:
    - Trust the PDF for EVIDENCE (Did the student take course X? What grade did they get?).
    - Trust the KnowledgeBase for METADATA (What is the name of course X? How many SKS?).
    """

    # ==========================================
    # REGEX PATTERNS
    # ==========================================
    
    # Matches: Course Code (TI or MH followed by 4 digits)
    # This is the anchor we use to identify a valid row.
    CODE_PATTERN = re.compile(r"(TI\d{4}|MH\d{4})", re.IGNORECASE)

    # Matches: Grades (A, A-, B+, B, B-, C+, C, D, E)
    # We look for this at the end of the line or column.
    GRADE_PATTERN = re.compile(r"\b([A-E][+-]?)\b")

    # Metadata Patterns (Header info)
    NIM_PATTERN = re.compile(r"No\.?\s*Mahasiswa\s*[:]\s*(\d+)", re.IGNORECASE)
    NAME_PATTERN = re.compile(r"Nama\s*[:]\s*([^\n\r]+?)(?=\s+(?:Fakultas|Program|$))", re.IGNORECASE)
    GPA_PATTERN = re.compile(r"IP\s*Kumulatif\s*[:]\s*([\d\.]+)", re.IGNORECASE)

    # Grade Value Mapping
    GRADE_MAP = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0,
        'D': 1.0, 'E': 0.0
    }

    def parse_pdf(self, file_bytes: bytes) -> StudentTranscript:
        """
        Main entry point. Converts PDF bytes to StudentTranscript object.
        """
        logger.info("Starting PDF Parsing process...")
        
        full_text_lines = []
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    # extract_text() usually preserves visual layout with newlines
                    text = page.extract_text()
                    if text:
                        full_text_lines.extend(text.split('\n'))
            
            full_text_blob = "\n".join(full_text_lines)
            
        except Exception as e:
            logger.error(f"PDFPlumber extraction failed: {str(e)}")
            raise ValueError("Invalid PDF file or corrupted format.")

        # 1. Extract Metadata (Header Info)
        student_id = self._extract_metadata(full_text_blob, self.NIM_PATTERN)
        student_name = self._extract_metadata(full_text_blob, self.NAME_PATTERN)
        gpa_str = self._extract_metadata(full_text_blob, self.GPA_PATTERN)
        
        gpa_val = 0.0
        if gpa_str:
            try:
                gpa_val = float(gpa_str)
            except ValueError:
                logger.warning(f"Could not parse GPA string: {gpa_str}")

        # 2. Extract Courses using Line Scanning
        parsed_courses = self._scan_lines_for_courses(full_text_lines)

        logger.info(f"Parsing complete. Found {len(parsed_courses)} valid courses for {student_name}.")

        return StudentTranscript(
            student_id=student_id,
            student_name=student_name,
            courses=parsed_courses,
            gpa_raw=gpa_val
        )

    def _extract_metadata(self, text: str, pattern: re.Pattern) -> Optional[str]:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _scan_lines_for_courses(self, lines: List[str]) -> List[ParsedCourse]:
        """
        Iterates through every line of text, looking for a valid Course Code and a Grade.
        If found, fetches details from KnowledgeBase.
        """
        results = []
        seen_codes: Set[str] = set()

        for line in lines:
            # 1. Look for a Code
            code_match = self.CODE_PATTERN.search(line)
            if not code_match:
                continue # Not a course line
            
            raw_code = code_match.group(1).upper().strip()

            # 2. Look for a Grade on the same line
            # We use findall because multiple grades might appear (unlikely but possible in messy text)
            # usually the last match is the actual grade for that row
            grade_matches = self.GRADE_PATTERN.findall(line)
            if not grade_matches:
                # Might be a wrapped line or header? Skip for safety.
                continue
            
            grade_letter = grade_matches[-1].strip().upper() # Take the last found grade pattern
            
            # 3. Check for Duplicates (PDF headers often repeat on new pages)
            if raw_code in seen_codes:
                continue

            # 4. SOURCE OF TRUTH LOOKUP
            # We have the Code and the Grade. Now get the Facts.
            meta = knowledge_base.get_course_metadata(raw_code)
            
            if not meta:
                # If course is in PDF but not in our YAML, we log it and skip.
                # This ensures we don't pollute the profile with unknown data.
                logger.debug(f"Course {raw_code} found in PDF but not in KnowledgeBase. Skipping.")
                continue

            # 5. Construct Object
            try:
                grade_val = self.GRADE_MAP.get(grade_letter, 0.0)
                
                course_obj = ParsedCourse(
                    code=meta.code,      # From YAML
                    name=meta.name,      # From YAML
                    sks=meta.sks,        # From YAML
                    grade_letter=grade_letter, # From PDF
                    grade_value=grade_val      # Mapped
                )
                results.append(course_obj)
                seen_codes.add(raw_code)
                
            except Exception as e:
                logger.warning(f"Error constructing ParsedCourse for {raw_code}: {e}")
                continue

        return results

# Singleton Instance
parser_service = TranscriptParser()