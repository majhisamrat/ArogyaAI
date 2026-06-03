from fastapi import APIRouter, HTTPException

from pydantic import BaseModel
from database.login_manager import (
    register_user,
    get_user,
    is_registered,
    update_user_language
)

from api.schemas.user_schema import (
    UserRegisterRequest,
    UserResponse
)
from auth.otp_service import verify_otp_code
from api.auth.jwt_handler import create_access_token

router = APIRouter()


@router.get("/user/{phone_number}")
async def get_user_profile(phone_number: str):

    user = get_user(phone_number)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "user": user
    }


@router.post("/register", response_model=UserResponse)
async def register_user_endpoint(payload: UserRegisterRequest):

    if is_registered(payload.phone_number):

        raise HTTPException(
            status_code=400,
            detail="User already registered"
        )

    # Verify OTP first for secure registration
    otp_res = verify_otp_code(payload.phone_number, payload.otp)
    if not otp_res.get("success"):
        raise HTTPException(
            status_code=400,
            detail=otp_res.get("message", "Invalid or expired OTP")
        )

    user = register_user(
        phone_number=payload.phone_number,
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        pincode=payload.pincode,
        language=payload.language
    )

    # Create JWT access token for immediate session setup
    token = create_access_token({"phone_number": payload.phone_number})
    response_data = dict(user)
    response_data["token"] = token

    return UserResponse(**response_data)


class UserUpdateLanguageRequest(BaseModel):
    phone_number: str
    language: str


@router.post("/user/update-language")
async def update_user_language_endpoint(payload: UserUpdateLanguageRequest):
    success = update_user_language(
        phone_number=payload.phone_number,
        language=payload.language
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return {
        "success": True,
        "message": "Language updated successfully",
        "language": payload.language
    }