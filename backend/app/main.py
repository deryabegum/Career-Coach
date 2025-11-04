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
from .extensions import bcrypt

bp = Blueprint("main", __name__)

# -------------------- Auth --------------------
# (These routes are no longer used by your new frontend, 
# but we'll leave them to avoid breaking anything)
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not all([email, password, name]):
        return jsonify({"error": "Missing required fields"}), 400

    db_conn = db.get_db()
    cursor = db_conn.cursor()
    try:
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, hashed_password, name),
        )
        db_conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close_db()


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    db_conn = db.get_db()
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return jsonify({"message": "Login successful"}), 200
        return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close_db()

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
def resume_view():
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isdir(upload_dir):
        abort(404)
    files = [f for f in os.listdir(upload_dir) if f.lower().endswith((".pdf", ".docx"))]
    if not files:
        abort(404)  # <-- THIS IS THE CORRECTED LINE
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(upload_dir, f)))
    return send_file(os.path.join(upload_dir, latest))


@bp.delete("/resume")
def resume_delete():
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isdir(upload_dir):
        return jsonify({"message": "Nothing to delete"}), 200
    files = [f for f in os.listdir(upload_dir) if f.lower().endswith((".pdf", ".docx"))]
    if not files:
        return jsonify({"message": "Nothing to delete"}), 200
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(upload_dir, f)))
    os.remove(os.path.join(upload_dir, latest))
    return jsonify({"message": f"Deleted {latest}"}), 200