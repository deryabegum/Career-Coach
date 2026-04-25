class ApplicationDAO:
    def __init__(self, conn):
        self.conn = conn

    def list(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM job_applications WHERE user_id = ? ORDER BY applied_date DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def create(self, user_id, company_name, applied_date, stage, field):
        cur = self.conn.execute(
            "INSERT INTO job_applications (user_id, company_name, applied_date, stage, field)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, company_name, applied_date, stage, field),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, app_id, user_id, company_name, applied_date, stage, field):
        self.conn.execute(
            "UPDATE job_applications"
            " SET company_name = ?, applied_date = ?, stage = ?, field = ?"
            " WHERE id = ? AND user_id = ?",
            (company_name, applied_date, stage, field, app_id, user_id),
        )
        self.conn.commit()

    def delete(self, app_id, user_id):
        self.conn.execute(
            "DELETE FROM job_applications WHERE id = ? AND user_id = ?",
            (app_id, user_id),
        )
        self.conn.commit()
