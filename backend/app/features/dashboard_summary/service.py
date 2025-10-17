# backend/app/features/dashboard_summary/service.py

from datetime import datetime, timezone

class DashboardDAO:
    def __init__(self, conn):
        self.conn = conn

    def last_resume_score(self, user_id: int):   
        # Schema: feedback_reports.score and resumes.user_id are correct
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

    def interview_average(self, user_id):
        # Schema: interview_answers.score and interview_sessions.user_id are correct
        row = self.conn.execute("""
            SELECT AVG(score) AS avg_score
            FROM interview_answers ia
            JOIN interview_sessions s ON ia.session_id = s.id
            WHERE s.user_id = ?
        """, (user_id,)).fetchone()
        return round(float(row["avg_score"]), 2) if row and row["avg_score"] is not None else 0

    def last_keyword_match(self, user_id):
        # FIXES: 
        # 1. Corrected SELECT column to match_score (was 'score')
        # 2. Added JOIN to resumes table (was using non-existent user_id)
        row = self.conn.execute("""
            SELECT ka.match_score 
            FROM keyword_analyses ka
            JOIN resumes r ON r.id = ka.resume_id
            WHERE r.user_id = ?
            ORDER BY ka.created_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
        # FIX: Corrected return key to match_score (was 'score')
        return (row["match_score"] if row and row["match_score"] is not None else 0) 

    # FIX: Indentation corrected so 'totals' is a method of DashboardDAO
    def totals(self, user_id):
        
        # Helper function for counting
        def count(table):
            
            # FIX: Special logic for keyword_analyses (needs JOIN)
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
            
            # Logic for other tables (resumes, interview_sessions)
            else:
                # Uses f-string for table name, requires user_id column in table
                r = self.conn.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE user_id = ?", (user_id,)).fetchone()
            
            return int(r["c"] if r and r["c"] is not None else 0)
            
        return {
            "resumes": count("resumes"),
            "interviews": count("interview_sessions"),
            "matches": count("keyword_analyses"),
        }


def build_summary(dao: 'DashboardDAO', user_id: int):
    # FIX: Updated type hint to 'DashboardDAO'
    return {
        "lastResumeScore": dao.last_resume_score(user_id),
        "interviewAverage": dao.interview_average(user_id),
        "lastKeywordMatchScore": dao.last_keyword_match(user_id),
        "totals": dao.totals(user_id),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }