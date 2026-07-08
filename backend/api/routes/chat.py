from fastapi import APIRouter

from ..schemas.chat_schema import (
    ChatRequest,
    ChatResponse
)

from orchestrator.langgraph_coordinator import LangGraphCoordinator


router = APIRouter()

coordinator = LangGraphCoordinator()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):

    history = [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in payload.history
    ]

    response = coordinator.handle_message(
        phone_number=payload.phone_number,
        user_input=payload.message,
        conversation_id=payload.conversation_id,
        chat_history=history
    )

    return ChatResponse(
        response=response
    )