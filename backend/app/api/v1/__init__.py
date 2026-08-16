from app.api.v1 import attendance, auth, health
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(attendance.router, tags=["attendance"])
