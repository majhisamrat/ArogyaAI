import logging

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from api.routes.chat import chat_endpoint
from api.schemas.chat_schema import ChatRequest
from whatsapp.message_parser import clean_whatsapp_text
from whatsapp.twilio_handler import TwilioService
from services.voice_service import get_voice_service

logger = logging.getLogger(__name__)

whatsapp_service = TwilioService()
voice_service = get_voice_service()


async def handle_whatsapp_webhook(request: Request) -> dict:
    """Handle the incoming Twilio WhatsApp webhook and forward it to the chatbot."""
    logger.info("🔍 WhatsApp webhook handler started")
    form_data = await request.form()
    params = dict(form_data)
    
    logger.info(f"📦 Received form data: {params}")

    # TEMPORARY: Skip signature validation for debugging
    # if not await whatsapp_service.validate_twilio_request(request, params=params):
    #     logger.warning("❌ Twilio signature validation failed")
    #     raise HTTPException(status_code=403, detail="Invalid Twilio request signature.")

    logger.info("✅ Signature validation skipped (DEBUG MODE)")

    raw_from = params.get("From")
    body = params.get("Body", "").strip()
    profile_name = params.get("ProfileName", "").strip()

    # ═══ CHECK FOR AUDIO MEDIA ═══
    num_media = params.get("NumMedia", "0")
    try:
        num_media_int = int(num_media)
    except (ValueError, TypeError):
        num_media_int = 0

    if num_media_int > 0:
        media_url = params.get("MediaUrl0")
        media_type = params.get("MediaContentType0", "")

        logger.info(f"📦 Audio media detected: {media_type}")

        # Transcribe if media is audio
        if media_type and media_type.startswith("audio/"):
            try:
                logger.info(f"🎤 Starting voice transcription...")
                transcribed_text = await voice_service.transcribe_whatsapp_audio(
                    media_url,
                    media_type,
                )

                if transcribed_text:
                    logger.info(f"✅ Voice transcription successful")
                    body = transcribed_text  # Replace body with transcription
                else:
                    logger.warning(
                        f"⚠️ Voice transcription failed, returning error"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Could not transcribe audio. Please try again.",
                    )

            except Exception as exc:
                logger.error(f"❌ Voice transcription error: {exc}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to transcribe audio message.",
                )

    logger.info(f"📱 From: {raw_from}, Body: {body}, Profile: {profile_name}")

    if not raw_from:
        raise HTTPException(status_code=400, detail="Missing From field in webhook payload.")
    if not body:
        raise HTTPException(status_code=400, detail="Empty message body or failed transcription.")

    phone_number = whatsapp_service.format_phone_number(raw_from)
    logger.info(f"📞 Normalized phone: {phone_number}")
    
    if not phone_number:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp phone number format.")

    chat_request = ChatRequest(
        phone_number=phone_number,
        message=body,
        history=[],
    )

    try:
        logger.info(f"🤖 Calling chat API for {phone_number}")
        chat_response = await chat_endpoint(chat_request)
        response_text = chat_response.response
        logger.info(f"✅ Chat response received: {response_text[:100]}...")
    except Exception as exc:
        logger.error(f"❌ Chat API call failed for {phone_number}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate chatbot response.")

    formatted_response = clean_whatsapp_text(response_text)

    try:
        logger.info(f"📤 Sending WhatsApp message to {raw_from}")
        message = await run_in_threadpool(
            whatsapp_service.send_whatsapp_message,
            raw_from,
            formatted_response,
        )
        logger.info(f"✅ WhatsApp message sent: {message.get('sid')}")
    except Exception as exc:
        logger.error(f"❌ Failed to send WhatsApp reply to {raw_from}: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to send WhatsApp response.")

    return {
        "status": "sent",
        "to": raw_from,
        "profile_name": profile_name,
        "sent_message_sid": message.get("sid"),
        "response": formatted_response,
    }
