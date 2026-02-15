from __future__ import annotations

from typing import List, Dict, Any
from ...db import get_db


BADGES = [
    ("first_steps",        lambda p: p["points"] > 0),
    ("resume_starter",     lambda p: p["best_resume_score"] > 0),
    ("interview_rookie",   lambda p: p["mock_interviews_completed"] >= 1),
    ("interview_regular",  lambda p: p["mock_interviews_completed"] >= 5),
    ("consistency_100",    lambda p: p["points"] >= 100),
]


def ensure_progress_row(user_id: int) -> None:
    db = get_db()
    db.execute(
        """
        INSERT OR IGNORE INTO user_progress (user_id, points, best_resume_score, mock_interviews_completed)
        VALUES (?, 0, 0, 0)
        """,
        (user_id,),
    )
    db.commit()


def _get_progress_row(user_id: int) -> Dict[str, Any]:
    ensure_progress_row(user_id)
    row = get_db().execute(
        """
        SELECT user_id, points, best_resume_score, mock_interviews_completed
        FROM user_progress
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return dict(row) if row else {
        "user_id": user_id,
        "points": 0,
        "best_resume_score": 0,
        "mock_interviews_completed": 0,
    }


def _get_badges(user_id: int) -> List[str]:
    rows = get_db().execute(
        "SELECT badge_key FROM user_badges WHERE user_id = ? ORDER BY earned_at ASC",
        (user_id,),
    ).fetchall()
    return [r["badge_key"] for r in rows]


def _award_badge_if_missing(user_id: int, badge_key: str) -> None:
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO user_badges (user_id, badge_key) VALUES (?, ?)",
        (user_id, badge_key),
    )
    db.commit()


def check_and_award_badges(user_id: int) -> None:
    p = _get_progress_row(user_id)
    for badge_key, rule in BADGES:
        if rule(p):
            _award_badge_if_missing(user_id, badge_key)


def award_mock_interview_completed(user_id: int) -> None:
    ensure_progress_row(user_id)
    db = get_db()
    db.execute(
        """
        UPDATE user_progress
        SET points = points + 20,
            mock_interviews_completed = mock_interviews_completed + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (user_id,),
    )
    db.commit()
    check_and_award_badges(user_id)


def award_resume_score(user_id: int, new_score_0_to_100: int) -> None:
    ensure_progress_row(user_id)
    p = _get_progress_row(user_id)

    new_score = int(max(0, min(100, new_score_0_to_100)))
    best = int(p["best_resume_score"] or 0)

    if new_score <= best:
        return

    improvement = new_score - best
    points_awarded = (improvement // 5) * 10

    db = get_db()
    db.execute(
        """
        UPDATE user_progress
        SET points = points + ?,
            best_resume_score = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (points_awarded, new_score, user_id),
    )
    db.commit()
    check_and_award_badges(user_id)


def get_progress_payload(user_id: int) -> Dict[str, Any]:
    p = _get_progress_row(user_id)
    badges = _get_badges(user_id)

    points = int(p["points"] or 0)
    level = (points // 50) + 1
    next_level_points = level * 50

    return {
        "points": points,
        "level": level,
        "next_level_points": next_level_points,
        "best_resume_score": int(p["best_resume_score"] or 0),
        "mock_interviews_completed": int(p["mock_interviews_completed"] or 0),
        "badges": badges,
    }
