from flask import Blueprint, jsonify, g
from backend.app.common.wire import get_db_conn
from backend.app.features.dashboard_summary.service import SummaryDAO, build_summary

from backend.app.features.jwt_auth.api import jwt_required

bp = Blueprint("dashboard_summary", __name__, url_prefix="/api/v1/dashboard")

def _current_user_id():
    return g.user_id

@bp.get("/summary")
@jwt_required 
def summary():
    conn = get_db_conn()
    dao = SummaryDAO(conn)
    return jsonify(build_summary(dao, _current_user_id())), 200
