from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from pydantic import BaseModel

from auth.otp_service import (
    send_verification_otp,
    verify_otp_code,
)

from ..auth.jwt_handler import (
    create_access_token
)
from database.login_manager import is_registered

router = APIRouter()


class SendOtpRequest(BaseModel):
    phone_number: str
    purpose: str = "login"  # "login" or "register"


class VerifyOtpRequest(BaseModel):

    phone_number: str

    otp: str


@router.post("/send-otp")
async def send_otp(payload: SendOtpRequest):

    if payload.purpose == "register":
        if is_registered(payload.phone_number):
            return {
                "success": False,
                "message": "Phone number is already registered"
            }
    else:  # default is "login"
        if not is_registered(payload.phone_number):
            return {
                "success": False,
                "message": "Phone number is not registered"
            }

    result = await run_in_threadpool(
        send_verification_otp,
        payload.phone_number,
    )

    return result


@router.post("/verify-otp")
async def verify_otp_route(
    payload: VerifyOtpRequest
):

    result = await run_in_threadpool(
        verify_otp_code,
        payload.phone_number,
        payload.otp,
    )

    if not result.get("success"):
        return {
            "success": False,
            "message": result.get("message", "Invalid OTP")
        }

    token = create_access_token({
        "phone_number": payload.phone_number
    })

    return {
        "success": True,
        "token": token
    }