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
            "extracted_data": {"name": None, "email": None, "phone": None, "summary": None, "skills": [], "work_experience": [], "education": []}
        }

    def extractResumeFields(self, text: str) -> dict:
        """
        Uses Gemini to extract structured fields from resume text.
        Falls back to regex-based extraction if LLM is unavailable.
        """
        default_fields = {
            "name": None,
            "email": None,
            "phone": None,
            "summary": None,
            "skills": [],
            "work_experience": [],
            "education": [],
        }

        if not text or not text.strip():
            return default_fields

        if self.model:
            try:
                prompt = f"""Extract the following fields from this resume text as JSON.
Return ONLY valid JSON with these exact keys, no extra text, no markdown code blocks:
{{
  "name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "summary": "string or null",
  "skills": ["skill1", "skill2"],
  "work_experience": [
    {{"company": "string", "role": "string", "start_date": "string or null", "end_date": "string or null", "description": "string or null"}}
  ],
  "education": [
    {{"institution": "string", "degree": "string or null", "field": "string or null", "year": "string or null"}}
  ]
}}

Resume text:
{text[:4000]}"""
                response = self.model.generate_content(prompt)
                content = self._clean_json_text(response.text)
                parsed = json.loads(content)
                return self._normalize_extracted_fields(parsed)
            except Exception as e:
                print(f"⚠️ Field extraction failed, falling back to regex: {e}")

        return self._regex_extract_fields(text)

    def _normalize_extracted_fields(self, data: dict) -> dict:
        """Ensure extracted fields have the correct types."""
        def clean_str(val):
            s = str(val).strip() if val else None
            return s if s and s.lower() not in ("null", "none", "n/a", "") else None

        return {
            "name": clean_str(data.get("name")),
            "email": clean_str(data.get("email")),
            "phone": clean_str(data.get("phone")),
            "summary": clean_str(data.get("summary")),
            "skills": [str(s).strip() for s in (data.get("skills") or []) if str(s).strip()],
            "work_experience": [
                {
                    "company": str(exp.get("company", "")).strip(),
                    "role": str(exp.get("role", "")).strip(),
                    "start_date": clean_str(exp.get("start_date")),
                    "end_date": clean_str(exp.get("end_date")),
                    "description": clean_str(exp.get("description")),
                }
                for exp in (data.get("work_experience") or [])
                if isinstance(exp, dict)
            ],
            "education": [
                {
                    "institution": str(edu.get("institution", "")).strip(),
                    "degree": clean_str(edu.get("degree")),
                    "field": clean_str(edu.get("field")),
                    "year": clean_str(edu.get("year")),
                }
                for edu in (data.get("education") or [])
                if isinstance(edu, dict)
            ],
        }

    def _regex_extract_fields(self, text: str) -> dict:
        """Basic regex extraction as fallback when LLM is unavailable."""
        import re
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text)
        phone_match = re.search(r'[\+]?[\d][\d\s\-\(\)]{8,15}[\d]', text)
        return {
            "name": None,
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0).strip() if phone_match else None,
            "summary": None,
            "skills": [],
            "work_experience": [],
            "education": [],
        }

    def generateInterviewQuestions(self, role: str = "", company: str = "", count: int = 5) -> list[dict]:
        """
        Generate a fresh set of mock interview questions.
        """
        safe_count = max(3, min(int(count or 5), 8))
        role_text = role or "Software / Data / Intern"
        company_text = company or "the target company"

        if self.model:
            try:
                prompt = f"""
                Generate {safe_count} mock interview questions for a candidate interviewing for a {role_text} role at {company_text}.

                Mix behavioral, situational, and role-specific questions.
                Keep each question realistic, concise, and distinct.

                Return ONLY a JSON array. Each item must have:
                - id: short id like q1
                - prompt: the interview question
                - tags: an array of 2 or 3 short lowercase tags
                """
                response = self.model.generate_content(prompt)
                content = self._clean_json_text(response.text)
                parsed = json.loads(content)
                if isinstance(parsed, list) and parsed:
                    return self._normalize_generated_questions(parsed, safe_count)
            except Exception as e:
                print(f"❌ Gemini Question Generation Error: {e}. Falling back to local questions.")

        return self._fallback_interview_questions(role_text, company_text, safe_count)

    def _normalize_generated_questions(self, questions: list, count: int) -> list[dict]:
        normalized = []
        for index, question in enumerate(questions[:count], start=1):
            if not isinstance(question, dict):
                continue
            prompt = str(question.get("prompt", "")).strip()
            if not prompt:
                continue
            tags = question.get("tags")
            if not isinstance(tags, list):
                tags = []
            normalized.append({
                "id": f"q{index}",
                "prompt": prompt,
                "tags": [str(tag).strip().lower() for tag in tags[:3] if str(tag).strip()],
            })
        return normalized or self._fallback_interview_questions("", "", count)

    def _fallback_interview_questions(self, role: str, company: str, count: int) -> list[dict]:
        role_lower = (role or "").lower()
        pools = {
            "behavioral": [
                "Tell me about a time you had to adapt quickly when priorities changed.",
                "Describe a challenge where you had to balance quality and speed.",
                "Tell me about a time you received difficult feedback and how you responded.",
                "Describe a situation where you had to collaborate with a difficult teammate.",
                "Tell me about a time you took initiative without being asked.",
            ],
            "technical": [
                f"Walk me through a technical project that best prepared you for this {role} role.",
                "Describe a bug or production issue you diagnosed. How did you find the root cause?",
                "How do you approach debugging when you do not immediately know what is wrong?",
                "Tell me about a time you improved performance, reliability, or maintainability in a project.",
                "How do you make tradeoffs when choosing between speed of delivery and long-term quality?",
            ],
            "data": [
                "Tell me about a project where you turned messy data into a useful insight.",
                "How do you validate that your analysis or model is actually reliable?",
                "Describe a time you had to explain a technical finding to a non-technical audience.",
                "How do you handle missing data, noisy data, or conflicting signals?",
                "Walk me through a project where your analysis changed a decision.",
            ],
            "closing": [
                f"Why are you interested in working at {company}?",
                f"What would success look like for you in your first 90 days at {company}?",
                "What is one project in your background you would definitely want to discuss with the hiring team?",
                "What questions would you ask the interviewer about the role, team, or company?",
            ],
        }

        selected = []
        selected.extend(pools["behavioral"][:2])
        if "data" in role_lower or "analyst" in role_lower or "ml" in role_lower:
            selected.extend(pools["data"][:2])
        else:
            selected.extend(pools["technical"][:2])
        selected.extend(pools["closing"][:2])

        seed = sum(ord(ch) for ch in f"{role}|{company}")
        ordered = sorted(selected, key=lambda prompt: (seed + len(prompt)) % 17)
        chosen = ordered[:count]

        return [
            {
                "id": f"q{index}",
                "prompt": prompt,
                "tags": self._question_tags(prompt),
            }
            for index, prompt in enumerate(chosen, start=1)
        ]

    def _question_tags(self, prompt: str) -> list[str]:
        lowered = prompt.lower()
        tags = []
        if any(token in lowered for token in ["time", "situation", "challenge", "feedback", "collaborate"]):
            tags.append("behavioral")
        if any(token in lowered for token in ["debug", "technical", "performance", "tradeoff", "project"]):
            tags.append("technical")
        if any(token in lowered for token in ["data", "analysis", "model", "insight"]):
            tags.append("data")
        if any(token in lowered for token in ["why", "90 days", "questions would you ask"]):
            tags.append("strategy")
        if not tags:
            tags.append("general")
        return tags[:3]

    def generateInterviewFeedback(self, question: str, answer: str, role: str = "", company: str = "") -> dict:
        """
        Generate structured interview feedback with score dimensions.
        """
        prompt_context = f" for a {role} role" if role else ""
        company_context = f" at {company}" if company else ""

        if self.model:
            try:
                prompt = f"""
                You are an expert interviewer evaluating a candidate answer{prompt_context}{company_context}.

                Question: "{question}"
                Candidate Answer: "{answer}"

                Evaluate the answer on these dimensions:
                - accuracy: Did the answer address the question correctly and stay internally consistent?
                - clearness: Was the answer easy to follow, structured, and concise?
                - confidence: Did the answer sound direct and professional without bluffing?

                Return a JSON object with these exact keys:
                - summary: A 1-2 sentence overview of the answer quality.
                - strengths: A list of 2-3 specific strong points.
                - suggestions: A list of 2-3 actionable improvements.
                - metrics: {{
                    "accuracy": {{"score": 1-5, "label": "Needs work|Developing|Solid|Strong|Excellent", "reason": "short reason"}},
                    "clearness": {{"score": 1-5, "label": "Needs work|Developing|Solid|Strong|Excellent", "reason": "short reason"}},
                    "confidence": {{"score": 1-5, "label": "Needs work|Developing|Solid|Strong|Excellent", "reason": "short reason"}}
                  }}
                - overall_score: A number from 0 to 100 computed with this weighting: accuracy 50%, clearness 30%, confidence 20%.
                - evaluator: {{
                    "provider": "gemini",
                    "method": "llm_rubric"
                  }}

                IMPORTANT: Return ONLY the JSON object. Do not wrap it in markdown code blocks.
                """

                response = self.model.generate_content(prompt)
                content = self._clean_json_text(response.text)
                parsed = json.loads(content)
                return self._normalize_interview_feedback(parsed, question, answer)
            except Exception as e:
                print(f"❌ Gemini API Error: {e}. Falling back to heuristics.")

        return self._heuristic_feedback(question, answer, role, company)

    def _clean_json_text(self, content: str) -> str:
        cleaned = (content or "").strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "", 1).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```", "", 1).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned

    def _score_label(self, score: int) -> str:
        if score <= 1:
            return "Needs work"
        if score == 2:
            return "Developing"
        if score == 3:
            return "Solid"
        if score == 4:
            return "Strong"
        return "Excellent"

    def _normalize_metric(self, metric: dict, fallback_reason: str) -> dict:
        raw_score = metric.get("score", 3) if isinstance(metric, dict) else 3
        try:
            score = int(round(float(raw_score)))
        except Exception:
            score = 3
        score = max(1, min(5, score))
        label = metric.get("label") if isinstance(metric, dict) else None
        reason = metric.get("reason") if isinstance(metric, dict) else None
        return {
            "score": score,
            "label": label or self._score_label(score),
            "reason": reason or fallback_reason,
        }

    def _normalize_interview_feedback(self, payload: dict, question: str, answer: str) -> dict:
        metrics = payload.get("metrics") or {}
        normalized_metrics = {
            "accuracy": self._normalize_metric(
                metrics.get("accuracy", {}),
                "The answer was judged for relevance and internal consistency.",
            ),
            "clearness": self._normalize_metric(
                metrics.get("clearness", {}),
                "The answer was judged for structure and readability.",
            ),
            "confidence": self._normalize_metric(
                metrics.get("confidence", {}),
                "The answer was judged for directness and professional tone.",
            ),
        }

        weighted = (
            normalized_metrics["accuracy"]["score"] * 0.5 +
            normalized_metrics["clearness"]["score"] * 0.3 +
            normalized_metrics["confidence"]["score"] * 0.2
        )
        overall_score = round((weighted / 5.0) * 100, 2)

        strengths = payload.get("strengths") if isinstance(payload.get("strengths"), list) else []
        suggestions = payload.get("suggestions") if isinstance(payload.get("suggestions"), list) else []
        summary = payload.get("summary") or "Interview answer evaluation completed."
        evaluator = payload.get("evaluator") if isinstance(payload.get("evaluator"), dict) else {}

        return {
            "summary": summary,
            "strengths": strengths[:3] or ["The answer addresses the prompt with relevant content."],
            "suggestions": suggestions[:3] or ["Add one more concrete example or measurable outcome."],
            "metrics": normalized_metrics,
            "overall_score": overall_score,
            "evaluator": {
                "provider": evaluator.get("provider", "gemini" if self.model else "heuristic"),
                "method": evaluator.get("method", "llm_rubric" if self.model else "rule_based"),
            },
            "question": question,
            "answer_excerpt": answer[:140],
        }

    def _heuristic_feedback(self, question, answer, role, company):
        words = answer.split()
        word_count = len(words)
        answer_lower = answer.lower()
        question_lower = question.lower()

        question_terms = {
            token.strip(".,!?")
            for token in question_lower.split()
            if len(token.strip(".,!?")) > 3
        }
        answer_terms = {
            token.strip(".,!?")
            for token in answer_lower.split()
            if len(token.strip(".,!?")) > 3
        }
        overlap = len(question_terms & answer_terms)

        behavioral_markers = sum(
            1 for token in ["example", "when", "project", "team", "deadline", "challenge", "situation"]
            if token in question_lower
        )
        technical_markers = sum(
            1 for token in ["system", "debug", "algorithm", "database", "api", "performance", "bug"]
            if token in question_lower
        )

        star_terms = sum(
            1 for token in ["situation", "task", "action", "result"] if token in answer_lower
        )
        impact_signals = sum(
            1 for token in ["%", "percent", "improved", "reduced", "increased", "saved", "grew", "delivered"]
            if token in answer_lower
        )
        evidence_signals = sum(
            1 for token in ["for example", "for instance", "specifically", "because", "so that", "which led to"]
            if token in answer_lower
        )
        ownership_signals = sum(
            1 for token in ["i led", "i built", "i created", "i implemented", "i owned", "i drove", "i resolved"]
            if token in answer_lower
        )
        filler_signals = sum(
            1 for token in ["maybe", "i guess", "kind of", "sort of", "probably", "i think"]
            if token in answer_lower
        )
        sentence_count = max(1, answer.count(".") + answer.count("!") + answer.count("?"))
        avg_sentence_length = word_count / sentence_count
        long_run_on_penalty = 1 if avg_sentence_length > 32 else 0
        very_short_penalty = 1 if word_count < 25 else 0
        very_long_penalty = 1 if word_count > 260 else 0

        strengths = []
        suggestions = []

        accuracy_score = 1
        if overlap >= 2:
            accuracy_score += 1
        if overlap >= 4:
            accuracy_score += 1
        if evidence_signals > 0:
            accuracy_score += 1
        if technical_markers > 0 and any(token in answer_lower for token in ["tradeoff", "root cause", "latency", "query", "cache", "test"]):
            accuracy_score += 1
        if behavioral_markers > 0 and (star_terms >= 2 or impact_signals > 0):
            accuracy_score += 1
        if very_short_penalty:
            accuracy_score -= 1
        accuracy_score = min(5, accuracy_score)
        accuracy_score = max(1, accuracy_score)

        clearness_score = 1
        if 35 <= word_count <= 180:
            clearness_score += 1
        if star_terms >= 2 or any(token in answer_lower for token in ["first", "then", "finally"]):
            clearness_score += 1
        if avg_sentence_length <= 24:
            clearness_score += 1
        if evidence_signals > 0 and very_long_penalty == 0:
            clearness_score += 1
        clearness_score -= long_run_on_penalty
        clearness_score -= very_short_penalty
        clearness_score -= very_long_penalty
        clearness_score = min(5, clearness_score)
        clearness_score = max(1, clearness_score)

        confidence_score = 1
        if "i " in answer_lower or "my " in answer_lower:
            confidence_score += 1
        if ownership_signals > 0:
            confidence_score += 1
        if filler_signals == 0 and word_count >= 25:
            confidence_score += 1
        if impact_signals > 0 or any(token in answer_lower for token in ["confident", "comfortable", "i would", "i can"]):
            confidence_score += 1
        if filler_signals >= 2:
            confidence_score -= 1
        if very_short_penalty:
            confidence_score -= 1
        confidence_score = max(1, min(5, confidence_score))

        if accuracy_score >= 4:
            strengths.append("The answer stays relevant to the question and includes believable supporting detail.")
        if clearness_score >= 4:
            strengths.append("The response is easy to follow and has a clear structure.")
        if confidence_score >= 4:
            strengths.append("The delivery sounds direct and professional without too much hedging.")
        if impact_signals > 0:
            strengths.append("The answer includes outcome-oriented language that strengthens credibility.")

        if accuracy_score <= 3:
            suggestions.append("Tie the answer more directly to the question and add one concrete example.")
        if clearness_score <= 3:
            suggestions.append("Use a tighter STAR-style structure so the answer is easier to follow.")
        if confidence_score <= 3:
            suggestions.append("Use more direct language and reduce hesitant phrases unless uncertainty is necessary.")
        if impact_signals == 0:
            suggestions.append("Add a measurable result or outcome to make the answer more convincing.")

        weighted = accuracy_score * 0.5 + clearness_score * 0.3 + confidence_score * 0.2
        overall_score = round((weighted / 5.0) * 100, 2)

        if overall_score >= 80:
            summary = "This answer is strong overall: it addresses the question clearly and sounds credible."
        elif overall_score >= 60:
            summary = "This answer is reasonably solid, but it would benefit from more specificity or sharper structure."
        elif overall_score >= 40:
            summary = "This answer shows the right direction, but it needs clearer structure and stronger supporting detail."
        else:
            summary = "This answer needs more development to feel complete, clear, and convincing."

        return {
            "summary": summary,
            "strengths": strengths[:3] or ["The answer is relevant to the interview topic."],
            "suggestions": suggestions[:3] or ["Add a little more detail and a concrete outcome."],
            "metrics": {
                "accuracy": {
                    "score": accuracy_score,
                    "label": self._score_label(accuracy_score),
                    "reason": "Based on how directly the answer addressed the prompt and whether it included consistent supporting detail.",
                },
                "clearness": {
                    "score": clearness_score,
                    "label": self._score_label(clearness_score),
                    "reason": "Based on structure, conciseness, and how easy the response was to follow.",
                },
                "confidence": {
                    "score": confidence_score,
                    "label": self._score_label(confidence_score),
                    "reason": "Based on direct ownership language, reduced hedging, and professional tone.",
                },
            },
            "overall_score": round((weighted / 5.0) * 100, 2),
            "evaluator": {
                "provider": "heuristic",
                "method": "rule_based",
            },
        }

    def scoreInterviewAnswer(self, question: str, answer: str) -> float:
        """
        Returns the overall interview score from the structured evaluator.
        """
        if not answer or not answer.strip():
            return 0.0
        evaluation = self.generateInterviewFeedback(question, answer)
        return float(evaluation.get("overall_score", 0.0))

    def scoreResume(self, parsed_resume: dict) -> dict:
        """
        Evaluate a resume and return a simple score payload for dashboard/report use.
        """
        sections = parsed_resume.get("sections") or []
        full_text = ""
        for section in sections:
            if section.get("name") == "full_content":
                full_text = section.get("content") or ""
                break

        text = full_text.strip()
        if not text:
            return {
                "score": 0,
                "summary": "Resume could not be evaluated because no text was extracted.",
                "details": {
                    "checks": {
                        "has_email": False,
                        "has_phone": False,
                        "has_skills_section": False,
                        "has_experience_section": False,
                        "has_education_section": False,
                        "has_project_section": False,
                        "length_ok": False,
                    }
                },
            }

        lowered = text.lower()
        word_count = len(text.split())
        checks = {
            "has_email": "@" in text,
            "has_phone": any(ch.isdigit() for ch in text) and sum(ch.isdigit() for ch in text) >= 10,
            "has_skills_section": "skill" in lowered,
            "has_experience_section": "experience" in lowered,
            "has_education_section": "education" in lowered,
            "has_project_section": "project" in lowered or "projects" in lowered,
            "length_ok": 200 <= word_count <= 900,
        }

        score = 30
        score += 10 if checks["has_email"] else 0
        score += 10 if checks["has_phone"] else 0
        score += 15 if checks["has_skills_section"] else 0
        score += 15 if checks["has_experience_section"] else 0
        score += 10 if checks["has_education_section"] else 0
        score += 10 if checks["has_project_section"] else 0
        score += 10 if checks["length_ok"] else 0
        score = min(100, score)

        missing = []
        if not checks["has_skills_section"]:
            missing.append("Add a dedicated skills section.")
        if not checks["has_experience_section"]:
            missing.append("Include an experience section with concrete impact.")
        if not checks["has_project_section"]:
            missing.append("Include at least one project with measurable outcomes.")
        if not checks["length_ok"]:
            missing.append("Keep the resume content within a focused one-page to two-page range.")

        summary = "Resume evaluation completed."
        if missing:
            summary = "Resume evaluation completed with improvement opportunities."

        return {
            "score": score,
            "summary": summary,
            "details": {
                "word_count": word_count,
                "checks": checks,
                "suggestions": missing,
            },
        }
