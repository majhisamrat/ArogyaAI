from fastapi import APIRouter, HTTPException

from database.login_manager import (
    get_user_health_history,
    get_user
)

from ..schemas.chat_schema import (
    HealthRecordResponse
)

router = APIRouter()

# API Health Check

@router.get("/health")
async def health_check():

    return {
        "status": "ok",
        "service": "Rural Health Assistant API"
    }

# User Health History

@router.get(
    "/history/{phone_number}",
    response_model=list[HealthRecordResponse]
)
async def get_health_history(
    phone_number: str
):

    user = get_user(phone_number)

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    history = get_user_health_history(
        phone_number
    )

    return history