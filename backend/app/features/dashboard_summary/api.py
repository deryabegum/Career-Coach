from flask import Blueprint, jsonify, g
from backend.app.common.wire import get_db_conn
from backend.app.features.dashboard_summary.service import SummaryDAO, build_summary

bp = Blueprint("dashboard_summary", __name__, url_prefix="/api/v1/dashboard")

def _current_user_id():
    # swap with JWT later; for now use session or a fixed id for testing
    return getattr(g, "user_id", 1)

@bp.get("/summary")
def summary():
    conn = get_db_conn()
    dao = SummaryDAO(conn)
    return jsonify(build_summary(dao, _current_user_id())), 200
