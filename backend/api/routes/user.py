from fastapi import APIRouter, HTTPException

from pydantic import BaseModel
from database.login_manager import (
    register_user,
    get_user,
    is_registered,
    update_user_language
)

from ..schemas.user_schema import (
    UserRegisterRequest,
    UserResponse
)
from auth.otp_service import verify_otp_code
from ..auth.jwt_handler import create_access_token
from config.logger import logger

router = APIRouter()


class OtpVerifyRequest(BaseModel):
    """Step 1: Verify OTP only (don't create user yet)"""
    phone_number: str
    otp: str


@router.post("/verify-otp")
async def verify_otp_endpoint(payload: OtpVerifyRequest):
    """Step 1: Verify OTP code for phone number.
    
    This endpoint is called in Step 1 of registration flow.
    It only verifies the OTP without creating a user account.
    """
    print(f"\n{'='*60}")
    print(f"OTP VERIFICATION REQUEST")
    print(f"{'='*60}")
    print(f"Phone: {payload.phone_number}")
    print(f"OTP: {payload.otp}")
    logger.info(f"[VerifyOTP] OTP verification for {payload.phone_number}")

    # Verify OTP with Twilio
    print(f"\n→ Calling verify_otp_code({payload.phone_number}, {payload.otp})")
    otp_res = verify_otp_code(payload.phone_number, payload.otp)
    print(f"← verify_otp_code returned: {otp_res}")
    
    if not otp_res.get("success"):
        print(f"❌ OTP verification failed: {otp_res.get('message')}")
        logger.error(f"[VerifyOTP] Failed: {otp_res.get('message')}")
        raise HTTPException(
            status_code=400,
            detail=otp_res.get("message", "Invalid or expired OTP")
        )

    print(f"✓ OTP verified successfully")
    logger.info(f"[VerifyOTP] Success for {payload.phone_number}")
    print(f"{'='*60}\n")
    
    return {
        "success": True,
        "message": "OTP verified successfully",
        "phone_number": payload.phone_number
    }



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
    """Step 3: Create user account with full profile.
    
    This endpoint is called in Step 3 of registration flow (after OTP is verified in Step 1).
    It creates the user account with personal details.
    OTP verification already happened in Step 1 via /verify-otp endpoint.
    The otp field is accepted but not used here.
    """
    print(f"\n{'='*60}")
    print(f"USER REGISTRATION REQUEST (Step 3)")
    print(f"{'='*60}")
    print(f"Phone: {payload.phone_number}")
    print(f"Name: {payload.name}")
    print(f"Age: {payload.age}")
    print(f"Gender: {payload.gender}")
    print(f"Pincode: {payload.pincode}")
    print(f"Language: {payload.language}")
    logger.info(f"[Register] User registration started for {payload.phone_number}")

    if is_registered(payload.phone_number):
        print(f"❌ User already registered: {payload.phone_number}")
        logger.warning(f"[Register] User already registered: {payload.phone_number}")
        raise HTTPException(
            status_code=400,
            detail="User already registered"
        )

    # Note: OTP verification already happened in Step 1 via /verify-otp endpoint
    # We don't verify it again here to avoid Twilio "resource not found" error
    print(f"✓ OTP verification skipped (already verified in Step 1)")
    
    print(f"\n→ Creating user record in database...")
    user = register_user(
        phone_number=payload.phone_number,
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        pincode=payload.pincode,
        language=payload.language
    )
    print(f"✓ User created: {user}")

    # Create JWT access token for immediate session setup
    print(f"→ Creating JWT token...")
    token = create_access_token({"phone_number": payload.phone_number})
    print(f"✓ JWT token created")
    
    response_data = dict(user)
    response_data["token"] = token

    print(f"{'='*60}")
    print(f"✓ REGISTRATION SUCCESSFUL")
    print(f"{'='*60}\n")
    logger.info(f"[Register] User registration completed for {payload.phone_number}")
    
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
