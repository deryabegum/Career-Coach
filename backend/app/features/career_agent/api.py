# backend/app/features/career_agent/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ...common.wire import get_db_conn
from .service import CareerAgentDAO, run_career_agent

bp = Blueprint("career_agent", __name__, url_prefix="/api/v1/career-agent")


def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        raise PermissionError("No JWT identity found")
    try:
        return int(uid)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid user ID format: {uid}") from e


@bp.post("/run")
@jwt_required()
def run_agent():
    conn = None
    try:
        user_id = _current_user_id()
        body = request.get_json(silent=True) or {}

        job_description = (body.get("job_description") or "").strip()
        role = (body.get("role") or "").strip()
        company = (body.get("company") or "").strip()

        if not job_description:
            return jsonify({"error": "job_description is required"}), 400

        conn = get_db_conn()
        result = run_career_agent(conn, user_id, job_description, role, company)
        return jsonify(result), 201
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error running career agent: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.get("/runs")
@jwt_required()
def list_runs():
    conn = None
    try:
        user_id = _current_user_id()
        conn = get_db_conn()
        runs = CareerAgentDAO(conn).list_runs(user_id)
        return jsonify({"runs": runs}), 200
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error listing career agent runs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.get("/runs/<int:run_id>")
@jwt_required()
def get_run(run_id: int):
    conn = None
    try:
        user_id = _current_user_id()
        conn = get_db_conn()
        run = CareerAgentDAO(conn).get_run(run_id, user_id)
        if run is None:
            return jsonify({"error": "Run not found"}), 404
        return jsonify(run), 200
    except PermissionError as e:
        return jsonify({"error": "Authentication required", "message": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Error fetching career agent run: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
