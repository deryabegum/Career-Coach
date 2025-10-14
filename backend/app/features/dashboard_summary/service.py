# put DB logic here later
# functions will call from api.py once wired to the database

from datetime import datetime, timezone

class SummaryDAO:
    def __init__(self, conn):
        self.conn = conn

    def last_resume_score(self, user_id):
        # TODO: adjust column/table to your schema (e.g., feedback_reports/keyword_analyses)
        row = self.conn.execute("""
            SELECT score FROM keyword_analyses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
        return (row["score"] if row and row["score"] is not None else 0)

    def interview_average(self, user_id):
        # If interview scoring is stored per answer, average scores from interview_answers
        row = self.conn.execute("""
            SELECT AVG(score) AS avg_score
            FROM interview_answers ia
            JOIN interview_sessions s ON ia.session_id = s.id
            WHERE s.user_id = ?
        """, (user_id,)).fetchone()
        return round(float(row["avg_score"]), 2) if row and row["avg_score"] is not None else 0

    def last_keyword_match(self, user_id):
        # Same table as first query (or change if you store a different metric)
        row = self.conn.execute("""
            SELECT score FROM keyword_analyses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
        return (row["score"] if row and row["score"] is not None else 0)

    def totals(self, user_id):
        def count(table):
            r = self.conn.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE user_id = ?", (user_id,)).fetchone()
            return int(r["c"] if r and r["c"] is not None else 0)
        # interviews = number of sessions
        return {
            "resumes": count("resumes"),
            "interviews": count("interview_sessions"),
            "matches": count("keyword_analyses"),
        }

def build_summary(dao: SummaryDAO, user_id: int):
    return {
        "lastResumeScore": dao.last_resume_score(user_id),
        "interviewAverage": dao.interview_average(user_id),
        "lastKeywordMatchScore": dao.last_keyword_match(user_id),
        "totals": dao.totals(user_id),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
