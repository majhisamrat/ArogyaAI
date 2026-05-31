# Arogya AI Server Changes Log

This document records the exact changes made to the `ArogyaAI-server` codebase. These changes facilitate country-wide Indian footprint expansions, enable 11-language classification, implement a mock fallback for verification checks, and support user profile language synchronizations.

---

## 1. Supported Languages Expansion
### File modified: [backend/config/settings.py](file:///d:/projects/arogya/ArogyaAI-server/backend/config/settings.py)
* **Change**: Added `"od": "Odia"` to the `SUPPORTED_LANGUAGES` map to explicitly support Odia alongside the existing ten Indian languages.
* **Result**: `SUPPORTED_LANGUAGES` now holds 11 supported languages: English (`en`), Hindi (`hi`), Odia (`od`), Bengali (`bn`), Tamil (`ta`), Telugu (`te`), Marathi (`mr`), Gujarati (`gu`), Kannada (`kn`), Malayalam (`ml`), and Punjabi (`pa`).

---

## 2. Multi-Agent Language Tool Expansion
### File modified: [backend/tools/language_tool.py](file:///d:/projects/arogya/ArogyaAI-server/backend/tools/language_tool.py)
* **Change**: Updated the system prompt inside the LLM language/style analyzer `analyze_language_style()` to support all 11 language codes, adding Odia and other regional codes as options.
* **Change**: Programmatically populated the `allowed_languages` list using the key set of the central configurations: `allowed_languages = list(SUPPORTED_LANGUAGES.keys())`. This ensures newly detected languages are processed instead of defaulting directly to English.

---

## 3. Database Language Sync Helper
### File modified: [backend/database/login_manager.py](file:///d:/projects/arogya/ArogyaAI-server/backend/database/login_manager.py)
* **Change**: Implemented the helper function `update_user_language(phone_number: str, language: str) -> bool` to write a user's updated preferred language directly to the `User` table inside SQLite.
* **Result**: Allows the database to save preferred languages dynamically. Future chat sessions and WhatsApp interactions for the user automatically load the correct regional preference.

---

## 4. Sync Language API Route
### File modified: [backend/api/routes/user.py](file:///d:/projects/arogya/ArogyaAI-server/backend/api/routes/user.py)
* **Change**: Added a Pydantic payload schema `UserUpdateLanguageRequest` containing `phone_number` and `language`.
* **Change**: Implemented a POST route `/api/user/update-language` calling the database update handler.
* **Result**: Allows the frontend to sync any navbar language selections instantly with the backend SQLite user profiles.

---

## 5. Development Verification Fallback
### File modified: [backend/auth/twilio_verify_service.py](file:///d:/projects/arogya/ArogyaAI-server/backend/auth/twilio_verify_service.py)
* **Change**: Added development mock fallbacks in both `send_verification_otp()` and `verify_otp_code()`. If the Twilio credentials are not active or raise a ValueError, print/log the OTP code `123456` in the console and allow the check to pass.
* **Result**: Allows developers to register and test the mobile/OTP onboarding flows out-of-the-box without requiring live Twilio endpoints.

---

## 6. Local Development Database Configuration
### File modified: [.env](file:///d:/projects/arogya/ArogyaAI-server/.env)
* **Change**: Changed `DATABASE_URL` from the Docker-specific container path `sqlite:////app/storage/health_db.sqlite` to the local development relative SQLite path `sqlite:///backend/data/health_db.sqlite`.
* **Result**: Resolves `sqlite3.OperationalError: unable to open database file` when running the FastAPI backend locally outside a Docker container, successfully linking the server to the pre-existing seed database at `backend/data/health_db.sqlite`.

---

## 7. Unified WhatsApp & Web SQLite History Sync
### File modified: [backend/orchestrator/langgraph_coordinator.py](file:///d:/projects/arogya/ArogyaAI-server/backend/orchestrator/langgraph_coordinator.py)
* **Change**: Added auto-resolution for `conversation_id` inside `handle_message()`. When incoming WhatsApp messages arrive (where `conversation_id` is `None`), retrieve the user's latest active conversation ID from SQLite, or create a new session if none exists.
* **Result**: WhatsApp messages and responses are now persisted directly to SQLite alongside standard Web portal sessions, unifying chat histories across mobile and web platforms.

---

## 8. SQLite Conversation Deletion & cascade messages prune
### File modified: [backend/database/conversation_manager.py](file:///d:/projects/arogya/ArogyaAI-server/backend/database/conversation_manager.py)
* **Change**: Added `delete_conversation(conversation_id)` which queries the `conversations` SQLite table and deletes the session. Message foreign key cascades automatically clean up message history rows.
### File modified: [backend/api/routes/conversation.py](file:///d:/projects/arogya/ArogyaAI-server/backend/api/routes/conversation.py)
* **Change**: Exposed `DELETE /api/conversation/{conversation_id}`.
* **Result**: Allows the Next.js frontend to cleanly purge sessions and remove clutter (like unused or empty chats) directly from SQLite.


server start commmand : uvicorn api.main:app --reload --port 8000