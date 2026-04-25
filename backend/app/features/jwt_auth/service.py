from ...db import get_db
from ...extensions import bcrypt
from werkzeug.security import check_password_hash as werkzeug_check_password_hash


def create_user(email: str, password: str, name: str):
    db = get_db()
    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        (email, pw_hash, name),
    )
    db.commit()


def get_user_by_email(email: str):
    return get_db().execute(
        "SELECT id, password_hash, name FROM users WHERE email = ?",
        (email,),
    ).fetchone()


def verify_pw(password: str, hashed: str) -> bool:
    if not hashed:
        return False

    if hashed.startswith("scrypt:") or hashed.startswith("pbkdf2:"):
        return werkzeug_check_password_hash(hashed, password)

    try:
        return bcrypt.check_password_hash(hashed, password)
    except ValueError:
        return False
