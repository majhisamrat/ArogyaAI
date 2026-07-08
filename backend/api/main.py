from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.chat import router as chat_router
from .routes.user import router as user_router
from .routes.health import router as health_router

from config.settings import CORS_ORIGINS, get_system_status
from database.models import init_db
from .routes.auth import router as auth_router
from .routes.conversation import router as conversation_router
from whatsapp.whatsapp_routes import router as whatsapp_router


# Init DB
init_db()


app = FastAPI(
    title="Rural Health Assistant API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)
app.include_router(
    conversation_router,
    prefix="/api"
)
app.include_router(
    whatsapp_router
)


@app.get("/")
async def root():

    return {
        "message": "Rural Health Assistant API Running"
    }


# ─────────────────────────────────────────────────────────────────────
# MONITORING ENDPOINTS (NEW)
# ─────────────────────────────────────────────────────────────────────
# These endpoints provide visibility into the high-concurrency system.

@app.get("/system/api-status")
async def get_api_status():
    """
    Get comprehensive status of Groq API keys and system health.
    
    Returns:
        {
            "app_name": "Rural Health Assistant",
            "app_version": "1.0.0",
            "async_client_enabled": true,
            "api_keys": {
                "keys": [
                    {
                        "name": "Key1",
                        "healthy": true,
                        "active_requests": 2,
                        "total_requests": 321,
                        "total_failures": 4,
                        "cooldown_until": 0.0,
                        "last_error": null
                    }
                ],
                "total_keys": 6,
                "healthy_keys": 5
            },
            "cache": {
                "status": "connected",
                "cached_responses": 1523
            }
        }
    """
    return get_system_status()


@app.get("/system/health")
async def system_health():
    """
    Simple health check endpoint.
    
    Returns:
        {"status": "healthy", "async_enabled": true}
    """
    status = get_system_status()
    is_healthy = status.get("async_client_enabled", False) and \
                 status.get("api_keys", {}).get("healthy_keys", 0) > 0
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "async_enabled": status.get("async_client_enabled", False),
        "healthy_keys": status.get("api_keys", {}).get("healthy_keys", 0),
        "total_keys": status.get("api_keys", {}).get("total_keys", 0),
    }