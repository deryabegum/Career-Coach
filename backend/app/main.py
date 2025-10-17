# backend/app/main.py
import os
import sqlite3
from uuid import uuid4
from flask import Blueprint, request, jsonify, session, current_app, send_file, abort
from werkzeug.utils import secure_filename
from . import db
from .services.ai_helper import AIHelper
from .extensions import bcrypt

bp = Blueprint("main", __name__)

# -------------------- Auth --------------------
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


@bp.post("/resume/upload")
def upload_resume():
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
    file.save(filepath)

    ai_helper = AIHelper()
    parsed_resume_data = ai_helper.parseResume(filepath)

    return jsonify({
        "message": "Resume uploaded and parsed successfully",
        "id": rid,
        "filename": original_name,
        "stored_filename": saved_name,
        "mimeType": file.mimetype,
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
        abort(404)
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
