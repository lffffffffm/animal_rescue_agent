"""
健康检查路由
"""
from fastapi import APIRouter
from datetime import datetime
from app.api.schemas import HealthStatusResponse

router = APIRouter()


@router.get("/health", response_model=HealthStatusResponse)
async def health_check():
    """
    健康检查端点
    """
    return HealthStatusResponse(
        status="healthy",
        service="animal_rescue_agent_api",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )
