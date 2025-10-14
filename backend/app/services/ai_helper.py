import os
import fitz  # PyMuPDF
import docx

class AIHelper:
    def __init__(self):
        pass

    def _extract_pdf(self, file_path):
        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text.strip()

    def _extract_docx(self, file_path):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs]).strip()

    def parseResume(self, file_path):
        """
        Extracts text and does lightweight parsing.
        """
        print(f"Parsing resume file at: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            text = self._extract_pdf(file_path)
        elif ext == ".docx":
            text = self._extract_docx(file_path)
        else:
            return {"error": "Unsupported file type"}

        # ----- Simple keyword-based parsing -----
        lower_text = text.lower()
        education = [line for line in text.splitlines() if "university" in line or "bachelor" in line or "master" in line]
        experience = [line for line in text.splitlines() if "intern" in line or "engineer" in line or "developer" in line]
        skills = [word for word in ["python", "sql", "java", "c++", "pandas", "flask", "excel"]
                  if word in lower_text]

        parsed_data = {
            "summary": text[:500] + "..." if len(text) > 500 else text,
            "education": education or ["Not found"],
            "experience": experience or ["Not found"],
            "skills": skills or ["Not detected"],
            "warnings": []
        }

        return parsed_data