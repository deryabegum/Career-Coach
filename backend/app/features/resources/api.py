# backend/app/features/resources/api.py

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ...db import get_db
from ..dashboard_summary.service import DashboardDAO, build_summary
from .service import ResourceDAO

bp = Blueprint("resources", __name__, url_prefix="/api/v1/resources")


@bp.get("")
def get_all_resources():
    try:
        conn = get_db()
        dao = ResourceDAO(conn)
        resources = dao.all_resources()
        return jsonify({"resources": resources}), 200
    except Exception as e:
        current_app.logger.error("Error loading all resources", exc_info=True)
        return jsonify({"error": "Could not load resources"}), 500


@bp.get("/recommended")
@jwt_required(optional=True)
def get_recommended_resources():
    try:
        conn = get_db()
        dao = ResourceDAO(conn)

        user_id = get_jwt_identity()
        resume_score = 0
        interview_avg = 0

        if user_id is not None:
            try:
                uid_int = int(user_id)
            except (TypeError, ValueError):
                uid_int = 0

            dashboard_dao = DashboardDAO(conn)
            summary = build_summary(dashboard_dao, uid_int)

            resume_score = summary.get("lastResumeScore", 0) or 0
            interview_avg = summary.get("interviewAverage", 0) or 0

        recommended = dao.recommended(resume_score, interview_avg)

        return jsonify(
            {
                "resources": recommended,
                "resumeScore": resume_score,
                "interviewAverage": interview_avg,
            }
        ), 200

    except Exception as e:
        current_app.logger.error("Error loading recommended resources", exc_info=True)
        return jsonify({"error": "Could not load recommended resources"}), 500
