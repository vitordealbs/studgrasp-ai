from typing import List, Optional
from pydantic import BaseModel

from app.schemas.analysis import WeakTopic


class InsightRequest(BaseModel):
    userId: str
    weakTopics: List[WeakTopic]
    streak: int
    reviewedToday: int
    correctToday: int
    dueNow: int
    retentionRate: Optional[float] = None


class InsightResponse(BaseModel):
    userId: str
    insights: List[str]


class StudentStats(BaseModel):
    userId: str
    userName: str
    reviewedToday: int
    retentionRate: Optional[float] = None


class ClassInsightRequest(BaseModel):
    classId: str
    totalStudents: int
    avgRetentionRate: Optional[float] = None
    totalReviewedToday: int
    weakTopics: List[WeakTopic]
    students: List[StudentStats]


class ClassInsightResponse(BaseModel):
    classId: str
    insights: List[str]
