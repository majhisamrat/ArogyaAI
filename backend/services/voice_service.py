"""
Voice Service

Handles WhatsApp audio transcription using Faster-Whisper.
Downloads audio from Twilio, transcribes it to text while preserving language.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional
import logging

import requests
from faster_whisper import WhisperModel

from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from config.logger import logger

# GLOBAL WHISPER MODEL (loaded once on startup)

_whisper_model = None


def _get_whisper_model() -> WhisperModel:
    """
    Lazy-load Faster-Whisper model once globally.
    Model is cached in memory to avoid reloading on every request.
    """
    global _whisper_model
    if _whisper_model is None:
        logger.info("[VoiceService] Loading Faster-Whisper base model...")
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("[VoiceService] Faster-Whisper model loaded successfully")
    return _whisper_model


# VOICE SERVICE

class VoiceService:
    """Service for downloading and transcribing WhatsApp audio messages."""

    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.temp_dir = tempfile.gettempdir()

    def _get_twilio_auth(self) -> tuple:
        """Return Twilio Basic Auth credentials."""
        return (self.account_sid, self.auth_token)

    async def download_media(
        self,
        media_url: str,
        media_type: str,
    ) -> Optional[str]:
        """
        Download audio media from Twilio with authentication.

        Args:
            media_url: Full URL to Twilio media (from MediaUrl0)
            media_type: MIME type (e.g., "audio/ogg", "audio/opus", "audio/mpeg")

        Returns:
            Path to temporary audio file or None if download failed
        """
        try:
            logger.info(
                f"[VoiceService] Downloading audio from Twilio "
                f"(type={media_type})"
            )

            # Map MIME type to file extension
            extension_map = {
                "audio/ogg": ".ogg",
                "audio/opus": ".opus",
                "audio/mpeg": ".mp3",
                "audio/wav": ".wav",
                "audio/webm": ".webm",
            }

            extension = extension_map.get(media_type, ".ogg")

            # Download with Twilio authentication
            auth = self._get_twilio_auth()
            response = await asyncio.to_thread(
                requests.get,
                media_url,
                auth=auth,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    f"[VoiceService] Twilio media download failed: "
                    f"{response.status_code}"
                )
                return None

            # Save to temporary file
            temp_file = os.path.join(
                self.temp_dir,
                f"whatsapp_audio_{os.urandom(8).hex()}{extension}",
            )
            with open(temp_file, "wb") as f:
                f.write(response.content)

            logger.info(f"[VoiceService] Audio saved to: {temp_file}")
            return temp_file

        except Exception as e:
            logger.error(f"[VoiceService] Media download error: {e}")
            return None

    async def transcribe_audio(
        self,
        audio_file_path: str,
    ) -> Optional[str]:
        """
        Transcribe audio file to text using Faster-Whisper.

        Args:
            audio_file_path: Path to audio file

        Returns:
            Transcribed text or None if transcription failed
        """
        try:
            if not os.path.exists(audio_file_path):
                logger.error(
                    f"[VoiceService] Audio file not found: {audio_file_path}"
                )
                return None

            logger.info(f"[VoiceService] Starting transcription...")

            # Get globally loaded model
            model = _get_whisper_model()

            # Transcribe with task="transcribe" to preserve language
            segments, info = await asyncio.to_thread(
                model.transcribe,
                audio_file_path,
                task="transcribe",
                language=None,  # Auto-detect language
                beam_size=5,
            )

            # Combine all segments into single text
            transcribed_text = " ".join(
                segment.text.strip() for segment in segments
            )

            detected_language = info.language if info else "unknown"

            logger.info(
                f"[VoiceService] Transcription completed "
                f"(language={detected_language}, "
                f"confidence={info.language_probability if info else 'N/A'})"
            )
            logger.info(f"[VoiceService] Transcribed text: {transcribed_text[:100]}...")

            return transcribed_text

        except Exception as e:
            logger.error(f"[VoiceService] Transcription error: {e}")
            return None

    def cleanup_temp_file(self, file_path: str) -> None:
        """Remove temporary audio file."""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"[VoiceService] Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"[VoiceService] Failed to cleanup temp file: {e}")

    async def transcribe_whatsapp_audio(
        self,
        media_url: str,
        media_type: str,
    ) -> Optional[str]:
        """
        End-to-end transcription: download → transcribe → cleanup.

        Args:
            media_url: Twilio media URL
            media_type: MIME type of audio

        Returns:
            Transcribed text or None if any step failed
        """
        temp_file = None
        try:
            # Download audio
            temp_file = await self.download_media(media_url, media_type)
            if not temp_file:
                return None

            # Transcribe
            transcribed = await self.transcribe_audio(temp_file)
            return transcribed

        finally:
            # Always cleanup
            if temp_file:
                self.cleanup_temp_file(temp_file)

# SINGLETON INSTANCE

_voice_service = None


def get_voice_service() -> VoiceService:
    """Get or create a singleton VoiceService instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
