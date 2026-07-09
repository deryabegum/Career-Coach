# backend/app/services/keyword_match.py
"""Shared resume/job-description matching helpers.

Used by the keywords feature (manual job description paste) and the
career_agent feature (automated gap analysis step) so both stay in sync.
"""

import re
from functools import lru_cache

SEMANTIC_MATCH_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ENGLISH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "he", "in", "is", "it", "its", "of", "on", "that", "the", "to", "was",
    "were", "will", "with", "or", "this", "these", "those", "your", "you",
    "our", "we", "they", "their", "them", "i", "me", "my", "mine", "but",
    "if", "then", "than", "into", "over", "under", "after", "before", "up",
    "down", "out", "about", "not", "no", "so", "too", "very", "can"
}


def tokenize_keywords(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", (text or "").lower())
        if len(token) > 2 and token not in ENGLISH_STOP_WORDS
    }


def split_text_chunks(text: str, max_chunks: int = 18) -> list[str]:
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


def compute_hybrid_match(resume_text: str, job_description: str) -> dict:
    model = _load_sentence_transformer()

    resume_keywords = tokenize_keywords(resume_text)
    jd_keywords = tokenize_keywords(job_description)
    shared_keywords = sorted(resume_keywords.intersection(jd_keywords))
    missing_keywords = sorted(jd_keywords.difference(resume_keywords))

    resume_chunks = split_text_chunks(resume_text)
    job_chunks = split_text_chunks(job_description)

    # Fall back to whole-document comparison if chunking produced little signal.
    resume_inputs = resume_chunks or [resume_text]
    job_inputs = job_chunks or [job_description]

    resume_embeddings = model.encode(resume_inputs, normalize_embeddings=True).tolist()
    job_embeddings = model.encode(job_inputs, normalize_embeddings=True).tolist()

    similarity_matrix = []
    for job_vector in job_embeddings:
        row = []
        for resume_vector in resume_embeddings:
            row.append(sum(a * b for a, b in zip(job_vector, resume_vector)))
        similarity_matrix.append(row)

    best_scores = [max(row) for row in similarity_matrix] if similarity_matrix else [0.0]
    chunk_coverage = (
        sum(1 for score in best_scores if score >= 0.35) / len(best_scores)
        if best_scores else 0.0
    )
    semantic_score = sum(best_scores) / len(best_scores) if best_scores else 0.0

    # Keep some lexical grounding so users still get actionable keyword feedback.
    lexical_overlap = (
        len(shared_keywords) / len(jd_keywords)
        if jd_keywords
        else 0.0
    )

    final_score = max(0.0, min(1.0, semantic_score * 0.7 + lexical_overlap * 0.3))

    top_matches = []
    if similarity_matrix:
        ranked_job_indices = sorted(
            range(len(best_scores)),
            key=lambda idx: best_scores[idx],
            reverse=True,
        )[:3]
        for job_idx in ranked_job_indices:
            resume_idx = max(
                range(len(similarity_matrix[job_idx])),
                key=lambda idx: similarity_matrix[job_idx][idx],
            )
            top_matches.append({
                "job_excerpt": job_inputs[job_idx],
                "resume_excerpt": resume_inputs[resume_idx],
                "score": float(best_scores[job_idx]),
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


def compute_lightweight_match(resume_text: str, job_description: str) -> dict:
    resume_keywords = tokenize_keywords(resume_text)
    jd_keywords = tokenize_keywords(job_description)
    shared_keywords = sorted(resume_keywords.intersection(jd_keywords))
    missing_keywords = sorted(jd_keywords.difference(resume_keywords))

    lexical_overlap = (
        len(shared_keywords) / len(jd_keywords)
        if jd_keywords else 0.0
    )

    resume_chunks = split_text_chunks(resume_text, max_chunks=12) or [resume_text]
    job_chunks = split_text_chunks(job_description, max_chunks=12) or [job_description]

    chunk_scores = []
    top_matches = []
    for job_chunk in job_chunks:
        job_chunk_tokens = tokenize_keywords(job_chunk)
        best_score = 0.0
        best_resume_chunk = resume_chunks[0] if resume_chunks else ""

        for resume_chunk in resume_chunks:
            resume_chunk_tokens = tokenize_keywords(resume_chunk)
            if not job_chunk_tokens:
                score = 0.0
            else:
                score = len(job_chunk_tokens.intersection(resume_chunk_tokens)) / len(job_chunk_tokens)

            if score > best_score:
                best_score = score
                best_resume_chunk = resume_chunk

        chunk_scores.append(best_score)
        top_matches.append({
            "job_excerpt": job_chunk,
            "resume_excerpt": best_resume_chunk,
            "score": round(best_score, 4),
        })

    coverage_score = (
        sum(1 for score in chunk_scores if score >= 0.35) / len(chunk_scores)
        if chunk_scores else 0.0
    )
    semantic_score = sum(chunk_scores) / len(chunk_scores) if chunk_scores else lexical_overlap
    final_score = max(0.0, min(1.0, semantic_score * 0.7 + lexical_overlap * 0.3))

    top_matches = sorted(top_matches, key=lambda item: item["score"], reverse=True)[:3]

    return {
        "score": round(final_score, 4),
        "semantic_score": round(semantic_score, 4),
        "lexical_overlap": round(lexical_overlap, 4),
        "coverage_score": round(coverage_score, 4),
        "matched_keywords": shared_keywords[:30],
        "missing_keywords": missing_keywords[:30],
        "top_matches": top_matches,
        "method": "lightweight-keyword-match",
        "model": None,
    }
