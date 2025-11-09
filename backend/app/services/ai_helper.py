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

    def generateInterviewFeedback(self, question: str, answer: str, role: str = "", company: str = "") -> dict:
        """
        Generate AI feedback for an interview answer.
        Returns structured feedback with summary, strengths, and suggestions.
        """
        # Heuristic-based feedback (similar to frontend, but more comprehensive)
        words = answer.split()
        word_count = len(words)
        char_count = len(answer)
        
        # Check for STAR structure
        has_situation = any(word in answer.lower() for word in ["situation", "context", "background", "when"])
        has_task = any(word in answer.lower() for word in ["task", "goal", "objective", "challenge", "needed"])
        has_action = any(word in answer.lower() for word in ["action", "did", "implemented", "created", "developed", "worked"])
        has_result = any(word in answer.lower() for word in ["result", "outcome", "impact", "achieved", "improved", "increased", "decreased", "saved"])
        has_star = has_situation and has_task and has_action and has_result
        
        # Check for metrics/quantifiable results
        mentions_metrics = any(word in answer.lower() for word in [
            "percent", "%", "metric", "kpi", "score", "rating", 
            "reduced", "improved", "increased", "decreased", "saved",
            "faster", "slower", "more", "less", "better", "worse"
        ])
        
        # Check for technical terms (if role is technical)
        is_technical = any(term in role.lower() for term in ["engineer", "developer", "programmer", "software", "data", "tech"])
        has_technical_terms = any(term in answer.lower() for term in [
            "code", "algorithm", "system", "api", "database", "framework", 
            "deploy", "test", "debug", "optimize", "architecture"
        ]) if is_technical else True
        
        # Build strengths
        strengths = []
        if word_count > 120:
            strengths.append("Thorough explanation with good depth and detail.")
        elif word_count > 60:
            strengths.append("Concise and focused response.")
        else:
            strengths.append("Brief and direct communication.")
        
        if has_star:
            strengths.append("Uses STAR structure effectively (Situation, Task, Action, Result).")
        elif has_situation and has_action:
            strengths.append("Provides context and describes actions taken.")
        
        if mentions_metrics:
            strengths.append("Highlights measurable impact and quantifiable results.")
        
        if has_technical_terms and is_technical:
            strengths.append("Uses appropriate technical terminology.")
        
        if char_count > 500:
            strengths.append("Comprehensive answer that demonstrates experience.")
        
        if not strengths:
            strengths.append("Clear and direct communication.")
        
        # Build suggestions
        suggestions = []
        if word_count < 60:
            suggestions.append("Consider adding more detail to demonstrate depth of experience.")
        elif word_count > 300:
            suggestions.append("Consider being more concise while maintaining key points.")
        
        if not has_star:
            if not has_situation:
                suggestions.append("Add context about the situation or background.")
            if not has_task:
                suggestions.append("Clearly state the task or objective you were working on.")
            if not has_action:
                suggestions.append("Describe the specific actions you took.")
            if not has_result:
                suggestions.append("Highlight the results or outcomes achieved.")
        
        if not mentions_metrics:
            suggestions.append("Add quantifiable metrics or measurable results to strengthen your answer.")
        
        if is_technical and not has_technical_terms:
            suggestions.append("Consider mentioning specific technologies or technical approaches used.")
        
        if not suggestions:
            suggestions.append("Excellent answer! Minor refinements could enhance clarity.")
        
        # Generate summary
        summary_parts = []
        summary_parts.append(f"~{word_count} words")
        if has_star:
            summary_parts.append("STAR structure detected")
        else:
            summary_parts.append("STAR structure partially present")
        if mentions_metrics:
            summary_parts.append("includes measurable impact")
        else:
            summary_parts.append("could benefit from metrics")
        
        summary = ". ".join(summary_parts) + "."
        
        return {
            "summary": summary,
            "strengths": strengths,
            "suggestions": suggestions
        }

    def scoreInterviewAnswer(self, question: str, answer: str) -> float:
        """
        Score an interview answer on a scale of 0-100.
        Returns a float score.
        """
        if not answer or not answer.strip():
            return 0.0
        
        words = answer.split()
        word_count = len(words)
        char_count = len(answer)
        
        score = 50.0  # Base score
        
        # Length scoring (optimal: 100-200 words)
        if 100 <= word_count <= 200:
            score += 15
        elif 60 <= word_count < 100 or 200 < word_count <= 300:
            score += 10
        elif word_count < 60:
            score += 5
        
        # STAR structure scoring
        has_situation = any(word in answer.lower() for word in ["situation", "context", "background", "when"])
        has_task = any(word in answer.lower() for word in ["task", "goal", "objective", "challenge", "needed"])
        has_action = any(word in answer.lower() for word in ["action", "did", "implemented", "created", "developed", "worked"])
        has_result = any(word in answer.lower() for word in ["result", "outcome", "impact", "achieved", "improved", "increased", "decreased", "saved"])
        
        star_count = sum([has_situation, has_task, has_action, has_result])
        score += star_count * 5  # 5 points per STAR component
        
        # Metrics scoring
        mentions_metrics = any(word in answer.lower() for word in [
            "percent", "%", "metric", "kpi", "score", "rating", 
            "reduced", "improved", "increased", "decreased", "saved",
            "faster", "slower", "more", "less", "better", "worse"
        ])
        if mentions_metrics:
            score += 10
        
        # Ensure score is between 0 and 100
        score = max(0.0, min(100.0, score))
        
        return round(score, 2)