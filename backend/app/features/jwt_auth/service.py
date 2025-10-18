import os, datetime, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app.db import get_db

ALGO = "HS256"
SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ACCESS_MIN = int(os.environ.get("JWT_ACCESS_MINUTES", "30"))

def create_user(email: str, password: str):
    db = get_db()
    pw_hash = generate_password_hash(password)
    db.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, pw_hash))
    db.commit()

def get_user_by_email(email: str):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def verify_pw(password: str, hashed: str) -> bool:
    return check_password_hash(hashed, password)

def mint_access(user_id: int) -> str:
    exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_MIN)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET, algorithm=ALGO)

def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGO])
