# backend/app/main.py
import os
import sqlite3
import json 
from uuid import uuid4
from flask import Blueprint, request, jsonify, session, current_app, send_file, abort
from werkzeug.utils import secure_filename
# 1. ADD these imports for JWT
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import db
from .services.ai_helper import AIHelper
import docx

bp = Blueprint("main", __name__)

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

def _latest_resume_row(user_id: int):
    db_conn = db.get_db()
    return db_conn.execute(
        """
        SELECT id, file_path, parsed_json, created_at
        FROM resumes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

def _save_text_as_docx(text: str, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    rid = str(uuid4())
    filename = f"{rid}_edited_resume.docx"
    filepath = os.path.join(upload_dir, filename)
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(filepath)
    return filepath

# --- THIS IS THE UPDATED FUNCTION ---
@bp.post("/resume/upload")
@jwt_required() # 2. ADD this decorator
def upload_resume():
    # 3. REPLACE the old session line with this
    user_id = get_jwt_identity() 
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    # ---------------------------------
    
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file or file.filename.strip() == "":
        return jsonify({"error": "No selected file"}), 400

    if not _allowed_file(file):
        return jsonify({"error": "Invalid file type. Only PDF or DOCX files are allowed."}), 415

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
        cursor.execute(
            """
            INSERT INTO resumes (user_id, file_path, parsed_json)
            VALUES (?, ?, ?)
            """,
            (user_id, filepath, json.dumps(parsed_resume_data)), # 4. This user_id is now correct
        )
        db_conn.commit()
    except Exception as e:
        # If DB save fails, log the error and remove the saved file
        current_app.logger.error(f"Failed to save resume record to DB: {e}")
        os.remove(filepath)
        return jsonify({"error": "Database error during resume upload."}), 500
    finally:
        db.close_db()

    # 4. Score resume and store feedback report
    try:
        resume_text = ""
        sections = parsed_resume_data.get("sections") or []
        for section in sections:
            if section.get("name") == "full_content":
                resume_text = section.get("content") or ""
                break
        if not resume_text:
            resume_text = parsed_resume_data.get("raw_text") or ""

        score_payload = ai_helper.scoreResume(resume_text)
        score_val = int(score_payload.get("score", 0))
        summary = score_payload.get("summary") or "Resume scored."
        details = {
            "strengths": score_payload.get("strengths") or [],
            "weaknesses": score_payload.get("weaknesses") or [],
            "suggestions": score_payload.get("suggestions") or [],
        }

        db_conn.execute(
            """
            INSERT INTO feedback_reports (resume_id, score, summary, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (cursor.lastrowid, score_val, summary, json.dumps(details)),
        )
        db_conn.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to save resume score: {e}")

    # 5. Return success response
    return jsonify({
        "message": "Resume uploaded and parsed successfully",
        "resume_db_id": cursor.lastrowid, # Get the ID of the new resume record
        "filename": original_name,
        "size": os.path.getsize(filepath),
        "parsed_data": parsed_resume_data
    }), 200


@bp.get("/resume/latest")
@jwt_required()
def resume_latest():
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    row = _latest_resume_row(int(user_id))
    if not row:
        return jsonify({"error": "No resume found."}), 404

    parsed_json = row["parsed_json"]
    if parsed_json:
        try:
            parsed = json.loads(parsed_json)
            # Prefer full content section if present
            sections = parsed.get("sections") or []
            content = ""
            for section in sections:
                if section.get("name") == "full_content":
                    content = section.get("content") or ""
                    break
            if not content:
                content = parsed.get("raw_text") or ""
            return jsonify(
                {
                    "resume_id": row["id"],
                    "content": content,
                    "file_path": row["file_path"],
                    "created_at": row["created_at"],
                }
            ), 200
        except Exception:
            pass

    # Fallback: parse from file if stored JSON is missing or invalid
    filepath = row["file_path"]
    if not filepath or not os.path.isfile(filepath):
        return jsonify({"error": "Resume file not found."}), 404

    parsed = AIHelper().parseResume(filepath)
    if "error" in parsed:
        return jsonify({"error": parsed["error"]}), 500

    return jsonify(
        {
            "resume_id": row["id"],
            "content": parsed.get("sections", [{}])[0].get("content", ""),
            "file_path": filepath,
            "created_at": row["created_at"],
        }
    ), 200


@bp.put("/resume/update")
@jwt_required()
def resume_update():
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(force=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Resume content is required."}), 400

    row = _latest_resume_row(int(user_id))
    if not row:
        return jsonify({"error": "No resume found. Upload one first."}), 404

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    new_filepath = _save_text_as_docx(content, upload_dir)

    parsed = AIHelper().parseResume(new_filepath)
    if "error" in parsed:
        os.remove(new_filepath)
        return jsonify({"error": parsed["error"]}), 500

    db_conn = db.get_db()
    try:
        db_conn.execute(
            """
            UPDATE resumes
            SET file_path = ?, parsed_json = ?
            WHERE id = ? AND user_id = ?
            """,
            (new_filepath, json.dumps(parsed), row["id"], int(user_id)),
        )
        db_conn.commit()

        try:
            resume_text = ""
            sections = parsed.get("sections") or []
            for section in sections:
                if section.get("name") == "full_content":
                    resume_text = section.get("content") or ""
                    break
            if not resume_text:
                resume_text = parsed.get("raw_text") or ""

            score_payload = AIHelper().scoreResume(resume_text)
            score_val = int(score_payload.get("score", 0))
            summary = score_payload.get("summary") or "Resume scored."
            details = {
                "strengths": score_payload.get("strengths") or [],
                "weaknesses": score_payload.get("weaknesses") or [],
                "suggestions": score_payload.get("suggestions") or [],
            }
            db_conn.execute(
                """
                INSERT INTO feedback_reports (resume_id, score, summary, details_json)
                VALUES (?, ?, ?, ?)
                """,
                (row["id"], score_val, summary, json.dumps(details)),
            )
            db_conn.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to save resume score: {e}")
    except Exception as e:
        current_app.logger.error(f"Failed to update resume record: {e}")
        os.remove(new_filepath)
        return jsonify({"error": "Database error during resume update."}), 500

    return jsonify(
        {
            "message": "Resume updated successfully",
            "resume_db_id": row["id"],
            "file_path": new_filepath,
        }
    ), 200
# ---------------- View / Delete (optional) ----------------
@bp.delete("/resume")
@jwt_required()
def resume_delete():
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    row = _latest_resume_row(int(user_id))
    if not row:
        return jsonify({"message": "Nothing to delete"}), 200

    filepath = row["file_path"]
    if filepath and os.path.isfile(filepath):
        os.remove(filepath)

    db_conn = db.get_db()
    db_conn.execute(
        "DELETE FROM resumes WHERE id = ? AND user_id = ?",
        (row["id"], int(user_id)),
    )
    db_conn.commit()

    return jsonify({"message": "Deleted latest resume"}), 200
