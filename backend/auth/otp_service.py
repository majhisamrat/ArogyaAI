import re

from auth.twilio_verify_service import (
    send_verification_otp as _send_verification_otp,
    verify_otp_code as _verify_otp_code,
)


PHONE_NUMBER_PATTERN = re.compile(r"^\+?[0-9]{8,20}$")


def _normalize_phone_number(phone_number: str) -> str:
    return phone_number.strip()


def _is_valid_phone_number(phone_number: str) -> bool:
    if not phone_number or not isinstance(phone_number, str):
        return False

    normalized = _normalize_phone_number(phone_number)
    digits = re.sub(r"\D", "", normalized)

    return bool(digits) and len(digits) >= 8 and bool(PHONE_NUMBER_PATTERN.match(normalized))


def send_verification_otp(phone_number: str) -> dict:
    """Validate input and send OTP through Twilio Verify."""
    normalized_phone = _normalize_phone_number(phone_number)

    if not _is_valid_phone_number(normalized_phone):
        return {
            "success": False,
            "message": "Invalid phone number",
        }

    return _send_verification_otp(normalized_phone)


def verify_otp_code(phone_number: str, otp: str) -> dict:
    """Validate input and verify OTP through Twilio Verify."""
    normalized_phone = _normalize_phone_number(phone_number)
    code = otp.strip() if isinstance(otp, str) else ""

    if not _is_valid_phone_number(normalized_phone):
        return {
            "success": False,
            "message": "Invalid phone number",
        }

    if not code:
        return {
            "success": False,
            "message": "Invalid OTP",
        }

    return _verify_otp_code(normalized_phone, code)
