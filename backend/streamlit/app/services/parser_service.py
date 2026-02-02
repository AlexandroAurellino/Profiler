import re
import pdfplumber
import logging
from io import BytesIO
from typing import List, Set

# Import Knowledge Base
from app.services.knowledge_base import knowledge_base
from app.models.schemas import StudentTranscript, ParsedCourse

# Logger
logger = logging.getLogger("ahp_profiler")

class TranscriptParser:
    """
    Robust Parser for 'Two-Column' Academic Transcripts.
    """

    # ==========================================
    # REGEX EXPLANATION
    # ==========================================
    # 1. (TI|MH|EL)\d{4}  -> Capture Code (Group 1). Matches TI, MH, or EL followed by 4 digits.
    # 2. \s+              -> Require space after code.
    # 3. .*?              -> Non-greedy match for Course Name (eats everything until the next part).
    # 4. \s+              -> Require space before SKS.
    # 5. (\d{1,2})        -> Capture SKS (Group 2). 1 or 2 digits.
    # 6. \s+              -> Require space before Grade.
    # 7. ([A-E][+-]?)     -> Capture Grade (Group 3). A-E, optional +/-.
    
    # We use DOTALL mode implicitly via findall logic on page text
    COURSE_REGEX = re.compile(r"((?:TI|MH|EL)\d{4})\s+.*?\s+(\d{1,2})\s+([A-E][+-]?)")

    # Metadata Patterns
    NIM_PATTERN = re.compile(r"No\.?\s*Mahasiswa\s*[:]\s*(\d+)", re.IGNORECASE)
    NAME_PATTERN = re.compile(r"Nama\s*[:]\s*([^\n\r]+?)(?=\s+(?:Fakultas|Program|$))", re.IGNORECASE)

    GRADE_MAP = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0,
        'D': 1.0, 'E': 0.0
    }

    def parse_pdf(self, file_bytes: bytes) -> StudentTranscript:
        full_text = ""
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    # extract_text() puts all text in a stream. 
                    # This works better for 2-column layouts than splitting by newline.
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            print(f"Error reading PDF: {e}")
            raise ValueError("Invalid PDF file.")

        # 1. Extract Metadata
        student_id = self._extract_metadata(full_text, self.NIM_PATTERN)
        student_name = self._extract_metadata(full_text, self.NAME_PATTERN)
        
        # 2. Extract Courses using Global FindAll
        parsed_courses = self._extract_courses(full_text)

        # Debugging Output to Console
        print(f"--- DEBUG: PARSED {len(parsed_courses)} COURSES ---")
        if not parsed_courses:
            print("WARNING: 0 Courses found. Printing raw text sample:")
            print(full_text[:500]) # Print first 500 chars to debug

        return StudentTranscript(
            student_id=student_id if student_id else "UNKNOWN",
            student_name=student_name if student_name else "Student",
            courses=parsed_courses,
            gpa_raw=0.0 # We let the AHP service calculate scores, or you can calc GPA here
        )

    def _extract_metadata(self, text: str, pattern: re.Pattern) -> str:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_courses(self, text: str) -> List[ParsedCourse]:
        results = []
        seen_codes: Set[str] = set()

        # findall returns a list of tuples: [(Code, SKS, Grade), (Code, SKS, Grade)...]
        matches = self.COURSE_REGEX.findall(text)

        for code, sks_str, grade_letter in matches:
            raw_code = code.strip().upper()
            
            # Avoid duplicates (PDF headers often repeat)
            if raw_code in seen_codes:
                continue

            # --- SOURCE OF TRUTH LOOKUP ---
            # We trust the Code, SKS, and Grade from PDF.
            # We trust the Name from YAML (if available).
            
            meta = knowledge_base.get_course_metadata(raw_code)
            
            # Default Name if not in YAML
            course_name = meta.name if meta else "Unknown Course (YAML Missing)"
            
            # Trust PDF SKS (Evidence) or YAML SKS (Fact)? 
            # Ideally PDF, but YAML is safer for logic. Let's use YAML if available, else PDF.
            sks_val = meta.sks if meta else int(sks_str)

            try:
                grade_val = self.GRADE_MAP.get(grade_letter, 0.0)
                
                results.append(ParsedCourse(
                    code=raw_code,
                    name=course_name,
                    sks=sks_val,
                    grade_letter=grade_letter,
                    grade_value=grade_val
                ))
                seen_codes.add(raw_code)
                
                # Debug print for every successful find
                # print(f"  [MATCH] {raw_code} | {grade_letter} | {course_name}")

            except Exception as e:
                print(f"Error constructing object for {raw_code}: {e}")
                continue

        # Check for items in PDF but not in YAML
        for r in results:
            if "YAML Missing" in r.name:
                print(f"  [WARN] Course {r.code} found in PDF but not in courses.yaml")

        return results

parser_service = TranscriptParser()