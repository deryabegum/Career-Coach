from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.common.wire import get_db_conn
from backend.app.features.mock_interview.service import MockInterviewDAO, create_session, submit_answers
from backend.app.services.ai_helper import AIHelper
import json

bp = Blueprint("mock_interview", __name__, url_prefix="/api/v1/mock-interview")

def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    return int(uid)


def _evaluate_answer_payload(conn, data: dict):
    session_id = data.get("session_id")
    qid = data.get("qid") or "adhoc"
    question_prompt = data.get("question_prompt")
    # Accept transcript-first payload, then fallback to answer_text for compatibility.
    transcript = (data.get("transcript") or data.get("answer_text") or "").strip()
    role = data.get("role", "")
    company = data.get("company", "")

    if not transcript:
        return jsonify({"error": "Transcript is required"}), 400

    if not question_prompt:
        return jsonify({"error": "Question prompt is required"}), 400

    ai_helper = AIHelper()
    feedback = ai_helper.generateInterviewFeedback(
        question_prompt,
        transcript,
        role,
        company
    )

    try:
        score = ai_helper.scoreInterviewAnswer(question_prompt, transcript)
        if isinstance(feedback, dict):
            feedback["score"] = round(float(score), 2)
    except Exception:
        pass

    if session_id:
        try:
            dao = MockInterviewDAO(conn)
            dao.save_answer(session_id, qid, question_prompt, transcript, feedback)
        except Exception:
            pass

    return jsonify(feedback), 200

@bp.post("/sessions")
@jwt_required()
def create_interview_session():
    """Create a new interview session"""
    try:
        data = request.get_json() or {}
        role = data.get("role", "Software / Data / Intern")
        company = data.get("company", "Company")
        
        user_id = _current_user_id()
        conn = get_db_conn()
        
        try:
            session_id = create_session(conn, user_id, role, company)
            return jsonify({
                "session_id": session_id,
                "role": role,
                "company": company,
                "message": "Session created successfully"
            }), 201
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
        _current_user_id()
        conn = get_db_conn()

        try:
            data = request.get_json() or {}
            return _evaluate_answer_payload(conn, data)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/evaluate")
@jwt_required()
def evaluate_transcript():
    """Evaluate transcript text for a single interview answer."""
    try:
        _current_user_id()
        conn = get_db_conn()

        try:
            data = request.get_json() or {}
            return _evaluate_answer_payload(conn, data)
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
            return jsonify(result), 200
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
    """Get all interview sessions for the current user"""
    try:
        user_id = _current_user_id()
        conn = get_db_conn()
        
        try:
            dao = MockInterviewDAO(conn)
            sessions = dao.get_user_sessions(user_id)
            return jsonify({"sessions": sessions}), 200
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500
