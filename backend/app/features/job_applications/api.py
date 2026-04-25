from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ...common.wire import get_db_conn
from .service import ApplicationDAO

bp = Blueprint("job_applications", __name__, url_prefix="/api/v1/applications")

VALID_STAGES = {"applied", "phone_screen", "interview", "offer", "rejected"}


def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    try:
        return int(uid)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid user ID format: {uid}") from e


@bp.get("/")
@jwt_required()
def list_applications():
    conn = None
    try:
        conn = get_db_conn()
        user_id = _current_user_id()
        apps = ApplicationDAO(conn).list(user_id)
        return jsonify({"applications": apps}), 200
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error listing applications: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.post("/")
@jwt_required()
def create_application():
    conn = None
    try:
        conn = get_db_conn()
        user_id = _current_user_id()
        body = request.get_json(silent=True) or {}

        company_name = (body.get("company_name") or "").strip()
        applied_date = (body.get("applied_date") or "").strip()
        stage = (body.get("stage") or "applied").strip()
        field = (body.get("field") or "").strip()

        if not company_name:
            return jsonify({"error": "company_name is required"}), 400
        if not applied_date:
            return jsonify({"error": "applied_date is required"}), 400
        if stage not in VALID_STAGES:
            return jsonify({"error": f"stage must be one of {sorted(VALID_STAGES)}"}), 400

        new_id = ApplicationDAO(conn).create(user_id, company_name, applied_date, stage, field)
        return jsonify({"id": new_id}), 201
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error creating application: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.put("/<int:app_id>")
@jwt_required()
def update_application(app_id):
    conn = None
    try:
        conn = get_db_conn()
        user_id = _current_user_id()
        body = request.get_json(silent=True) or {}

        company_name = (body.get("company_name") or "").strip()
        applied_date = (body.get("applied_date") or "").strip()
        stage = (body.get("stage") or "applied").strip()
        field = (body.get("field") or "").strip()

        if not company_name:
            return jsonify({"error": "company_name is required"}), 400
        if not applied_date:
            return jsonify({"error": "applied_date is required"}), 400
        if stage not in VALID_STAGES:
            return jsonify({"error": f"stage must be one of {sorted(VALID_STAGES)}"}), 400

        ApplicationDAO(conn).update(app_id, user_id, company_name, applied_date, stage, field)
        return jsonify({"ok": True}), 200
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error updating application: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.delete("/<int:app_id>")
@jwt_required()
def delete_application(app_id):
    conn = None
    try:
        conn = get_db_conn()
        user_id = _current_user_id()
        ApplicationDAO(conn).delete(app_id, user_id)
        return jsonify({"ok": True}), 200
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error deleting application: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
