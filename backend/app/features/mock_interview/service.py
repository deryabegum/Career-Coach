# backend/app/features/mock_interview/service.py

from datetime import datetime, timezone
import json
from backend.app.services.ai_helper import AIHelper


class MockInterviewDAO:
    def __init__(self, conn):
        self.conn = conn

    def create_interview(
        self,
        user_id: int,
        role: str,
        company: str,
        questions_json: str | None = None,
    ) -> int:
        """Create a new interview record and return its ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO interviews (user_id, role, company, created_at, questions_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                role,
                company,
                datetime.now(timezone.utc).isoformat(),
                questions_json,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def save_answer(
        self,
        interview_id: int,
        qid: str,
        prompt: str,
        answer: str,
        feedback_json: dict = None,
    ):
        """Save an answer to the answers table"""
        feedback_str = json.dumps(feedback_json) if feedback_json else None
        self.conn.execute(
            """
            INSERT INTO answers (interview_id, qid, prompt, answer, feedback_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (interview_id, qid, prompt, answer, feedback_str),
        )
        self.conn.commit()

    def delete_answers_for_interview(self, interview_id: int):
        self.conn.execute("DELETE FROM answers WHERE interview_id = ?", (interview_id,))
        self.conn.commit()

    def update_interview_summary(
        self,
        interview_id: int,
        submitted_at: str,
        average_score: float,
        total_score: float,
    ):
        self.conn.execute(
            """
            UPDATE interviews
            SET submitted_at = ?, average_score = ?, total_score = ?
            WHERE id = ?
            """,
            (submitted_at, average_score, total_score, interview_id),
        )
        self.conn.commit()

    def get_interview(self, interview_id: int):
        row = self.conn.execute(
            "SELECT * FROM interviews WHERE id = ?",
            (interview_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_interview_answers(self, interview_id: int):
        rows = self.conn.execute(
            "SELECT * FROM answers WHERE interview_id = ? ORDER BY id ASC",
            (interview_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_user_sessions_summary(self, user_id: int, limit: int = 50):
        rows = self.conn.execute(
            """
            SELECT
              i.id,
              i.role,
              i.company,
              i.created_at,
              i.submitted_at,
              i.average_score,
              i.total_score,
              (SELECT COUNT(*) FROM answers a WHERE a.interview_id = i.id) AS answer_count
            FROM interviews i
            WHERE i.user_id = ?
            ORDER BY i.created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def create_session(
    conn,
    user_id: int,
    role: str,
    company: str,
    questions: list | None = None,
) -> int:
    """Create a new interview session and return session_id"""
    dao = MockInterviewDAO(conn)
    qj = json.dumps(questions) if questions else None
    return dao.create_interview(user_id, role, company, qj)


def build_question_set(role: str, company: str, count: int = 5) -> list[dict]:
    """Generate a fresh question set for a session."""
    ai_helper = AIHelper()
    return ai_helper.generateInterviewQuestions(role, company, count)


def get_feedback_for_answer(
    conn, question: str, answer: str, role: str, company: str
) -> dict:
    """Get AI feedback for a single answer"""
    ai_helper = AIHelper()
    return ai_helper.generateInterviewFeedback(question, answer, role, company)


def submit_answers(
    conn, session_id: int, user_id: int, answers: dict, role: str, company: str
) -> dict:
    """
    Submit all answers for an interview session.
    Returns summary with scores and feedback.
    """
    dao = MockInterviewDAO(conn)
    ai_helper = AIHelper()

    interview = dao.get_interview(session_id)
    if not interview:
        raise ValueError(f"Interview session {session_id} not found")

    owner_id = interview.get("user_id")
    if owner_id is not None and int(owner_id) != int(user_id):
        raise PermissionError("You cannot submit answers for this session")

    all_feedback = {}
    all_scores = []

    dao.delete_answers_for_interview(session_id)

    for qid, answer_data in answers.items():
        if isinstance(answer_data, dict):
            answer_text = answer_data.get("answer", "")
            question_prompt = answer_data.get("prompt", f"Question {qid}")
        else:
            answer_text = answer_data
            question_prompt = f"Question {qid}"

        if not answer_text or not answer_text.strip():
            continue

        feedback = ai_helper.generateInterviewFeedback(
            question_prompt, answer_text, role, company
        )
        score = float(feedback.get("overall_score", 0))

        all_feedback[qid] = feedback
        all_scores.append(score)

        dao.save_answer(session_id, qid, question_prompt, answer_text, feedback)

    average_score = sum(all_scores) / len(all_scores) if all_scores else 0
    total_score = sum(all_scores)

    now = datetime.now(timezone.utc).isoformat()
    dao.update_interview_summary(
        session_id,
        now,
        round(average_score, 2),
        round(total_score, 2),
    )

    return {
        "session_id": session_id,
        "total_score": round(total_score, 2),
        "average_score": round(average_score, 2),
        "questions_answered": len(answers),
        "feedback": all_feedback,
        "message": "Interview submitted successfully",
    }


def get_session_detail(conn, session_id: int, user_id: int) -> dict | None:
    """Load one session with Q&A and stored feedback for the given user."""
    dao = MockInterviewDAO(conn)
    row = dao.get_interview(session_id)
    if not row:
        return None
    owner_id = row.get("user_id")
    if owner_id is not None and int(owner_id) != int(user_id):
        return None

    answer_rows = dao.get_interview_answers(session_id)
    items = []
    for ar in answer_rows:
        fb = {}
        raw_fb = ar.get("feedback_json")
        if raw_fb:
            try:
                fb = json.loads(raw_fb) if isinstance(raw_fb, str) else raw_fb
            except Exception:
                fb = {}
        items.append(
            {
                "qid": ar["qid"],
                "prompt": ar["prompt"],
                "answer": ar["answer"],
                "feedback": fb,
            }
        )

    questions_snapshot = None
    qj = row.get("questions_json")
    if qj:
        try:
            questions_snapshot = json.loads(qj) if isinstance(qj, str) else qj
        except Exception:
            questions_snapshot = None

    return {
        "id": row["id"],
        "role": row["role"],
        "company": row["company"],
        "created_at": row["created_at"],
        "submitted_at": row.get("submitted_at"),
        "average_score": row.get("average_score"),
        "total_score": row.get("total_score"),
        "questions_snapshot": questions_snapshot,
        "items": items,
    }
