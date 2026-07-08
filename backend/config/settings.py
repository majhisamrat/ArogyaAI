import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from config.logger import logger

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent

# Load .env 
dotenv_path = Path('.env')
if not dotenv_path.exists():
    dotenv_path = WORKSPACE_ROOT / '.env'
load_dotenv(dotenv_path=dotenv_path)

# ── Groq ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Two models strategy
GROQ_MAIN_MODEL  = "llama-3.3-70b-versatile"   # Symptom, Education, Outbreak
GROQ_FAST_MODEL  = "llama-3.1-8b-instant"       # Language detection, simple replies

# Groq client (legacy fallback - new code uses async client)
groq_client = Groq(api_key=GROQ_API_KEY)


try:
    from services.groq_client import get_async_groq_client
    async_groq_client = None  # Lazy initialized on first use
    USE_ASYNC_CLIENT = True
except ImportError:
    USE_ASYNC_CLIENT = False
    logger.warning("[Settings] Async Groq client not available, using legacy client")

# ── Twilio ────────────────────────────────────────────
TWILIO_ACCOUNT_SID         = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN          = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER     = os.getenv("TWILIO_WHATSAPP_NUMBER")  # whatsapp:+14155238886
TWILIO_VERIFY_SERVICE_SID  = os.getenv("TWILIO_VERIFY_SERVICE_SID")

# Database 
raw_database_url = os.getenv("DATABASE_URL", "sqlite:///backend/data/health_db.sqlite")
if raw_database_url.startswith("sqlite:///./"):
    DATABASE_URL = f"sqlite:///{WORKSPACE_ROOT / raw_database_url[10:]}"
elif raw_database_url.startswith("sqlite:///") and "./" not in raw_database_url:
    relative_path = raw_database_url.replace("sqlite:///", "")
    DATABASE_URL = f"sqlite:///{WORKSPACE_ROOT / relative_path}"
else:
    DATABASE_URL = raw_database_url

#  Redis / Session Memory 
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Mem0 Long-Term Memory 
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# CORS Origins
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

# App Settings 
APP_NAME        = "Rural Health Assistant"
APP_VERSION     = "1.0.0"
DEBUG           = os.getenv("DEBUG", "False").lower() == "true"

# Temperature settings per agent
TEMP_SYMPTOM    = 0.3   # Low  → more accurate medical advice
TEMP_EDUCATION  = 0.7   # Mid  → natural teaching tone
TEMP_OUTBREAK   = 0.2   # Very low → factual outbreak alerts
TEMP_LANGUAGE   = 0.1   # Very low → precise language detection

# Max tokens per agent
MAX_TOKENS_SYMPTOM   = 1024
MAX_TOKENS_EDUCATION = 1024
MAX_TOKENS_OUTBREAK  = 512
MAX_TOKENS_LANGUAGE  = 256

#  Outbreak Settings 
OUTBREAK_THRESHOLD      = 5    # 5+ same symptoms in same pincode
OUTBREAK_WINDOW_DAYS    = 7    # within 7 days = outbreak alert

# Supported Languages 
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "od": "Odia",
}

# LLM Response Functions
# These functions support both sync and async patterns
# Automatically uses the high-concurrency async client if available

async def _get_llm_response_async(
    messages: list,
    model: str = GROQ_MAIN_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str:
    """
    Async implementation of LLM response (UPGRADED).
    Uses high-concurrency async client with:
    - Multiple API key load balancing
    - Redis response caching
    - Automatic retry with cooldown
    - Health checking per key
    
    Args:
        messages: List of message dicts with "role" and "content"
        model: Groq model name
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum response tokens
        
    Returns:
        LLM response string
    """
    global async_groq_client
    if async_groq_client is None:
        async_groq_client = get_async_groq_client(REDIS_URL)
    
    try:
        response = await async_groq_client.chat_completions_create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=True,
        )
        return response
    except Exception as e:
        logger.error(f"[Settings] Async LLM error: {str(e)}")
        return f"Error: {str(e)}"


def get_llm_response(
    messages: list,
    model: str = GROQ_MAIN_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str:
    """
    UPGRADED: Synchronous wrapper for async LLM calls.
    
    This function maintains backward compatibility with all existing code
    while using the new high-concurrency async client internally.
    
    Supports:
    - Multiple Groq API keys (GROQ_API_KEY_1 to GROQ_API_KEY_6)
    - Automatic load balancing across keys
    - Redis response caching (24-hour TTL)
    - Automatic retry with cooldown on failures
    - Health checking and recovery
    
    Falls back to legacy client if async client unavailable or in async context.
    
    Args:
        messages: List of message dicts with "role" and "content"
                Format: [{"role": "system/user/assistant", "content": "..."}]
        model: Groq model name (default: llama-3.3-70b-versatile)
        temperature: Sampling temperature (0.0-2.0, default: 0.5)
        max_tokens: Maximum response tokens (default: 1024)
        
    Returns:
        LLM response string (or error message if request fails)
    """
    try:
        # Check if we're already in an async event loop
        try:
            asyncio.get_running_loop()
            # We're in an async context - use legacy client to avoid event loop conflicts
            in_async_context = True
        except RuntimeError:
            # No running loop, we can use the async client
            in_async_context = False
        
        # Use async client if available and we're not in async context
        if USE_ASYNC_CLIENT and not in_async_context:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    _get_llm_response_async(
                        messages,
                        model,
                        temperature,
                        max_tokens,
                    )
                )
                return response
            finally:
                loop.close()
        else:
            # Fallback to legacy client if async not available or in async context
            if in_async_context and USE_ASYNC_CLIENT:
                logger.debug("[Settings] In async context, using legacy client for compatibility")
            elif not USE_ASYNC_CLIENT:
                logger.warning("[Settings] Using legacy Groq client (async not available)")
            
            response = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
            
    except Exception as e:
        logger.error(f"[Settings] LLM request failed: {str(e)}")
        return f"Error: {str(e)}"


#  Validate on startup 
def validate_env():
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_VERIFY_SERVICE_SID:
        missing.append("TWILIO_VERIFY_SERVICE_SID")
    if missing:
        print(f"[Warning] Missing env variables: {', '.join(missing)}")
    else:
        print("All environment variables loaded successfully!")
    
    # Check for multi-key setup
    if USE_ASYNC_CLIENT:
        from services.api_key_manager import get_api_key_manager
        manager = get_api_key_manager()
        num_keys = len(manager.get_all_keys())
        if num_keys > 1:
            print(f"✓ High-concurrency Groq support enabled ({num_keys} API keys loaded)")
        elif num_keys == 1:
            print("✓ Single Groq API key loaded (no multi-key load balancing)")
        else:
            print("[Warning] No Groq API keys found! LLM calls will fail.")

validate_env()


# System Status Functions (for monitoring)
def get_system_status():
    """
    Get comprehensive system status including API key health.
    
    Returns:
        Dict with system metrics
    """
    status = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "async_client_enabled": USE_ASYNC_CLIENT,
    }
    
    if USE_ASYNC_CLIENT:
        try:
            global async_groq_client
            if async_groq_client is None:
                async_groq_client = get_async_groq_client(REDIS_URL)
            status.update(async_groq_client.get_status())
        except Exception as e:
            logger.error(f"[Settings] Error getting system status: {e}")
            status["error"] = str(e)
    
    return status