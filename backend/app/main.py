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

    # 4. Return success response
    return jsonify({
        "message": "Resume uploaded and parsed successfully",
        "resume_db_id": cursor.lastrowid, # Get the ID of the new resume record
        "filename": original_name,
        "size": os.path.getsize(filepath),
        "parsed_data": parsed_resume_data
    }), 200
# ---------------- View / Delete (optional) ----------------
@bp.get("/resume/view")
@jwt_required()
def resume_view():
    user_id = get_jwt_identity()
    db_conn = db.get_db()
    row = db_conn.execute(
        "SELECT file_path FROM resumes WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if not row or not os.path.isfile(row["file_path"]):
        abort(404)
    return send_file(row["file_path"])


@bp.delete("/resume")
@jwt_required()
def resume_delete():
    user_id = get_jwt_identity()
    db_conn = db.get_db()
    row = db_conn.execute(
        "SELECT id, file_path FROM resumes WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if not row:
        return jsonify({"message": "Nothing to delete"}), 200
    # Remove the file from disk if it still exists
    if os.path.isfile(row["file_path"]):
        os.remove(row["file_path"])
    db_conn.execute("DELETE FROM resumes WHERE id = ?", (row["id"],))
    db_conn.commit()
    return jsonify({"message": "Resume deleted"}), 200