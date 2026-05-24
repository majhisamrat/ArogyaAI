from fastapi import APIRouter

from pydantic import BaseModel

from database.conversation_manager import (
    create_conversation,
    save_message,
    get_user_conversations,
    get_conversation_messages
)

router = APIRouter()



class CreateConversationRequest(BaseModel):

    phone_number: str

    title: str = "New Chat"



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

    return {
        "messages":
            get_conversation_messages(
                conversation_id
            )
    }