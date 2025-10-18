from flask import Blueprint, request, jsonify, g
from backend.app.features.jwt_auth.service import (
    create_user, get_user_by_email, verify_pw, mint_access, decode_token
)

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

@bp.post("/register")
def register():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error":"email and password required"}), 400
    if get_user_by_email(email):
        return jsonify({"error":"email already exists"}), 409
    create_user(email, password)
    return jsonify({"ok": True}), 201

@bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    u = get_user_by_email(email)
    if not u or not verify_pw(password, u["password"]):
        return jsonify({"error":"invalid credentials"}), 401
    return jsonify({"accessToken": mint_access(u["id"])}), 200

# tiny decorator to protect routes
def jwt_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization","")
        if not auth.startswith("Bearer "):
            return jsonify({"error":"missing bearer token"}), 401
        token = auth.split(" ",1)[1]
        try:
            payload = decode_token(token)
        except Exception:
            return jsonify({"error":"invalid or expired token"}), 401
        g.user_id = int(payload.get("sub"))
        return fn(*args, **kwargs)
    return wrapper
