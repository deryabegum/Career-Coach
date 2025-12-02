import os
import fitz  # PyMuPDF
import docx  # python-docx
import json
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
        
        words = len(answer.split())
        score = 60.0 
        
        if 50 <= words <= 300: score += 20
        if "result" in answer.lower(): score += 10
        if "action" in answer.lower(): score += 10
        
        return min(100.0, score)