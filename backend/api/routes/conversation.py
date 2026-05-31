from fastapi import APIRouter

from pydantic import BaseModel

from database.conversation_manager import (
    create_conversation,
    save_message,
    get_user_conversations,
    get_conversation_messages,
    update_conversation_title,
    delete_conversation
)

router = APIRouter()



class CreateConversationRequest(BaseModel):

    phone_number: str

    title: str = "New Chat"


class UpdateTitleRequest(BaseModel):

    title: str



@router.post("/conversation/create")
async def create_conversation_endpoint(
    payload: CreateConversationRequest
):

    convo_id = create_conversation(
        payload.phone_number,
        payload.title
    )

    return {
        "conversation_id": convo_id
    }



@router.get("/conversations/{phone_number}")
async def get_conversations(
    phone_number: str
):

    return {
        "conversations":
            get_user_conversations(
                phone_number
            )
    }



@router.get("/conversation/{conversation_id}")
async def get_messages(
    conversation_id: int
):
    from database.db_handler import get_db_session
    from database.models import Conversation

    db = get_db_session()
    try:
        convo = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if not convo:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "id": convo.id,
            "title": convo.title,
            "created_at": convo.created_at.isoformat(),
            "updated_at": convo.updated_at.isoformat(),
            "messages": get_conversation_messages(conversation_id)
        }
    finally:
        db.close()


@router.patch("/conversation/{conversation_id}/title")
async def update_title(
    conversation_id: int,
    payload: UpdateTitleRequest
):
    """Update the title/name of a conversation."""
    success = update_conversation_title(conversation_id, payload.title)
    if success:
        return {"success": True, "title": payload.title}
    return {"success": False, "detail": "Conversation not found"}


@router.delete("/conversation/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: int
):
    """Delete a conversation and all its messages."""
    success = delete_conversation(conversation_id)
    if success:
        return {"success": True}
    
    from fastapi import HTTPException
    raise HTTPException(
        status_code=404,
        detail="Conversation not found or could not be deleted"
    )