from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from config.logger import logger

from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_VERIFY_SERVICE_SID,
)


def _get_twilio_client() -> Client:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_SID:
        raise ValueError("Twilio Verify configuration is incomplete")

    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def _extract_error_message(exc: Exception) -> str:
    if isinstance(exc, TwilioRestException):
        if exc.code == 21608:
            return "Twilio Trial Limit: The phone number is unverified. Please add it to Verified Caller IDs in your Twilio Console."
        if hasattr(exc, "msg") and exc.msg:
            return exc.msg
        return str(exc)
    return "Twilio Verify request failed"


def send_verification_otp(phone_number: str, channel: str = "sms") -> dict:
    """Send a Twilio Verify OTP to the requested phone number."""
    try:
        print(f"\n=== TWILIO SEND OTP START ===")
        print(f"Phone (from frontend): {phone_number}")
        print(f"Phone (type): {type(phone_number)}")
        print(f"Phone (repr): {repr(phone_number)}")
        print(f"Phone (length): {len(phone_number)}")
        print(f"Channel: {channel}")
        print(f"Service SID: {TWILIO_VERIFY_SERVICE_SID}")
        
        client = _get_twilio_client()
        print(f"✓ Twilio client created")
        
        print(f"\nAttempting verifications.create() with:")
        print(f"  to={repr(phone_number)}")
        print(f"  channel={channel}")
        verification = client.verify.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone_number,
            channel=channel,
        )

        if verification.status in ("pending", "approved"):
            return {
                "success": True,
                "message": "OTP sent",
            }

        return {
            "success": False,
            "message": f"Failed to send OTP. Status: {verification.status}",
        }

    except TwilioRestException as exc:
        return {
            "success": False,
            "message": _extract_error_message(exc),
        }
    except ValueError as exc:
        return {
            "success": False,
            "message": f"Twilio configuration error: {str(exc)}",
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Failed to send OTP: {str(exc)}",
        }


def verify_otp_code(phone_number: str, code: str) -> dict:
    """Verify the provided OTP code using Twilio Verify."""
    try:
        print(f"\n=== TWILIO OTP VERIFICATION START ===")
        print(f"Phone (from frontend): {phone_number}")
        print(f"Phone (type): {type(phone_number)}")
        print(f"Phone (repr): {repr(phone_number)}")
        print(f"Phone (length): {len(phone_number)}")
        print(f"Code: {code}")
        print(f"Code (type): {type(code)}")
        print(f"Service SID: {TWILIO_VERIFY_SERVICE_SID}")
        
        logger.info(f"[Twilio] Verifying OTP for {phone_number} with service {TWILIO_VERIFY_SERVICE_SID}")
        client = _get_twilio_client()
        print(f"✓ Twilio client created")
        
        print(f"\nAttempting verification_checks.create() with:")
        print(f"  to={repr(phone_number)}")
        print(f"  code={repr(code)}")
        verification_check = client.verify.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone_number,
            code=code,
        )
        print(f"✓ Verification check response: {verification_check}")

        if verification_check.status == "approved":
            print(f"✓ OTP verification APPROVED")
            logger.info(f"[Twilio] OTP verification succeeded for {phone_number}")
            return {
                "success": True,
                "message": "OTP verified",
            }

        print(f"✗ OTP verification FAILED: status={verification_check.status}")
        logger.warning(f"[Twilio] OTP verification failed for {phone_number}: status={verification_check.status}")
        return {
            "success": False,
            "message": "Invalid or expired OTP",
        }

    except TwilioRestException as exc:
        print(f"\n❌ TWILIO REST EXCEPTION ❌")
        print(f"Error Code: {exc.code}")
        print(f"Error Message: {exc.msg}")
        print(f"Full Error: {str(exc)}")
        logger.error(f"[Twilio] Error code {exc.code}: {exc.msg}")
        logger.error(f"[Twilio] Full error response: {str(exc)}")
        return {
            "success": False,
            "message": _extract_error_message(exc),
        }
    except ValueError as exc:
        print(f"\n❌ CONFIGURATION ERROR ❌")
        print(f"Error: {str(exc)}")
        logger.error(f"[Twilio] Configuration error: {str(exc)}")
        return {
            "success": False,
            "message": f"Twilio configuration error: {str(exc)}",
        }
    except Exception as exc:
        print(f"\n❌ UNEXPECTED ERROR ❌")
        print(f"Error Type: {type(exc).__name__}")
        print(f"Error: {str(exc)}")
        logger.error(f"[Twilio] Unexpected error during verification: {str(exc)}")
        return {
            "success": False,
            "message": f"OTP verification failed: {str(exc)}",
        }

