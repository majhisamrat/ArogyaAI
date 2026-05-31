import os
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

# Groq client 
groq_client = Groq(api_key=GROQ_API_KEY)

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

# Helper: get LLM response 
def get_llm_response(
    messages: list,
    model: str = GROQ_MAIN_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str:
    """
    Shared function to call Groq API.
    messages format: [{"role": "system/user/assistant", "content": "..."}]
    """
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
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
        print(f"⚠️  Missing env variables: {', '.join(missing)}")
    else:
        print("✅ All environment variables loaded successfully!")

validate_env()