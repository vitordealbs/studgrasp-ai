from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class FlashcardGenerateRequest(BaseModel):
    nodeId: str
    nodeTitle: str
    nodeDescription: str
    quantity: int = Field(default=5, ge=1, le=20)


class FlashcardItem(BaseModel):
    question: str
    answer: str
    difficulty: Difficulty


class FlashcardGenerateResponse(BaseModel):
    nodeId: str
    flashcards: List[FlashcardItem]


class ReviewFlashcard(BaseModel):
    id: str
    nodeId: Optional[str]
    question: str
    answer: str
    difficulty: str
    nextReviewAt: Optional[str]
    easeFactor: Optional[float]
    intervalDays: Optional[int]
    repetitions: Optional[int]
