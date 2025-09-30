import os
import sqlite3
from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from . import db
from app.services.ai_helper import AIHelper

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-here'
app.config['DATABASE'] = os.path.join(app.instance_path, 'app.db')

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize the database with the Flask app
db.init_app(app)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
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
    data = request.get_json()
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
        
@app.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Call the AIHelper to parse the resume
        ai_helper = AIHelper()
        parsed_resume_data = ai_helper.parseResume(filepath)
        
        # Here you would save the parsed data to your database
        # For now, we'll just return it in the response
        return jsonify({
            "message": "Resume uploaded and parsed successfully", 
            "filename": filename,
            "parsed_data": parsed_resume_data
        }), 200

if __name__ == '__main__':
    app.run(debug=True)