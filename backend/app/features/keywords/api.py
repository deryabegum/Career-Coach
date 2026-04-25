from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import numpy as np
import re
import time
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
from urllib.request import urlopen, Request
from urllib.error import URLError
from html import unescape
from functools import lru_cache

from ... import db  # Import the db module from the app's root
from ..progress.service import award_resume_score  # ✅ add progress award

# This blueprint is already registered in your __init__.py
bp = Blueprint("keywords", __name__, url_prefix="/api/keywords")

SIMPLIFY_README_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"
JOBS_CACHE_TTL_SECONDS = 60 * 30
_jobs_cache = {"jobs": [], "fetched_at": 0}
SEMANTIC_MATCH_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<br\s*/?>", ", ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_first_link(html: str) -> str | None:
    match = re.search(r'href="([^"]+)"', html)
    return match.group(1) if match else None


def _parse_jobs_from_readme(markdown: str) -> list[dict]:
    jobs = []
    section_pattern = re.compile(
        r"##\s+(?P<title>.+?)\n.*?<tbody>(?P<body>.*?)</tbody>",
        re.DOTALL,
    )
    row_pattern = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
    cell_pattern = re.compile(r"<td>(.*?)</td>", re.DOTALL)

    for section in section_pattern.finditer(markdown):
        section_title = _strip_html(section.group("title"))
        if "new grad roles" not in section_title.lower():
            continue

        category = section_title.replace("New Grad Roles", "").strip(" -")
        body = section.group("body")
        for row in row_pattern.finditer(body):
            cells = cell_pattern.findall(row.group(1))
            if len(cells) < 5:
                continue

            company_html, role_html, location_html, application_html, age_html = cells[:5]
            company_text = _strip_html(company_html)
            role_text = _strip_html(role_html)
            location_text = _strip_html(location_html)
            age_text = _strip_html(age_html)

            if not company_text or not role_text or company_text.lower() == "company":
                continue

            apply_links = re.findall(r'href="([^"]+)"', application_html)
            apply_url = apply_links[0] if apply_links else None
            simplify_url = apply_links[1] if len(apply_links) > 1 else None
            company_url = _extract_first_link(company_html)

            jobs.append({
                "id": f"{category.lower().replace(' ', '-')}-{len(jobs) + 1}",
                "category": category,
                "company": company_text.replace("🔥", "").strip(),
                "role": role_text.replace("🎓", "").strip(),
                "location": location_text,
                "age": age_text,
                "apply_url": apply_url,
                "simplify_url": simplify_url,
                "company_url": company_url,
                "is_featured": "🔥" in company_text,
                "advanced_degree": "🎓" in role_text,
                "description_seed": f"{company_text} - {role_text} - {location_text} - {category}",
            })

    return jobs


def _fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Career-Coach/1.0"})
    with urlopen(req, timeout=15) as response:
        return response.read().decode("utf-8")


def _html_to_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fetch_job_details(simplify_url: str) -> dict:
    html = _fetch_text(simplify_url)
    match = re.search(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find structured job details on the Simplify page.")

    payload = json.loads(match.group(1))
    description_html = payload.get("description") or ""
    locations = payload.get("jobLocation") or []
    if isinstance(locations, dict):
        locations = [locations]

    location_text = ", ".join(
        filter(
            None,
            [
                _strip_html(
                    " ".join(
                        filter(
                            None,
                            [
                                (((loc or {}).get("address") or {}).get("addressLocality")),
                                (((loc or {}).get("address") or {}).get("addressRegion")),
                                (((loc or {}).get("address") or {}).get("addressCountry")),
                            ],
                        )
                    )
                )
                for loc in locations
            ],
        )
    )

    salary = payload.get("baseSalary") or {}
    salary_value = salary.get("value") or {}
    salary_text = ""
    if salary_value:
        min_value = salary_value.get("minValue")
        max_value = salary_value.get("maxValue")
        currency = salary.get("currency", "USD")
        if min_value and max_value:
            salary_text = f"{currency} {min_value:,} - {max_value:,}"

    return {
        "title": payload.get("title", ""),
        "description": _html_to_text(description_html),
        "date_posted": payload.get("datePosted"),
        "employment_type": payload.get("employmentType"),
        "location": location_text,
        "direct_apply": payload.get("directApply"),
        "salary": salary_text,
        "valid_through": payload.get("validThrough"),
        "company": ((payload.get("hiringOrganization") or {}).get("name")) or "",
        "raw_source": simplify_url,
    }


def _tokenize_keywords(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", (text or "").lower())
        if len(token) > 2 and token not in ENGLISH_STOP_WORDS
    }


def _split_text_chunks(text: str, max_chunks: int = 18) -> list[str]:
    raw_parts = re.split(r"\n+|(?<=[.!?])\s+", text or "")
    chunks: list[str] = []

    for part in raw_parts:
        cleaned = re.sub(r"\s+", " ", part).strip(" -•\t")
        if len(cleaned) < 30:
            continue
        chunks.append(cleaned)
        if len(chunks) >= max_chunks:
            break

    return chunks


@lru_cache(maxsize=1)
def _load_sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(SEMANTIC_MATCH_MODEL, local_files_only=True)


def _compute_hybrid_match(resume_text: str, job_description: str) -> dict:
    model = _load_sentence_transformer()

    resume_keywords = _tokenize_keywords(resume_text)
    jd_keywords = _tokenize_keywords(job_description)
    shared_keywords = sorted(resume_keywords.intersection(jd_keywords))
    missing_keywords = sorted(jd_keywords.difference(resume_keywords))

    resume_chunks = _split_text_chunks(resume_text)
    job_chunks = _split_text_chunks(job_description)

    # Fall back to whole-document comparison if chunking produced little signal.
    resume_inputs = resume_chunks or [resume_text]
    job_inputs = job_chunks or [job_description]

    resume_embeddings = model.encode(resume_inputs, normalize_embeddings=True)
    job_embeddings = model.encode(job_inputs, normalize_embeddings=True)

    similarity_matrix = np.matmul(job_embeddings, resume_embeddings.T)
    best_scores = similarity_matrix.max(axis=1) if similarity_matrix.size else np.array([0.0])
    chunk_coverage = float(np.mean(best_scores >= 0.35)) if len(best_scores) else 0.0
    semantic_score = float(np.mean(best_scores)) if len(best_scores) else 0.0

    # Keep some lexical grounding so users still get actionable keyword feedback.
    lexical_overlap = (
        len(shared_keywords) / len(jd_keywords)
        if jd_keywords
        else 0.0
    )

    final_score = max(0.0, min(1.0, semantic_score * 0.7 + lexical_overlap * 0.3))

    top_matches = []
    if similarity_matrix.size:
        for job_idx in np.argsort(best_scores)[::-1][:3]:
            resume_idx = int(np.argmax(similarity_matrix[job_idx]))
            top_matches.append({
                "job_excerpt": job_inputs[int(job_idx)],
                "resume_excerpt": resume_inputs[resume_idx],
                "score": float(best_scores[int(job_idx)]),
            })

    return {
        "score": final_score,
        "semantic_score": semantic_score,
        "lexical_overlap": lexical_overlap,
        "coverage_score": chunk_coverage,
        "matched_keywords": shared_keywords[:30],
        "missing_keywords": missing_keywords[:30],
        "top_matches": top_matches,
        "method": "sentence-transformers-hybrid",
        "model": SEMANTIC_MATCH_MODEL,
    }


def _load_new_grad_jobs(force_refresh: bool = False) -> list[dict]:
    now = time.time()
    if (
        not force_refresh and
        _jobs_cache["jobs"] and
        now - _jobs_cache["fetched_at"] < JOBS_CACHE_TTL_SECONDS
    ):
        return _jobs_cache["jobs"]

    req = Request(
        SIMPLIFY_README_URL,
        headers={"User-Agent": "Career-Coach/1.0"},
    )
    with urlopen(req, timeout=15) as response:
        markdown = response.read().decode("utf-8")

    jobs = _parse_jobs_from_readme(markdown)
    _jobs_cache["jobs"] = jobs
    _jobs_cache["fetched_at"] = now
    return jobs


@bp.get("/jobs/new-grad")
@jwt_required()
def get_new_grad_jobs():
    try:
        limit = min(max(int(request.args.get("limit", 40)), 1), 100)
        category = (request.args.get("category") or "").strip().lower()
        search = (request.args.get("search") or "").strip().lower()
        force_refresh = (request.args.get("refresh") or "").strip().lower() == "true"

        jobs = _load_new_grad_jobs(force_refresh=force_refresh)

        if category and category != "all":
            jobs = [job for job in jobs if job["category"].lower() == category]

        if search:
            jobs = [
                job for job in jobs
                if search in job["company"].lower()
                or search in job["role"].lower()
                or search in job["location"].lower()
                or search in job["category"].lower()
            ]

        categories = sorted({job["category"] for job in _jobs_cache["jobs"]})

        return jsonify({
            "jobs": jobs[:limit],
            "total": len(jobs),
            "categories": categories,
            "source": "SimplifyJobs/New-Grad-Positions",
        }), 200
    except URLError as exc:
        return jsonify({
            "message": "Could not load live job listings right now.",
            "error": str(exc),
        }), 502
    except Exception as exc:
        return jsonify({
            "message": "Unexpected error while loading live job listings.",
            "error": str(exc),
        }), 500


@bp.get("/jobs/details")
@jwt_required()
def get_job_details():
    simplify_url = (request.args.get("simplify_url") or "").strip()
    if not simplify_url:
        return jsonify({"message": "simplify_url is required"}), 400

    try:
        details = _fetch_job_details(simplify_url)
        return jsonify(details), 200
    except URLError as exc:
        return jsonify({
            "message": "Could not load detailed job information right now.",
            "error": str(exc),
        }), 502
    except Exception as exc:
        return jsonify({
            "message": "Could not parse detailed job information from the source page.",
            "error": str(exc),
        }), 500


@bp.post("/match")
@jwt_required()
def match_keywords():
    try:
        # 1. Get the logged-in user's ID from the JWT token
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"message": "Authentication required."}), 401

        # Ensure it's an int (JWT identity may be a string)
        current_user_id = int(current_user_id)

        # 2. Get the job description from the frontend
        data = request.get_json()
        job_description = data.get("job_description")
        if not job_description:
            return jsonify({"message": "Job description is required."}), 400

        # 3. Get the user's most recent resume from the database
        db_conn = db.get_db()
        cursor = db_conn.cursor()

        cursor.execute(
            """
            SELECT id, parsed_json 
            FROM resumes 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (current_user_id,),
        )
        resume_row = cursor.fetchone()

        if not resume_row:
            return jsonify({"message": "No resume found. Please upload one first."}), 404

        # 4. Extract the full text from the parsed JSON
        try:
            # Load the JSON text blob from the database
            parsed_data = json.loads(resume_row["parsed_json"])

            # Find the full text from the 'sections' list
            resume_text = None
            if "sections" in parsed_data and isinstance(parsed_data["sections"], list):
                for section in parsed_data["sections"]:
                    if section.get("name") == "full_content":
                        resume_text = section.get("content")
                        break

            if not resume_text:
                return jsonify(
                    {
                        "message": "Resume parsed, but 'full_content' section not found. Please check your AIHelper."
                    }
                ), 500

        except json.JSONDecodeError:
            return jsonify(
                {"message": "Failed to read resume data from database. It may be corrupted."}
            ), 500
        except Exception as e:
            return jsonify({"message": f"Error parsing resume JSON: {str(e)}"}), 500

        # 5. Score the match using semantic embeddings first, with TF-IDF fallback.
        method = "sentence-transformers-hybrid"
        semantic_score = None
        lexical_overlap = None
        coverage_score = None
        top_matches = []
        model_name = None

        try:
            match_result = _compute_hybrid_match(resume_text, job_description)
            score = float(match_result["score"])
            semantic_score = float(match_result["semantic_score"])
            lexical_overlap = float(match_result["lexical_overlap"])
            coverage_score = float(match_result["coverage_score"])
            matched_keywords = match_result["matched_keywords"]
            missing_keywords = match_result["missing_keywords"]
            top_matches = match_result["top_matches"]
            model_name = match_result["model"]
        except Exception:
            corpus = [resume_text, job_description]
            vectorizer = TfidfVectorizer(stop_words="english", lowercase=True)
            tfidf_matrix = vectorizer.fit_transform(corpus)

            score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])

            feature_names = np.array(vectorizer.get_feature_names_out())
            resume_vec = tfidf_matrix[0].toarray().flatten()
            jd_vec = tfidf_matrix[1].toarray().flatten()
            resume_keywords = set(feature_names[resume_vec > 0.1])
            jd_keywords = set(feature_names[jd_vec > 0.1])
            matched_keywords = sorted(list(resume_keywords.intersection(jd_keywords)))
            missing_keywords = sorted(list(jd_keywords.difference(resume_keywords)))
            method = "tfidf-fallback"

        # ✅ Award progress points based on improved "resume score" (0..100)
        award_resume_score(current_user_id, int(score * 100))

        cursor.execute(
            """
            INSERT INTO keyword_analyses (resume_id, job_text, match_score, missing_keywords_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                int(resume_row["id"]),
                job_description,
                float(score),
                json.dumps(missing_keywords),
            ),
        )
        db_conn.commit()

        # 7. Return the results
        return jsonify(
            {
                "score": float(score),
                "semantic_score": semantic_score,
                "lexical_overlap": lexical_overlap,
                "coverage_score": coverage_score,
                "matched_keywords": matched_keywords,
                "missing_keywords": missing_keywords,
                "top_matches": top_matches,
                "method": method,
                "model": model_name,
            }
        ), 200

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500
