import os
import sqlite3
from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from . import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-here'  # Required for sessions
app.config['DATABASE'] = os.path.join(app.instance_path, 'app.db')

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize the database with the Flask app
db.init_app(app)

@app.route('/api/register', methods=['POST'])
def register():
    # (Your existing registration code here)
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
            # If login is successful, you can manage the session or return a token
            session['user_id'] = user['id']
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close_db()

if __name__ == '__main__':
    app.run(debug=True)