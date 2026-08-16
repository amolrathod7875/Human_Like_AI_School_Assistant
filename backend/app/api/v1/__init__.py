from app.api.v1 import ai, attendance, auth, avatar, escalation, health, voice
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(attendance.router, tags=["attendance"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(escalation.router, tags=["escalation"])
api_router.include_router(voice.router, tags=["voice"])
api_router.include_router(avatar.router, tags=["avatar"])
