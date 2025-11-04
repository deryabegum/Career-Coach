from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.app.features.jwt_auth.service import (
    create_user, get_user_by_email, verify_pw
)

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/register")
def register():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() # <-- 1. Get name from request

    # 2. Check for name
    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400
    
    if get_user_by_email(email):
        return jsonify({"error": "email already exists"}), 409
    
    # 3. Pass name to create_user
    create_user(email, password, name)
    return jsonify({"ok": True}), 201


@bp.post("/login")
def login():
    """
    Verifies email/password and returns a JWT access token.

    Response shape keeps your existing key for the frontend:
      { "accessToken": "<JWT string>" }
    """
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_user_by_email(email)
    
    # 4. --- FIX THE LOGIN BUG ---
    #    Change user["password"] to user["password_hash"]
    if not user or not verify_pw(password, user["password_hash"]):
        return jsonify({"error": "invalid credentials"}), 401

    # identity becomes get_jwt_identity() on protected routes
    token = create_access_token(identity=int(user["id"]))
    return jsonify({"accessToken": token}), 200


# Optional endpoint: proves JWT works with get_jwt_identity()
@bp.get("/me")
@jwt_required()
def me():
    return jsonify({"user_id": int(get_jwt_identity())}), 200