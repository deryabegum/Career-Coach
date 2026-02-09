# backend/app/features/mock_interview/service.py

from datetime import datetime, timezone
import json
from backend.app.services.ai_helper import AIHelper

class MockInterviewDAO:
    def __init__(self, conn):
        self.conn = conn

    def create_interview(self, user_id: int, role: str, company: str) -> int:
        """Create a new interview record and return its ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO interviews (role, company, created_at)
            VALUES (?, ?, ?)
            """,
            (role, company, datetime.now(timezone.utc).isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid

    def save_answer(self, interview_id: int, qid: str, prompt: str, answer: str, feedback_json: dict = None):
        """Save an answer to the answers table"""
        feedback_str = json.dumps(feedback_json) if feedback_json else None
        existing = self.conn.execute(
            """
            SELECT id FROM answers
            WHERE interview_id = ? AND qid = ?
            LIMIT 1
            """,
            (interview_id, qid),
        ).fetchone()

        if existing:
            self.conn.execute(
                """
                UPDATE answers
                SET prompt = ?, answer = ?, feedback_json = ?
                WHERE id = ?
                """,
                (prompt, answer, feedback_str, existing["id"]),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO answers (interview_id, qid, prompt, answer, feedback_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (interview_id, qid, prompt, answer, feedback_str)
            )
        self.conn.commit()

    def get_interview(self, interview_id: int, user_id: int = None):
        """Get interview by ID (optionally check user ownership)"""
        if user_id:
            # Note: interviews table doesn't have user_id, so we can't filter by user
            # For now, we'll just get by ID
            row = self.conn.execute(
                "SELECT * FROM interviews WHERE id = ?",
                (interview_id,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM interviews WHERE id = ?",
                (interview_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_interview_answers(self, interview_id: int):
        """Get all answers for an interview"""
        rows = self.conn.execute(
            "SELECT * FROM answers WHERE interview_id = ?",
            (interview_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_user_sessions(self, user_id: int):
        """Get all interview sessions for a user"""
        # Note: interviews table doesn't have user_id
        # For now, return all interviews (this is a limitation of current schema)
        # In production, you'd want to add user_id to interviews table
        rows = self.conn.execute(
            "SELECT * FROM interviews ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return [dict(row) for row in rows]


def create_session(conn, user_id: int, role: str, company: str) -> int:
    """Create a new interview session and return session_id"""
    dao = MockInterviewDAO(conn)
    interview_id = dao.create_interview(user_id, role, company)
    return interview_id


def get_feedback_for_answer(conn, question: str, answer: str, role: str, company: str) -> dict:
    """Get AI feedback for a single answer"""
    ai_helper = AIHelper()
    return ai_helper.generateInterviewFeedback(question, answer, role, company)


def submit_answers(conn, session_id: int, user_id: int, answers: dict, role: str, company: str) -> dict:
    """
    Submit all answers for an interview session.
    Returns summary with scores and feedback.
    """
    dao = MockInterviewDAO(conn)
    ai_helper = AIHelper()
    
    # Verify interview exists
    interview = dao.get_interview(session_id)
    if not interview:
        raise ValueError(f"Interview session {session_id} not found")
    
    all_feedback = {}
    all_scores = []
    
    # Process each answer
    for qid, answer_data in answers.items():
        # Support both formats: {qid: "answer"} or {qid: {answer: "...", prompt: "..."}}
        if isinstance(answer_data, dict):
            answer_text = answer_data.get("answer", "")
            question_prompt = answer_data.get("prompt", f"Question {qid}")
        else:
            answer_text = answer_data
            question_prompt = f"Question {qid}"
        
        if not answer_text or not answer_text.strip():
            continue
        
        # Generate feedback
        feedback = ai_helper.generateInterviewFeedback(question_prompt, answer_text, role, company)
        
        # Calculate score (0-100)
        score = ai_helper.scoreInterviewAnswer(question_prompt, answer_text)
        if isinstance(feedback, dict):
            feedback["score"] = round(float(score), 2)
        
        all_feedback[qid] = feedback
        all_scores.append(score)
        
        # Save answer to database
        dao.save_answer(session_id, qid, question_prompt, answer_text, feedback)
    
    # Calculate averages
    average_score = sum(all_scores) / len(all_scores) if all_scores else 0
    total_score = sum(all_scores)
    
    return {
        "session_id": session_id,
        "total_score": round(total_score, 2),
        "average_score": round(average_score, 2),
        "questions_answered": len(answers),
        "feedback": all_feedback,
        "message": "Interview submitted successfully"
    }
