# backend/app/main.py
import os
import sqlite3
import json 
from uuid import uuid4
from flask import Blueprint, request, jsonify, current_app, send_file, abort
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import db
from .services.ai_helper import AIHelper
from .features.progress.service import award_resume_score

bp = Blueprint("main", __name__)


def _current_user_id():
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return int(user_id)


def _resume_display_name(file_path: str) -> str:
    filename = os.path.basename(file_path or "")
    if "_" in filename:
        return filename.split("_", 1)[1]
    return filename


def _resume_text_from_parsed(parsed_resume: dict) -> str:
    sections = parsed_resume.get("sections") or []
    for section in sections:
        if section.get("name") == "full_content":
            return section.get("content") or ""
    return parsed_resume.get("raw_text") or ""


def _set_resume_text(parsed_resume: dict, new_text: str) -> dict:
    parsed_copy = dict(parsed_resume or {})
    sections = list(parsed_copy.get("sections") or [])
    found = False
    for section in sections:
        if section.get("name") == "full_content":
            section["content"] = new_text
            found = True
            break
    if not found:
        sections.append({"name": "full_content", "content": new_text})
    parsed_copy["sections"] = sections
    parsed_copy["raw_text"] = new_text[:500] + "..." if len(new_text) > 500 else new_text
    return parsed_copy


def _serialize_resume_row(row) -> dict:
    parsed_json = {}
    try:
        parsed_json = json.loads(row["parsed_json"] or "{}")
    except json.JSONDecodeError:
        parsed_json = {}
    return {
        "id": int(row["id"]),
        "filename": _resume_display_name(row["file_path"]),
        "uploadedAt": row["created_at"],
        "resumeText": _resume_text_from_parsed(parsed_json),
        "resumeScore": int(row["score"]) if row["score"] is not None else 0,
        "resumeSummary": row["summary"] or "",
        "fileUrl": f"/api/resume/{int(row['id'])}/view",
    }

# ----------------- Resume Upload -----------------
def _allowed_file(upload) -> bool:
    """Validate extension and MIME type using current app config."""
    filename = secure_filename(upload.filename or "")
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed_exts = current_app.config.get("ALLOWED_EXTS") or current_app.config.get("ALLOWED_EXTENSIONS", set())
    allowed_mimes = current_app.config.get("ALLOWED_MIMES") or current_app.config.get("ALLOWED_MIMETYPES", set())
    return ext in allowed_exts and (upload.mimetype in allowed_mimes)


@bp.post("/resume/upload")
@jwt_required()
def upload_resume():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file or file.filename.strip() == "":
        return jsonify({"error": "No selected file"}), 400

    if not _allowed_file(file):
        return jsonify({"error": "Invalid file type. Only PDF or DOCX files are allowed."}), 415

    # Reject empty files (0 bytes)
    file.seek(0, 2)  # seek to end
    size = file.tell()
    file.seek(0)
    if size == 0:
        return jsonify({"error": "File is empty. Please select a non-empty PDF or DOCX file."}), 400

    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    if size > max_size:
        return jsonify({
            "error": f"File too large. Maximum size is {max_size // (1024 * 1024)} MB."
        }), 413

    original_name = secure_filename(file.filename)
    rid = str(uuid4())
    saved_name = f"{rid}_{original_name}"

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, saved_name)
    
    # 1. Save the file to disk
    file.save(filepath)

    # 2. Parse the resume content
    ai_helper = AIHelper()
    parsed_resume_data = ai_helper.parseResume(filepath)
    
    # Check if parsing failed before continuing
    if "error" in parsed_resume_data:
        os.remove(filepath)
        return jsonify({"error": f"Parsing failed: {parsed_resume_data['error']}"}), 500

    # 3. Store the record in the database
    db_conn = db.get_db()
    cursor = db_conn.cursor()
    try:
        resume_evaluation = ai_helper.scoreResume(parsed_resume_data)
        cursor.execute(
            """
            INSERT INTO resumes (user_id, file_path, parsed_json)
            VALUES (?, ?, ?)
            """,
            (user_id, filepath, json.dumps(parsed_resume_data)),
        )
        resume_db_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO feedback_reports (resume_id, score, summary, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                resume_db_id,
                int(resume_evaluation["score"]),
                resume_evaluation["summary"],
                json.dumps(resume_evaluation["details"]),
            ),
        )
        db_conn.commit()
        award_resume_score(int(user_id), int(resume_evaluation["score"]))
    except Exception as e:
        # If DB save fails, log the error and remove the saved file
        current_app.logger.error(f"Failed to save resume record to DB: {e}")
        os.remove(filepath)
        return jsonify({"error": "Database error during resume upload."}), 500
    finally:
        db.close_db()

    # 4. Return success response
    return jsonify({
        "message": "Resume uploaded and parsed successfully",
        "resume_db_id": resume_db_id,
        "filename": original_name,
        "size": os.path.getsize(filepath),
        "parsed_data": parsed_resume_data,
        "resume_score": int(resume_evaluation["score"]),
        "resume_summary": resume_evaluation["summary"],
    }), 200



@bp.get("/resume")
@jwt_required()
def list_resumes():
    user_id = _current_user_id()
    conn = db.get_db()
    rows = conn.execute(
        """
        SELECT r.id, r.file_path, r.parsed_json, r.created_at, fr.score, fr.summary
        FROM resumes r
        LEFT JOIN feedback_reports fr
          ON fr.id = (
            SELECT id
            FROM feedback_reports
            WHERE resume_id = r.id
            ORDER BY created_at DESC
            LIMIT 1
          )
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC, r.id DESC
        """,
        (user_id,),
    ).fetchall()
    return jsonify({"resumes": [_serialize_resume_row(row) for row in rows]}), 200


@bp.get("/resume/<int:resume_id>")
@jwt_required()
def get_resume(resume_id: int):
    user_id = _current_user_id()
    conn = db.get_db()
    row = conn.execute(
        """
        SELECT r.id, r.file_path, r.parsed_json, r.created_at, fr.score, fr.summary
        FROM resumes r
        LEFT JOIN feedback_reports fr
          ON fr.id = (
            SELECT id
            FROM feedback_reports
            WHERE resume_id = r.id
            ORDER BY created_at DESC
            LIMIT 1
          )
        WHERE r.id = ? AND r.user_id = ?
        """,
        (resume_id, user_id),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Resume not found"}), 404
    return jsonify(_serialize_resume_row(row)), 200


@bp.put("/resume/<int:resume_id>")
@jwt_required()
def update_resume(resume_id: int):
    user_id = _current_user_id()
    payload = request.get_json(force=True) or {}
    resume_text = (payload.get("resumeText") or "").strip()
    if not resume_text:
        return jsonify({"error": "resumeText is required"}), 400

    conn = db.get_db()
    row = conn.execute(
        "SELECT parsed_json FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, user_id),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Resume not found"}), 404

    try:
        parsed_json = json.loads(row["parsed_json"] or "{}")
    except json.JSONDecodeError:
        parsed_json = {}

    ai_helper = AIHelper()
    updated_parsed = _set_resume_text(parsed_json, resume_text)
    resume_evaluation = ai_helper.scoreResume(updated_parsed)

    conn.execute(
        "UPDATE resumes SET parsed_json = ? WHERE id = ? AND user_id = ?",
        (json.dumps(updated_parsed), resume_id, user_id),
    )
    conn.execute(
        """
        INSERT INTO feedback_reports (resume_id, score, summary, details_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            resume_id,
            int(resume_evaluation["score"]),
            resume_evaluation["summary"],
            json.dumps(resume_evaluation["details"]),
        ),
    )
    conn.commit()
    award_resume_score(user_id, int(resume_evaluation["score"]))

    refreshed = conn.execute(
        """
        SELECT r.id, r.file_path, r.parsed_json, r.created_at, fr.score, fr.summary
        FROM resumes r
        LEFT JOIN feedback_reports fr
          ON fr.id = (
            SELECT id
            FROM feedback_reports
            WHERE resume_id = r.id
            ORDER BY created_at DESC
            LIMIT 1
          )
        WHERE r.id = ? AND r.user_id = ?
        """,
        (resume_id, user_id),
    ).fetchone()
    return jsonify(_serialize_resume_row(refreshed)), 200


@bp.get("/resume/<int:resume_id>/view")
@jwt_required()
def resume_view(resume_id: int):
    user_id = _current_user_id()
    row = db.get_db().execute(
        "SELECT file_path FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, user_id),
    ).fetchone()
    if row is None:
        abort(404)
    return send_file(row["file_path"])


@bp.delete("/resume/<int:resume_id>")
@jwt_required()
def resume_delete(resume_id: int):
    user_id = _current_user_id()
    conn = db.get_db()
    row = conn.execute(
        "SELECT file_path FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, user_id),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Resume not found"}), 404

    conn.execute("DELETE FROM feedback_reports WHERE resume_id = ?", (resume_id,))
    conn.execute("DELETE FROM keyword_analyses WHERE resume_id = ?", (resume_id,))
    conn.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id))
    conn.commit()

    if row["file_path"] and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])

    return jsonify({"message": f"Deleted {_resume_display_name(row['file_path'])}"}), 200
