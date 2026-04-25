# backend/app/features/jwt_auth/api.py
import os
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from .service import (
    create_user,
    get_user_by_email,
    verify_pw,
)
from ... import db
from ...extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PW_LETTER = re.compile(r"[a-zA-Z]")
_PW_DIGIT  = re.compile(r"\d")


@bp.post("/register")
def register():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "invalid email format"}), 400

    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    if not _PW_LETTER.search(password) or not _PW_DIGIT.search(password):
        return jsonify({"error": "password must contain at least one letter and one number"}), 400

    if get_user_by_email(email):
        return jsonify({"error": "email already exists"}), 409

    create_user(email, password, name)
    return jsonify({"ok": True}), 201


@bp.post("/login")
@limiter.limit("5 per minute")
def login():
    """
    Verifies email/password and returns JWT access and refresh tokens.

    Response shape:
      { "accessToken": "<JWT string>", "refreshToken": "<JWT string>" }
    """
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_user_by_email(email)

    if not user or not verify_pw(password, user["password_hash"]):
        return jsonify({"error": "invalid credentials"}), 401

    user_id = str(user["id"])

    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    return jsonify(
        {
            "accessToken": access_token,
            "refreshToken": refresh_token,
        }
    ), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """
    Uses a valid refresh token to issue a new access token.
    """
    identity = str(get_jwt_identity())
    new_access_token = create_access_token(identity=identity)
    return jsonify({"accessToken": new_access_token}), 200


@bp.get("/me")
@jwt_required()
def me():
    return jsonify({"user_id": int(str(get_jwt_identity()))}), 200


@bp.get("/profile")
@jwt_required()
def profile():
    user_id = int(get_jwt_identity())
    conn = db.get_db()

    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    resume_count = conn.execute(
        "SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    interview_count = conn.execute(
        "SELECT COUNT(*) FROM interview_sessions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    return jsonify({
        "name": user["name"],
        "email": user["email"],
        "joined": user["created_at"],
        "resume_count": resume_count,
        "interview_count": interview_count,
    }), 200


@bp.put("/account")
@jwt_required()
def update_account():
    user_id = int(get_jwt_identity())
    data = request.get_json(force=True) or {}
    conn = db.get_db()

    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name and not email and not password:
        return jsonify({"error": "no fields provided to update"}), 400

    if email and not _EMAIL_RE.match(email):
        return jsonify({"error": "invalid email format"}), 400

    if email:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id)
        ).fetchone()
        if existing:
            return jsonify({"error": "email already in use"}), 409

    if password:
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400
        if not _PW_LETTER.search(password) or not _PW_DIGIT.search(password):
            return jsonify({"error": "password must contain at least one letter and one number"}), 400

    if name:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    if email:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    if password:
        from ...extensions import bcrypt as _bcrypt
        pw_hash = _bcrypt.generate_password_hash(password).decode("utf-8")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))

    conn.commit()
    return jsonify({"ok": True}), 200


@bp.delete("/account")
@jwt_required()
def delete_account():
    user_id = int(get_jwt_identity())
    conn = db.get_db()

    # Delete resume files from disk
    resumes = conn.execute(
        "SELECT id, file_path FROM resumes WHERE user_id = ?", (user_id,)
    ).fetchall()
    for resume in resumes:
        resume_id = resume["id"]
        conn.execute("DELETE FROM feedback_reports WHERE resume_id = ?", (resume_id,))
        conn.execute("DELETE FROM keyword_analyses WHERE resume_id = ?", (resume_id,))
        if resume["file_path"] and os.path.exists(resume["file_path"]):
            os.remove(resume["file_path"])
    conn.execute("DELETE FROM resumes WHERE user_id = ?", (user_id,))

    # Delete interview data
    sessions = conn.execute(
        "SELECT id FROM interview_sessions WHERE user_id = ?", (user_id,)
    ).fetchall()
    for session in sessions:
        conn.execute("DELETE FROM interview_answers WHERE session_id = ?", (session["id"],))
    conn.execute("DELETE FROM interview_sessions WHERE user_id = ?", (user_id,))

    # Delete progress and badges
    conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))

    # Delete the user
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

    return jsonify({"message": "Account deleted successfully"}), 200


@bp.get("/account/export")
@jwt_required()
def export_account():
    user_id = int(get_jwt_identity())
    conn = db.get_db()

    user = conn.execute(
        "SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    resumes = conn.execute(
        """
        SELECT r.id, r.file_path, r.created_at, fr.score, fr.summary
        FROM resumes r
        LEFT JOIN feedback_reports fr ON fr.resume_id = r.id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
        """,
        (user_id,),
    ).fetchall()

    sessions = conn.execute(
        "SELECT id, started_at FROM interview_sessions WHERE user_id = ?", (user_id,)
    ).fetchall()
    interview_data = []
    for session in sessions:
        answers = conn.execute(
            "SELECT answer_text, score FROM interview_answers WHERE session_id = ?",
            (session["id"],),
        ).fetchall()
        interview_data.append({
            "session_id": session["id"],
            "started_at": session["started_at"],
            "answers": [{"answer": a["answer_text"], "score": a["score"]} for a in answers],
        })

    progress = conn.execute(
        "SELECT points, best_resume_score, mock_interviews_completed FROM user_progress WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    badges = conn.execute(
        "SELECT badge_key, earned_at FROM user_badges WHERE user_id = ?", (user_id,)
    ).fetchall()

    return jsonify({
        "account": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "created_at": user["created_at"],
        },
        "resumes": [
            {
                "id": r["id"],
                "filename": r["file_path"],
                "uploaded_at": r["created_at"],
                "score": r["score"],
                "summary": r["summary"],
            }
            for r in resumes
        ],
        "interviews": interview_data,
        "progress": dict(progress) if progress else {},
        "badges": [{"badge": b["badge_key"], "earned_at": b["earned_at"]} for b in badges],
    }), 200
