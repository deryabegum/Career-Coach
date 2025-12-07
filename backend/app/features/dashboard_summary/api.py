from flask import Blueprint, jsonify, current_app
from ...common.wire import get_db_conn  # fixed: wire, not wair
from .service import DashboardDAO, build_summary

from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("dashboard_summary", __name__, url_prefix="/api/v1/dashboard")

def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    try:
        return int(uid)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid user ID format: {uid}") from e

@bp.get("/summary")
@jwt_required()
def summary():
    conn = None
    try:
        conn = get_db_conn()
        dao = DashboardDAO(conn)
        user_id = _current_user_id()
        result = build_summary(dao, user_id)
        return jsonify(result), 200
    except PermissionError as e:
        current_app.logger.error(f"Permission error in dashboard summary: {e}")
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except ValueError as e:
        current_app.logger.error(f"Value error in dashboard summary: {e}")
        return jsonify({"error": "Invalid request", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in dashboard summary: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": "An error occurred while fetching dashboard data"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
