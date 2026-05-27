from typing import List
from pydantic import BaseModel


class WeakTopic(BaseModel):
    nodeId: str
    nodeTitle: str
    errorRate: float


class AnalysisResponse(BaseModel):
    userId: str
    weakTopics: List[WeakTopic]
