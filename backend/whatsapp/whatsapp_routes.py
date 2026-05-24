import logging

from fastapi import APIRouter, Request

from whatsapp.webhook_handler import handle_whatsapp_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    logger.info("✅ WhatsApp webhook called")
    logger.info(f"Headers: {dict(request.headers)}")
    return await handle_whatsapp_webhook(request)
