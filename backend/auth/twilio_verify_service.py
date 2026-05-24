from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

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
        return str(exc)
    return "Twilio Verify request failed"


def send_verification_otp(phone_number: str, channel: str = "sms") -> dict:
    """Send a Twilio Verify OTP to the requested phone number."""
    try:
        client = _get_twilio_client()
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
            "message": str(exc),
        }
    except Exception:
        return {
            "success": False,
            "message": "Unable to send OTP at this time",
        }


def verify_otp_code(phone_number: str, code: str) -> dict:
    """Verify the provided OTP code using Twilio Verify."""
    try:
        client = _get_twilio_client()
        verification_check = client.verify.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone_number,
            code=code,
        )

        if verification_check.status == "approved":
            return {
                "success": True,
                "message": "OTP verified",
            }

        return {
            "success": False,
            "message": "Invalid or expired OTP",
        }

    except TwilioRestException as exc:
        return {
            "success": False,
            "message": _extract_error_message(exc),
        }
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception:
        return {
            "success": False,
            "message": "OTP verification failed",
        }
