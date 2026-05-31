from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HealthRecordResponse(BaseModel):

    possible_disease: str

    severity: str

    confidence: float

    emergency: bool

    timestamp: datetime

class ChatMessage(BaseModel):

    role: str
    content: str


class ChatRequest(BaseModel):

    phone_number: str
    message: str
    conversation_id: Optional[int] = None
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):

    response: str