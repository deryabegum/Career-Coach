import os
import fitz  # PyMuPDF
import docx  # python-docx
import json
import re
import google.generativeai as genai
from flask import current_app
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class AIHelper:
    """
    Handles AI interactions using dynamic model selection to prevent 404 errors.
    """
    
    def __init__(self):
        # API anahtarını .env dosyasından al
        api_key = os.getenv("GOOGLE_API_KEY")
        self.model = None
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                
                # 1. Mevcut ve desteklenen modelleri listele
                available_models = []
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                except Exception as e:
                    print(f"⚠️ Model listesi alınırken hata: {e}")

                print(f"ℹ️ Erişilebilir Modeller: {available_models}")

                # 2. En uygun modeli seç (Flash > Pro > Diğerleri)
                target_model = None
                preferences = [
                    'models/gemini-1.5-flash',
                    'models/gemini-1.5-flash-latest',
                    'models/gemini-1.5-pro',
                    'models/gemini-1.5-pro-latest',
                    'models/gemini-1.0-pro',
                    'models/gemini-pro'
                ]

                # Tercih listesinden, mevcut modeller içinde olan ilkini seç
                for pref in preferences:
                    if pref in available_models:
                        target_model = pref
                        break
                
                # Eğer tercihlerden hiçbiri yoksa, listenin başındaki herhangi bir modeli al
                if not target_model and available_models:
                    target_model = available_models[0]

                if target_model:
                    print(f"✅ Seçilen Model: {target_model}")
                    self.model = genai.GenerativeModel(target_model)
                else:
                    print("❌ Uygun bir model bulunamadı (generateContent destekleyen).")

            except Exception as e:
                print(f"❌ AI Client Init Error: {e}")
        else:
            print("⚠️  UYARI: GOOGLE_API_KEY bulunamadı. Yerel mantık kullanılacak.")

    def _read_docx(self, filepath):
        try:
            document = docx.Document(filepath)
            return '\n'.join([paragraph.text for paragraph in document.paragraphs])
        except Exception as e:
            current_app.logger.error(f"Error reading DOCX {filepath}: {e}")
            return None

    def _read_pdf(self, filepath):
        try:
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            current_app.logger.error(f"Error reading PDF {filepath}: {e}")
            return None

    def _extract_json(self, text: str):
        if not text:
            return None
        # Try to extract the first JSON object in the response.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    def parseResume(self, filepath: str) -> dict:
        """
        CV dosyasından metin okur.
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.pdf':
            raw_text = self._read_pdf(filepath)
        elif ext == '.docx':
            raw_text = self._read_docx(filepath)
        else:
            return {"error": "Unsupported file type."}

        if not raw_text:
            return {"error": "Failed to extract text."}

        return {
            "summary": "Text extracted successfully.",
            "raw_text": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text,
            "sections": [{"name": "full_content", "content": raw_text}],
            "extracted_data": {"name": "Candidate", "email": "N/A", "skills": [], "experience_count": 0}
        }

    def scoreResume(self, resume_text: str) -> dict:
        """
        Score resume on a 0-100 scale. Returns dict with score + feedback.
        """
        resume_text = (resume_text or "").strip()
        if not resume_text:
            return {
                "score": 0,
                "summary": "No resume content provided.",
                "strengths": [],
                "weaknesses": ["Missing resume content."],
                "suggestions": ["Add resume content to receive a score."],
            }

        if self.model:
            try:
                prompt = f"""
You are an expert resume reviewer. Score the resume from 0 to 100.
Evaluate clarity, structure, impact, relevance, concision, and grammar.
Return ONLY valid JSON with these exact keys:
score (integer 0-100), summary (string), strengths (array of 3 short strings),
weaknesses (array of 3 short strings), suggestions (array of 3 short strings).

Resume text:
\"\"\"{resume_text[:8000]}\"\"\"
"""
                response = self.model.generate_content(prompt)
                content = response.text
                parsed = self._extract_json(content)
                if parsed and "score" in parsed:
                    # Normalize types
                    parsed["score"] = int(float(parsed.get("score", 0)))
                    parsed["strengths"] = parsed.get("strengths") or []
                    parsed["weaknesses"] = parsed.get("weaknesses") or []
                    parsed["suggestions"] = parsed.get("suggestions") or []
                    return parsed
            except Exception as e:
                print(f"❌ Resume scoring failed, falling back to heuristics: {e}")

        # Heuristic fallback
        words = len(resume_text.split())
        has_contact = bool(re.search(r"@|phone|linkedin", resume_text.lower()))
        has_metrics = bool(re.search(r"\b\d+%|\b\d+\s*(users|customers|months|years)\b", resume_text.lower()))
        has_sections = any(k in resume_text.lower() for k in ["experience", "education", "skills", "projects"])

        score = 60
        if words >= 200: score += 10
        if words >= 400: score += 5
        if has_contact: score += 5
        if has_sections: score += 10
        if has_metrics: score += 10
        score = min(100, score)

        strengths = []
        weaknesses = []
        suggestions = []
        if has_sections: strengths.append("Resume includes clear sections.")
        else: weaknesses.append("Missing clear section headings.")
        if has_metrics: strengths.append("Includes quantifiable impact.")
        else: suggestions.append("Add metrics to highlight impact (e.g., % improvements).")
        if words < 200: weaknesses.append("Resume content is too brief.")
        if not has_contact: suggestions.append("Add contact details (email/LinkedIn).")

        if not strengths: strengths.append("Relevant resume content present.")
        if not weaknesses: weaknesses.append("No major structural issues detected.")
        if not suggestions: suggestions.append("Consider tightening wording for clarity.")

        return {
            "score": score,
            "summary": "Heuristic score generated (AI unavailable).",
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "suggestions": suggestions[:3],
        }

    def generateInterviewFeedback(self, question: str, answer: str, role: str = "", company: str = "") -> dict:
        """
        AI Feedback üretir.
        """
        # --- PLAN A: GERÇEK AI (Google Gemini) ---
        if self.model:
            try:
                prompt = f"""
                You are an expert technical interviewer for a {role} position at {company}.
                
                Question: "{question}"
                Candidate Answer: "{answer}"
                
                Analyze the answer and provide a JSON response with these exact keys:
                - summary: A 1-2 sentence overview of the answer quality.
                - strengths: A list of 2-3 specific strong points.
                - suggestions: A list of 2-3 actionable improvements.
                
                IMPORTANT: Return ONLY the JSON object. Do not wrap it in markdown code blocks.
                """
                
                response = self.model.generate_content(prompt)
                
                content = response.text
                # Temizlik
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "")
                elif content.startswith("```"):
                    content = content.replace("```", "")
                
                return json.loads(content)
                
            except Exception as e:
                # Log hatayı ama uygulamanın çökmesine izin verme
                print(f"❌ Gemini API Error: {e}. Falling back to heuristics.")
                
        # --- PLAN B: YEDEK PLAN (Heuristic) ---
        return self._heuristic_feedback(question, answer, role)

    def _heuristic_feedback(self, question, answer, role):
        """
        API anahtarı veya bağlantı yoksa çalışacak basit mantık.
        """
        words = answer.split()
        word_count = len(words)
        
        has_action = any(w in answer.lower() for w in ["action", "i did", "implemented", "created"])
        
        strengths = []
        suggestions = []
        
        if word_count > 30: strengths.append("Good amount of detail.")
        else: suggestions.append("Please elaborate more on your experience.")
        
        if has_action: strengths.append("Clear description of actions taken.")
        else: suggestions.append("Focus more on what YOU specifically did (Action).")
        
        if not strengths: strengths.append("Answer is relevant to the topic.")
        if not suggestions: suggestions.append("Try to provide concrete examples.")
        
        return {
            "summary": "AI Service unavailable (Quota/Error). Basic analysis provided.",
            "strengths": strengths,
            "suggestions": suggestions
        }

    def scoreInterviewAnswer(self, question: str, answer: str) -> float:
        """
        Cevaba 0-100 arası puan verir.
        """
        if not answer or not answer.strip():
            return 0.0

        if self.model:
            try:
                prompt = f"""
You are an expert interviewer. Score the candidate's answer from 0 to 100.
Evaluate structure (STAR), specificity, impact, clarity, and relevance.
Return ONLY JSON with keys: score (number), summary (string),
strengths (array), suggestions (array).

Question: "{question}"
Answer: "{answer}"
"""
                response = self.model.generate_content(prompt)
                parsed = self._extract_json(response.text)
                if parsed and "score" in parsed:
                    return float(parsed.get("score", 0))
            except Exception as e:
                print(f"❌ Interview scoring failed, falling back to heuristics: {e}")

        words = len(answer.split())
        score = 60.0
        if 50 <= words <= 300: score += 20
        if "result" in answer.lower(): score += 10
        if "action" in answer.lower(): score += 10
        return min(100.0, score)
