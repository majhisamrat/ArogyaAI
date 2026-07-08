import re

from auth.twilio_verify_service import (
    send_verification_otp as _send_verification_otp,
    verify_otp_code as _verify_otp_code,
)


PHONE_NUMBER_PATTERN = re.compile(r"^\+?[0-9]{8,20}$")

# Default to India (+91) - change this if most users are from a different country
DEFAULT_COUNTRY_CODE = "+91"


def _normalize_phone_number(phone_number: str) -> str:
    """Convert phone number to E.164 format required by Twilio Verify.
    
    Examples:
    - "9162913247" → "+919162913247" (India)
    - "+919162913247" → "+919162913247" (already formatted)
    - "14155552671" → "+114155552671" (USA)
    """
    phone = phone_number.strip()
    
    # If already starts with +, assume it's in E.164 format
    if phone.startswith("+"):
        return phone
    
    # Remove any non-digit characters
    digits_only = re.sub(r"\D", "", phone)
    
    # If 10 digits (India), prepend +91
    if len(digits_only) == 10:
        return f"{DEFAULT_COUNTRY_CODE}{digits_only}"
    
    # If already has country code prefix (usually 1-3 digits), prepend +
    if digits_only and len(digits_only) >= 8:
        return f"+{digits_only}"
    
    # Fallback - just prepend default country code
    return f"{DEFAULT_COUNTRY_CODE}{digits_only}" if digits_only else phone


def _is_valid_phone_number(phone_number: str) -> bool:
    if not phone_number or not isinstance(phone_number, str):
        return False

    normalized = _normalize_phone_number(phone_number)
    digits = re.sub(r"\D", "", normalized)

    return bool(digits) and len(digits) >= 8 and bool(PHONE_NUMBER_PATTERN.match(normalized))


def send_verification_otp(phone_number: str) -> dict:
    """Validate input and send OTP through Twilio Verify."""
    print(f"\n[OTP Service] send_verification_otp called")
    print(f"  Input: {phone_number}")
    normalized_phone = _normalize_phone_number(phone_number)
    print(f"  Normalized to E.164: {normalized_phone}")

    if not _is_valid_phone_number(normalized_phone):
        print(f"  ✗ Invalid phone number format")
        return {
            "success": False,
            "message": "Invalid phone number",
        }

    print(f"  ✓ Phone number valid, calling Twilio...")
    return _send_verification_otp(normalized_phone)


def verify_otp_code(phone_number: str, otp: str) -> dict:
    """Validate input and verify OTP through Twilio Verify."""
    print(f"\n[OTP Service] verify_otp_code called")
    print(f"  Input phone: {phone_number}")
    print(f"  Input OTP: {otp}")
    normalized_phone = _normalize_phone_number(phone_number)
    print(f"  Normalized to E.164: {normalized_phone}")
    code = otp.strip() if isinstance(otp, str) else ""

    if not _is_valid_phone_number(normalized_phone):
        print(f"  ✗ Invalid phone number format")
        return {
            "success": False,
            "message": "Invalid phone number",
        }

    if not code:
        print(f"  ✗ Empty OTP code")
        return {
            "success": False,
            "message": "Invalid OTP",
        }

    print(f"  ✓ Inputs valid, calling Twilio verification check...")
    return _verify_otp_code(normalized_phone, code)
