# backend/app/features/dashboard_summary/service.py
from datetime import datetime, timezone
import sqlite3

from ..progress.service import get_progress_payload

class DashboardDAO:
    def __init__(self, conn):
        self.conn = conn

    def user_name(self, user_id: int):
        try:
            row = self.conn.execute(
                "SELECT name FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return row["name"] if row and row["name"] else "User"
        except (sqlite3.Error, KeyError, TypeError):
            return "User"

    def last_resume_score(self, user_id: int):   
        try:
            row = self.conn.execute(
                """
                SELECT fr.score
                FROM feedback_reports fr
                JOIN resumes r ON r.id = fr.resume_id
                WHERE r.user_id = ?
                ORDER BY fr.created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return int(row["score"]) if row and row["score"] is not None else 0
        except (sqlite3.Error, KeyError, ValueError, TypeError):
            return 0

    def interview_average(self, user_id):
        try:
            row = self.conn.execute("""
                SELECT AVG(score) AS avg_score
                FROM interview_answers ia
                JOIN interview_sessions s ON ia.session_id = s.id
                WHERE s.user_id = ?
            """, (user_id,)).fetchone()
            return round(float(row["avg_score"]), 2) if row and row["avg_score"] is not None else 0
        except (sqlite3.Error, KeyError, ValueError, TypeError):
            return 0

    def last_keyword_match(self, user_id):
        try:
            row = self.conn.execute("""
                SELECT ka.match_score 
                FROM keyword_analyses ka
                JOIN resumes r ON r.id = ka.resume_id
                WHERE r.user_id = ?
                ORDER BY ka.created_at DESC
                LIMIT 1
            """, (user_id,)).fetchone()
            return (row["match_score"] if row and row["match_score"] is not None else 0)
        except (sqlite3.Error, KeyError, ValueError, TypeError):
            return 0

    def totals(self, user_id):
        def count(table):
            try:
                if table == "keyword_analyses":
                    r = self.conn.execute(
                        """
                        SELECT COUNT(ka.id) AS c 
                        FROM keyword_analyses ka
                        JOIN resumes r ON r.id = ka.resume_id
                        WHERE r.user_id = ?
                        """, 
                        (user_id,)
                    ).fetchone()
                else:
                    r = self.conn.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE user_id = ?", (user_id,)).fetchone()
                
                return int(r["c"] if r and r["c"] is not None else 0)
            except (sqlite3.Error, KeyError, ValueError, TypeError):
                return 0

        progress = get_progress_payload(user_id)
        return {
            "resumes": count("resumes"),
            "interviews": int(progress.get("mock_interviews_completed", 0)),
            "matches": count("keyword_analyses"),
        }


def build_summary(dao: 'DashboardDAO', user_id: int):
    try:
        progress = get_progress_payload(user_id)
        totals = dao.totals(user_id)
        points = int(progress.get("points", 0))
        level = int(progress.get("level", 1))
        next_level_points = int(progress.get("next_level_points", level * 50))
        current_level_start_points = max(0, (level - 1) * 50)
        level_span = max(1, next_level_points - current_level_start_points)
        level_progress_pct = min(
            100,
            max(0, round(((points - current_level_start_points) / level_span) * 100)),
        )
        points_to_next_level = max(0, next_level_points - points)
        progress_pct = min(
            100,
            totals["resumes"] * 25
            + totals["matches"] * 20
            + totals["interviews"] * 25
            + min(points, 30),
        )
        return {
            "name": dao.user_name(user_id),
            "lastResumeScore": dao.last_resume_score(user_id),
            "interviewAverage": dao.interview_average(user_id),
            "lastKeywordMatchScore": dao.last_keyword_match(user_id),
            "totals": totals,
            "points": points,
            "level": level,
            "nextLevelPoints": next_level_points,
            "currentLevelStartPoints": current_level_start_points,
            "levelProgressPct": level_progress_pct,
            "pointsToNextLevel": points_to_next_level,
            "progressPct": progress_pct,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {
            "name": "User",
            "lastResumeScore": 0,
            "interviewAverage": 0,
            "lastKeywordMatchScore": 0,
            "totals": {
                "resumes": 0,
                "interviews": 0,
                "matches": 0,
            },
            "points": 0,
            "level": 1,
            "nextLevelPoints": 50,
            "currentLevelStartPoints": 0,
            "levelProgressPct": 0,
            "pointsToNextLevel": 50,
            "progressPct": 0,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
