from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

bp = Blueprint("keywords", __name__, url_prefix="/api/keywords")

_TOKEN = r"[A-Za-z][A-Za-z+\-#\.0-9]*"

def _clean(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "").strip())

@bp.post("/match")
@jwt_required()
def match():
    data = request.get_json() or {}
    resume_text = _clean(data.get("resume_text"))
    job_description = _clean(data.get("job_description"))

    if not resume_text or not job_description:
        return jsonify({"error": "resume_text and job_description are required"}), 400

    vec = TfidfVectorizer(stop_words="english")
    tfidf = vec.fit_transform([resume_text, job_description])
    score = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)

    jd_terms = {t for t in re.findall(_TOKEN, job_description.lower()) if len(t) > 2}
    rs_terms = {t for t in re.findall(_TOKEN, resume_text.lower()) if len(t) > 2}
    missing = sorted(list(jd_terms - rs_terms))[:50]

    return jsonify({"match_score": round(score, 2), "missing_keywords": missing}), 200
