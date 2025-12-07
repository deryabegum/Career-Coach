# backend/app/features/resources/service.py

from typing import List, Dict
import sqlite3


class ResourceDAO:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def all_resources(self) -> List[Dict]:
        rows = self.conn.execute(
            """
            SELECT id, title, link, type
            FROM resources
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def recommended(self, resume_score: int, interview_avg: float) -> List[Dict]:
        """
        Very simple recommendation logic:
        - If resume score is low  -> show resume resources
        - If interview avg is low -> show interview tips
        - If both are OK          -> show articles
        """

        resume_score = resume_score or 0
        interview_avg = interview_avg or 0

        types: List[str] = []

        if resume_score < 75:
            types.append("resume")

        if interview_avg < 75:
            types.append("interview")

        if not types:
            types.append("article")

        placeholders = ",".join("?" * len(types))

        rows = self.conn.execute(
            f"""
            SELECT id, title, link, type
            FROM resources
            WHERE type IN ({placeholders})
            ORDER BY id ASC
            """,
            types,
        ).fetchall()

        return [dict(r) for r in rows]
