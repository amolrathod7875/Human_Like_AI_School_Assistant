from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.responses import ApiResponse, success_response


class HealthData(BaseModel):
    service: str
    status: str


router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check() -> ApiResponse[HealthData]:
    return success_response(
        HealthData(service=settings.SERVICE_NAME, status="healthy")
    )
