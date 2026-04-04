from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.app.common.wire import get_db_conn
from backend.app.features.mock_interview.service import (
    MockInterviewDAO,
    build_question_set,
    create_session,
    submit_answers,
    get_session_detail,
)
from backend.app.services.ai_helper import AIHelper

# ✅ Progress tracking (award points)
from backend.app.features.progress.service import award_mock_interview_completed

bp = Blueprint("mock_interview", __name__, url_prefix="/api/v1/mock-interview")


def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    return int(uid)


@bp.post("/sessions")
@jwt_required()
def create_interview_session():
    """Create a new interview session"""
    try:
        data = request.get_json() or {}
        role = data.get("role", "Software / Data / Intern")
        company = data.get("company", "Company")
        question_count = int(data.get("question_count", 5) or 5)

        user_id = _current_user_id()
        conn = get_db_conn()

        try:
            questions = build_question_set(role, company, question_count)
            session_id = create_session(conn, user_id, role, company, questions)
            return jsonify(
                {
                    "session_id": session_id,
                    "role": role,
                    "company": company,
                    "questions": questions,
                    "message": "Session created successfully",
                }
            ), 201
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/feedback")
@jwt_required()
def get_feedback():
    """Get AI feedback for a single answer"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        question_prompt = data.get("question_prompt")
        answer_text = data.get("answer_text", "").strip()
        role = data.get("role", "")
        company = data.get("company", "")

        if not answer_text:
            return jsonify({"error": "Answer text is required"}), 400

        if not question_prompt:
            return jsonify({"error": "Question prompt is required"}), 400

        user_id = _current_user_id()
        conn = get_db_conn()

        try:
            ai_helper = AIHelper()
            feedback = ai_helper.generateInterviewFeedback(
                question_prompt,
                answer_text,
                role,
                company,
            )

            return jsonify(feedback), 200
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/submit")
@jwt_required()
def submit_interview():
    """Submit complete interview with all answers"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        answers = data.get("answers", {})  # {qid: answer_text}
        role = data.get("role", "")
        company = data.get("company", "")

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        if not answers:
            return jsonify({"error": "answers are required"}), 400

        user_id = _current_user_id()
        conn = get_db_conn()

        try:
            result = submit_answers(conn, session_id, user_id, answers, role, company)

            # ✅ Award +20 points for completing a mock interview (only if submit succeeded)
            award_mock_interview_completed(user_id)

            return jsonify(result), 200
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/sessions/<int:session_id>")
@jwt_required()
def get_interview_session(session_id: int):
    """Return one session with Q&A and stored evaluation for the current user."""
    try:
        user_id = _current_user_id()
        conn = get_db_conn()
        try:
            detail = get_session_detail(conn, session_id, user_id)
            if detail is None:
                return jsonify({"error": "Session not found"}), 404
            return jsonify(detail), 200
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/sessions")
@jwt_required()
def get_user_sessions():
    """List interview sessions for the current user (metadata + answer counts)."""
    try:
        user_id = _current_user_id()
        conn = get_db_conn()

        try:
            dao = MockInterviewDAO(conn)
            sessions = dao.list_user_sessions_summary(user_id)
            return jsonify({"sessions": sessions}), 200
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500
