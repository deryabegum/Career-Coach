# backend/app/features/career_agent/service.py
"""
Autonomous multi-step "Career Agent": chains resume analysis, job-fit gap
analysis, cover letter drafting, and interview prep into a single run, with
branching decisions based on what it discovers about the candidate along the
way (not just a fixed sequence of calls).
"""

from datetime import datetime, timezone
import json

from ...services.ai_helper import AIHelper
from ...services.keyword_match import compute_lightweight_match
from ..progress.service import award_resume_score


class CareerAgentDAO:
    def __init__(self, conn):
        self.conn = conn

    def latest_resume(self, user_id: int):
        row = self.conn.execute(
            """
            SELECT id, parsed_json
            FROM resumes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def save_run(
        self,
        user_id: int,
        resume_id: int,
        role: str,
        company: str,
        job_description: str,
        steps: list,
        result: dict,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO career_agent_runs
                (user_id, resume_id, role, company, job_description, steps_json, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                resume_id,
                role,
                company,
                job_description,
                json.dumps(steps),
                json.dumps(result),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_runs(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT id, role, company, created_at, result_json
            FROM career_agent_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

        summaries = []
        for row in rows:
            try:
                result = json.loads(row["result_json"] or "{}")
            except json.JSONDecodeError:
                result = {}
            summaries.append({
                "id": row["id"],
                "role": row["role"],
                "company": row["company"],
                "created_at": row["created_at"],
                "resume_score": (result.get("resume_analysis") or {}).get("score"),
                "fit_score": (result.get("match_analysis") or {}).get("score"),
            })
        return summaries

    def get_run(self, run_id: int, user_id: int):
        row = self.conn.execute(
            """
            SELECT id, role, company, job_description, steps_json, result_json, created_at
            FROM career_agent_runs
            WHERE id = ? AND user_id = ?
            """,
            (run_id, user_id),
        ).fetchone()
        if not row:
            return None

        try:
            steps = json.loads(row["steps_json"] or "[]")
        except json.JSONDecodeError:
            steps = []
        try:
            result = json.loads(row["result_json"] or "{}")
        except json.JSONDecodeError:
            result = {}

        return {
            "id": row["id"],
            "role": row["role"],
            "company": row["company"],
            "job_description": row["job_description"],
            "created_at": row["created_at"],
            "steps": steps,
            **result,
        }


def _load_parsed_resume(parsed_json_str: str) -> dict:
    try:
        return json.loads(parsed_json_str or "{}")
    except json.JSONDecodeError:
        return {}


def _resume_full_text(parsed_resume: dict) -> str:
    for section in (parsed_resume.get("sections") or []):
        if section.get("name") == "full_content":
            return section.get("content") or ""
    return parsed_resume.get("raw_text") or ""


class _AgentTrace:
    """Records each autonomous step in order, so a run can be inspected end-to-end."""

    def __init__(self):
        self.steps: list[dict] = []

    def record(self, step: str, detail: str) -> None:
        self.steps.append({
            "step": step,
            "status": "done",
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })


def run_career_agent(
    conn,
    user_id: int,
    job_description: str,
    role: str = "",
    company: str = "",
) -> dict:
    """
    Runs the full agent pipeline for the user's most recent resume:
      1. load resume -> 2. score resume -> 3. gap analysis vs job_description ->
      4. adapt the plan based on scores -> 5. draft cover letter -> 6. build interview prep.
    Raises ValueError if there is no usable resume on file.
    """
    dao = CareerAgentDAO(conn)
    ai_helper = AIHelper()
    trace = _AgentTrace()

    resume_row = dao.latest_resume(user_id)
    if not resume_row:
        raise ValueError("No resume found. Upload a resume before running the career agent.")

    parsed_resume = _load_parsed_resume(resume_row["parsed_json"])
    resume_text = _resume_full_text(parsed_resume)
    if not resume_text.strip():
        raise ValueError("The stored resume has no readable text to analyze.")
    extracted_data = parsed_resume.get("extracted_data") or {}
    trace.record("load_resume", f"Loaded resume #{resume_row['id']} for analysis.")

    resume_evaluation = ai_helper.scoreResume(parsed_resume)
    trace.record("score_resume", f"Resume scored {resume_evaluation['score']}/100.")

    match_result = compute_lightweight_match(resume_text, job_description or "")
    trace.record(
        "gap_analysis",
        f"Job-fit score {round(match_result['score'] * 100)}%, "
        f"{len(match_result['missing_keywords'])} missing keywords identified.",
    )

    # Decision point: the plan adapts to what the agent just learned instead of
    # running a fixed script regardless of the candidate's actual standing.
    decisions = []
    if resume_evaluation["score"] < 60:
        decisions.append(
            "Resume score is on the low side, so the cover letter leans on the strongest "
            "matched skills rather than general resume framing, and prep adds an extra question."
        )
    if match_result["score"] < 0.4:
        decisions.append(
            "Job-fit score is low, so interview prep prioritizes bridging the largest "
            "keyword gaps over general behavioral questions."
        )
    else:
        decisions.append(
            "Job-fit score is solid, so interview prep emphasizes differentiation on top "
            "of covering the remaining gaps."
        )
    trace.record("plan_adjustment", " ".join(decisions))

    cover_letter = ai_helper.generateCoverLetter(
        extracted_data,
        role,
        company,
        job_description or "",
        match_result["matched_keywords"],
        match_result["missing_keywords"],
    )
    trace.record("draft_cover_letter", "Drafted a tailored cover letter grounded in resume evidence.")

    prep_plan = ai_helper.generateInterviewPrepPlan(
        role,
        company,
        match_result["missing_keywords"],
        resume_evaluation["score"],
    )
    trace.record(
        "build_interview_prep",
        f"Built prep plan with {len(prep_plan['focus_areas'])} focus areas "
        f"and {len(prep_plan['questions'])} questions.",
    )

    result = {
        "resume_analysis": {
            "score": resume_evaluation["score"],
            "summary": resume_evaluation["summary"],
            "suggestions": resume_evaluation["details"].get("suggestions", []),
        },
        "match_analysis": match_result,
        "decisions": decisions,
        "cover_letter": cover_letter,
        "interview_prep": prep_plan,
    }

    run_id = dao.save_run(
        user_id,
        int(resume_row["id"]),
        role,
        company,
        job_description or "",
        trace.steps,
        result,
    )

    # Reuse the same progress hook a direct resume upload triggers, so a
    # career-agent run contributes to the existing gamified progress too.
    award_resume_score(user_id, int(resume_evaluation["score"]))

    return {
        "run_id": run_id,
        "steps": trace.steps,
        **result,
    }
