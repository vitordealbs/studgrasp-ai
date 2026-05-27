import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.services.spaced_repetition import (
    calculate_sm2,
    _query_due_flashcards,
    _query_weak_topics,
)


# --- SM-2 unit tests ---

def test_sm2_quality_below_3_resets():
    ease, interval, reps = calculate_sm2(quality=2, ease_factor=2.5, interval_days=6, repetitions=3)
    assert reps == 0
    assert interval == 1
    assert ease == 2.5


def test_sm2_first_correct_answer():
    ease, interval, reps = calculate_sm2(quality=4, ease_factor=2.5, interval_days=1, repetitions=0)
    assert reps == 1
    assert interval == 1


def test_sm2_second_correct_answer():
    ease, interval, reps = calculate_sm2(quality=4, ease_factor=2.5, interval_days=1, repetitions=1)
    assert reps == 2
    assert interval == 6


def test_sm2_subsequent_correct():
    ease, interval, reps = calculate_sm2(quality=5, ease_factor=2.5, interval_days=6, repetitions=2)
    assert reps == 3
    assert interval == round(6 * 2.5)


def test_sm2_ease_factor_minimum():
    ease, _, _ = calculate_sm2(quality=0, ease_factor=1.3, interval_days=1, repetitions=0)
    assert ease >= 1.3


def test_sm2_ease_increases_on_perfect():
    ease, _, _ = calculate_sm2(quality=5, ease_factor=2.5, interval_days=1, repetitions=0)
    assert ease > 2.5


# --- DB query tests ---

def _make_row(**kwargs):
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def test_query_due_flashcards():
    db = MagicMock()
    now = datetime.now(timezone.utc)
    row = _make_row(
        id="fc-1",
        node_id="node-1",
        question="Q?",
        answer="A",
        difficulty="EASY",
        next_review_at=now,
        ease_factor=2.5,
        interval_days=1,
        repetitions=0,
    )
    db.execute.return_value.fetchall.return_value = [row]

    result = _query_due_flashcards("user-1", db)

    assert len(result) == 1
    assert result[0]["id"] == "fc-1"
    assert result[0]["easeFactor"] == 2.5


def test_query_due_flashcards_empty():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = []

    result = _query_due_flashcards("user-1", db)

    assert result == []


def test_query_weak_topics():
    db = MagicMock()
    row = _make_row(
        node_id="node-1",
        node_title="HTTP",
        total_attempts=10,
        wrong_attempts=7,
    )
    db.execute.return_value.fetchall.return_value = [row]

    result = _query_weak_topics("user-1", db)

    assert len(result) == 1
    assert result[0].nodeTitle == "HTTP"
    assert result[0].errorRate == 0.7


def test_query_weak_topics_empty():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = []

    result = _query_weak_topics("user-1", db)

    assert result == []
