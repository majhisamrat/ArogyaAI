from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import router as chat_router
from api.routes.user import router as user_router
from api.routes.health import router as health_router

from config.settings import CORS_ORIGINS
from database.models import init_db
from api.routes.auth import router as auth_router
from api.routes.conversation import router as conversation_router
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