from flask import Blueprint, jsonify
from ...common.wire import get_db_conn  # fixed: wire, not wair
from .service import DashboardDAO, build_summary

from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("dashboard_summary", __name__, url_prefix="/api/v1/dashboard")

def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    return int(uid)

@bp.get("/summary")
@jwt_required()
def summary():
    conn = get_db_conn()
    try:
        dao = DashboardDAO(conn)
        user_id = _current_user_id()
        return jsonify(build_summary(dao, user_id)), 200
    finally:
        try:
            conn.close()
        except Exception:
            pass
