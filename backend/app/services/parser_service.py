import re
import pdfplumber
import logging
from io import BytesIO
from typing import List, Dict, Optional

from app.models.schemas import (
    StudentTranscript,
    ParsedCourse,
    GradeLetter
)

logger = logging.getLogger("ahp_profiler")

class TranscriptParser:
    """
    Service responsible for extracting structured data from raw PDF bytes.
    Specific to the Campus 'Daftar Nilai' format.
    """

    # ==========================================
    # REGEX PATTERNS (The Eyes of the Parser)
    # ==========================================
    
    # Matches: TI6043 (2 letters, 4 digits)
    # Followed by: Course Name (variable length)
    # Followed by: SKS (1 digit)
    # Followed by: Grade (A, A-, B+, etc)
    # Explanation:
    #   ([A-Z]{2}\d{4})  -> Group 1: Code
    #   \s+              -> Space
    #   (.*?)            -> Group 2: Name (Non-greedy)
    #   \s+              -> Space
    #   (\d{1,2})        -> Group 3: SKS (1 or 2 digits)
    #   \s+              -> Space
    #   ([A-E][+-]?)     -> Group 4: Grade
    COURSE_PATTERN = re.compile(r"([A-Z]{2}\d{4})\s+(.*?)\s+(\d{1,2})\s+([A-E][+-]?)")

    # Metadata Patterns
    NIM_PATTERN = re.compile(r"No\.?\s*Mahasiswa\s*[:]\s*(\d+)", re.IGNORECASE)
    NAME_PATTERN = re.compile(r"Nama\s*[:]\s*([^\n\r]+?)(?=\s+(?:Fakultas|Program|$))", re.IGNORECASE)
    GPA_PATTERN = re.compile(r"IP\s*Kumulatif\s*[:]\s*([\d\.]+)", re.IGNORECASE)

    # Grade to Value Mapping
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
        
        full_text = ""
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                # Iterate through all pages
                for page_num, page in enumerate(pdf.pages):
                    # extract_text() usually handles multi-column layouts 
                    # by reading left-to-right, top-to-bottom line by line.
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                        
            logger.debug(f"Extracted {len(full_text)} characters from PDF.")
            
        except Exception as e:
            logger.error(f"PDFPlumber failed: {str(e)}")
            raise ValueError("Invalid PDF file or corrupted format.")

        # 1. Extract Metadata
        student_id = self._extract_metadata(full_text, self.NIM_PATTERN)
        student_name = self._extract_metadata(full_text, self.NAME_PATTERN)
        gpa_str = self._extract_metadata(full_text, self.GPA_PATTERN)
        
        gpa_val = 0.0
        if gpa_str:
            try:
                gpa_val = float(gpa_str)
            except ValueError:
                logger.warning(f"Could not parse GPA: {gpa_str}")

        # 2. Extract Courses
        parsed_courses = self._extract_courses(full_text)

        if not parsed_courses:
            logger.warning("No courses were found in the PDF. Regex might need adjustment.")

        logger.info(f"Successfully parsed {len(parsed_courses)} courses for student {student_name}.")

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

    def _extract_courses(self, text: str) -> List[ParsedCourse]:
        results = []
        
        # findall returns a list of tuples: [(Code, Name, SKS, Grade), ...]
        matches = self.COURSE_PATTERN.findall(text)
        
        for match in matches:
            code, raw_name, sks_str, grade_letter = match
            
            # Clean Data
            clean_name = raw_name.strip()
            # Optional: Remove "MBKM" suffix if you want cleaner names
            # clean_name = clean_name.replace(" MBKM", "") 
            
            try:
                sks_val = int(sks_str)
                grade_val = self.GRADE_MAP.get(grade_letter, 0.0)
                
                course_obj = ParsedCourse(
                    code=code,
                    name=clean_name,
                    sks=sks_val,
                    grade_letter=grade_letter,
                    grade_value=grade_val
                )
                results.append(course_obj)
            except Exception as e:
                logger.warning(f"Skipping malformed row: {match} - Error: {e}")
                continue

        return results

# Singleton instance
parser_service = TranscriptParser()