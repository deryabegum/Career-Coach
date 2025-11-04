import os, datetime, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app.db import get_db
from backend.app.extensions import bcrypt

ALGO = "HS256"
SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ACCESS_MIN = int(os.environ.get("JWT_ACCESS_MINUTES", "30"))

# 1. Add 'name' to the function signature
def create_user(email: str, password: str, name: str):
    db = get_db()
    pw_hash = generate_password_hash(password)
    
    # 2. Add 'name' to the query and use the correct 'password_hash' column
    db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)", 
        (email, pw_hash, name)
    )
    db.commit()

def get_user_by_email(email: str):
    # 3. Select the correct column name 'password_hash'
    return get_db().execute(
        "SELECT id, password_hash, name FROM users WHERE email = ?", 
        (email,)
    ).fetchone()

def verify_pw(password: str, hashed: str) -> bool:
    return check_password_hash(hashed, password)

# These functions are not used by your api.py but are left unchanged
def mint_access(user_id: int) -> str:
    exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_MIN)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET, algorithm=ALGO)

def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGO])