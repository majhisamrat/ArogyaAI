from pydantic import BaseModel
from typing import Optional

class SymptomAnalysisResponse(BaseModel):

    possible_disease: str

    severity: str

    advice: str

    see_doctor: bool

    confidence: float

    emergency: bool = False


class PlannerStep(BaseModel):

    tool: str

    reason: str


class PlannerResponse(BaseModel):

    plan: list[PlannerStep]