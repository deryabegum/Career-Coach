from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from backend.app.features.jwt_auth.service import (
    create_user,
    get_user_by_email,
    verify_pw,
)

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/register")
def register():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    if get_user_by_email(email):
        return jsonify({"error": "email already exists"}), 409
    create_user(email, password)
    return jsonify({"ok": True}), 201


@bp.post("/login")
def login():
    """
    Verifies email/password and returns JWT access and refresh tokens.

    Response shape keeps your existing key for the frontend:
      { "accessToken": "<JWT string>", "refreshToken": "<JWT string>" }
    """
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_user_by_email(email)
    if not user or not verify_pw(password, user["password"]):
        return jsonify({"error": "invalid credentials"}), 401

    user_id = int(user["id"])

    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    return jsonify(
        {
            "accessToken": access_token,
            "refreshToken": refresh_token,
        }
    ), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """
    Uses a valid refresh token to issue a new access token.
    """
    identity = int(get_jwt_identity())
    new_access_token = create_access_token(identity=identity)
    return jsonify({"accessToken": new_access_token}), 200


@bp.get("/me")
@jwt_required()
def me():
    return jsonify({"user_id": int(get_jwt_identity())}), 200
