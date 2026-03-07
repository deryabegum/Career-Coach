from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .service import get_progress_payload, ensure_progress_row

bp = Blueprint("progress", __name__, url_prefix="/api/v1/progress")


@bp.get("/me")
@jwt_required()
def my_progress():
    user_id = int(get_jwt_identity())
    ensure_progress_row(user_id)
    return jsonify(get_progress_payload(user_id)), 200
