import os
import sqlite3
from uuid import uuid4
from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from . import db
from .services.ai_helper import AIHelper

app = Flask(__name__)

# ---- App Config ----
app.config['SECRET_KEY'] = 'your-very-secret-key-here'
app.config['DATABASE'] = os.path.join(app.instance_path, 'app.db')

# Uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Limit uploads (optional safety)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Allowed file types for resume uploads
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}
app.config['ALLOWED_MIMETYPES'] = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

# ---- Extensions ----
bcrypt = Bcrypt(app)
db.init_app(app)


# ---------------- Auth ----------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not all([email, password, name]):
        return jsonify({"error": "Missing required fields"}), 400

    db_conn = db.get_db()
    cursor = db_conn.cursor()

    try:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, hashed_password, name)
        )
        db_conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close_db()


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    db_conn = db.get_db()
    cursor = db_conn.cursor()

    try:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close_db()


# ------------- Resume Upload -------------
def _allowed_file(upload) -> bool:
    """Validate both extension and MIME type."""
    filename = secure_filename(upload.filename or "")
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return (
        ext in app.config['ALLOWED_EXTENSIONS']
        and (upload.mimetype in app.config['ALLOWED_MIMETYPES'])
    )


@app.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if not file or file.filename.strip() == '':
        return jsonify({"error": "No selected file"}), 400

    # Validate type (PDF/DOCX only)
    if not _allowed_file(file):
        return jsonify({"error": "Invalid file type. Only PDF or DOCX files are allowed."}), 415

    # Save with a UUID prefix to avoid collisions
    original_name = secure_filename(file.filename)
    rid = str(uuid4())
    saved_name = f"{rid}_{original_name}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
    file.save(filepath)

    # Parse via AI helper
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


if __name__ == '__main__':
    app.run(debug=True)