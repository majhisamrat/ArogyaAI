import logging

import phonenumbers
from fastapi import Request
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER,
)

logger = logging.getLogger(__name__)


class TwilioService:
    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.whatsapp_number = TWILIO_WHATSAPP_NUMBER
        self.client = None

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)

    async def validate_twilio_request(
        self,
        request: Request,
        params: dict | None = None,
    ) -> bool:
        """Validate incoming Twilio webhook requests."""
        if not self.auth_token:
            logger.warning("Twilio auth token is not configured.")
            return False

        signature = request.headers.get("X-Twilio-Signature")
        if not signature:
            logger.warning("Missing Twilio signature header.")
            return False

        if params is None:
            params = dict(await request.form())

        validator = RequestValidator(self.auth_token)
        try:
            return validator.validate(str(request.url), params, signature)
        except Exception as exc:
            logger.error(f"Twilio request validation failed: {exc}")
            return False

    def format_phone_number(self, raw_number: str) -> str:
        """Normalize the WhatsApp incoming sender to plain E.164 format."""
        if not raw_number:
            return ""

        normalized = raw_number.strip()
        if normalized.lower().startswith("whatsapp:"):
            normalized = normalized.split(":", 1)[1]

        try:
            parsed = phonenumbers.parse(normalized, None)
            if not phonenumbers.is_valid_number(parsed):
                return ""
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164,
            )
        except Exception:
            return normalized if normalized.startswith("+") else ""

    def _format_whatsapp_number(self, raw_number: str) -> str:
        """Convert a phone number into a Twilio WhatsApp address."""
        normalized = raw_number.strip()
        if normalized.lower().startswith("whatsapp:"):
            normalized = normalized.split(":", 1)[1]
        return f"whatsapp:{normalized}"

    def send_whatsapp_message(self, to_number: str, body: str) -> dict:
        """Send a WhatsApp message through Twilio."""
        if not self.client:
            raise RuntimeError("Twilio client is not configured.")

        if not self.whatsapp_number:
            raise RuntimeError("TWILIO_WHATSAPP_NUMBER is not configured.")

        to_whatsapp = self._format_whatsapp_number(to_number)
        try:
            message = self.client.messages.create(
                body=body,
                from_=self.whatsapp_number,
                to=to_whatsapp,
            )
            return {
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "body": message.body,
            }
        except TwilioRestException as exc:
            logger.error(f"Twilio send message failed: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected Twilio error: {exc}")
            raise
