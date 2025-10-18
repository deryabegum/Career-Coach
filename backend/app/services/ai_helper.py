# backend/app/services/ai_helper.py
import os
import fitz  # PyMuPDF
import docx  # python-docx
import json
from flask import current_app

class AIHelper:
    """
    Handles AI interactions, including resume parsing and analysis.
    For this step, we only implement file content extraction.
    """
    
    def _read_docx(self, filepath):
        """Reads text from a DOCX file."""
        try:
            document = docx.Document(filepath)
            return '\n'.join([paragraph.text for paragraph in document.paragraphs])
        except Exception as e:
            current_app.logger.error(f"Error reading DOCX {filepath}: {e}")
            return None

    def _read_pdf(self, filepath):
        """Reads text from a PDF file."""
        try:
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            current_app.logger.error(f"Error reading PDF {filepath}: {e}")
            return None

    def parseResume(self, filepath: str) -> dict:
        """
        Extracts text from a resume file and returns a structured dictionary (JSON).
        This is a basic text extraction. Full AI parsing will be added later.
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        # 1. Extract raw text based on file type
        if ext == '.pdf':
            raw_text = self._read_pdf(filepath)
        elif ext == '.docx':
            raw_text = self._read_docx(filepath)
        else:
            return {"error": "Unsupported file type during parsing."}

        if not raw_text:
            return {"error": "Failed to extract text from file."}

        # 2. Mock Parsing (Return raw text as a 'parsed' section for now)
        # In a later step, you would send raw_text to an LLM (GPT-4) for structured analysis.
        
        # For now, return a basic structure with the full text
        return {
            "summary": "Basic text extracted successfully.",
            "raw_text": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text,
            "sections": [
                {"name": "full_content", "content": raw_text}
            ],
            "extracted_data": {
                "name": "N/A", 
                "email": "N/A", 
                "skills": [], 
                "experience_count": 0
            }
        }