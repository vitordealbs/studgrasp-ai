import asyncio
from typing import List, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.analysis import WeakTopic


def calculate_sm2(
    quality: int,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
) -> Tuple[float, int, int]:
    """
    SM-2 algorithm. quality: 0-5 (0-2 = fail, 3-5 = pass).
    Returns (new_ease_factor, new_interval_days, new_repetitions).
    """
    if quality < 3:
        new_repetitions = 0
        new_interval = 1
        new_ease = ease_factor
    else:
        new_repetitions = repetitions + 1
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)

        new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    new_ease = max(1.3, new_ease)
    return new_ease, new_interval, new_repetitions


def _query_due_flashcards(user_id: str, db: Session) -> List[dict]:
    sql = text(
        """
        SELECT
            f.id,
            f.node_id,
            f.question,
            f.answer,
            f.difficulty,
            fa.next_review_at,
            fa.ease_factor,
            fa.interval_days,
            fa.repetitions
        FROM flashcard_attempts fa
        JOIN flashcards f ON fa.flashcard_id = f.id
        WHERE fa.user_id = :user_id
          AND fa.next_review_at <= NOW()
        ORDER BY fa.next_review_at ASC
        """
    )
    rows = db.execute(sql, {"user_id": user_id}).fetchall()
    return [
        {
            "id": str(row.id),
            "nodeId": str(row.node_id) if row.node_id else None,
            "question": row.question,
            "answer": row.answer,
            "difficulty": row.difficulty,
            "nextReviewAt": row.next_review_at.isoformat() if row.next_review_at else None,
            "easeFactor": float(row.ease_factor) if row.ease_factor else None,
            "intervalDays": row.interval_days,
            "repetitions": row.repetitions,
        }
        for row in rows
    ]


def _query_weak_topics(user_id: str, db: Session) -> List[WeakTopic]:
    sql = text(
        """
        SELECT
            rn.id        AS node_id,
            rn.title     AS node_title,
            COUNT(fa.id)                                               AS total_attempts,
            SUM(CASE WHEN fa.correct = false THEN 1 ELSE 0 END)       AS wrong_attempts
        FROM flashcard_attempts fa
        JOIN flashcards f  ON fa.flashcard_id = f.id
        JOIN roadmap_nodes rn ON f.node_id = rn.id
        WHERE fa.user_id = :user_id
        GROUP BY rn.id, rn.title
        HAVING COUNT(fa.id) > 0
        ORDER BY (SUM(CASE WHEN fa.correct = false THEN 1 ELSE 0 END)::float / COUNT(fa.id)) DESC
        """
    )
    rows = db.execute(sql, {"user_id": user_id}).fetchall()
    return [
        WeakTopic(
            nodeId=str(row.node_id),
            nodeTitle=row.node_title,
            errorRate=round(row.wrong_attempts / row.total_attempts, 4),
        )
        for row in rows
    ]


async def get_due_flashcards(user_id: str, db: Session) -> List[dict]:
    return await asyncio.to_thread(_query_due_flashcards, user_id, db)


async def get_weak_topics(user_id: str, db: Session) -> List[WeakTopic]:
    return await asyncio.to_thread(_query_weak_topics, user_id, db)
