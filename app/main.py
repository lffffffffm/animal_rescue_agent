from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
# from app.api import health, api_v1
from app.config import settings
from loguru import logger


logger.info("项目启动")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：创建数据库表
    logger.info("启动应用...")

    # 加载知识库（可以异步进行）
    logger.info("加载知识库...")

    yield

    # 关闭时：清理资源
    logger.info("关闭应用，清理资源...")


# 创建FastAPI应用
app = FastAPI(
    title="流浪动物救助智能问答平台",
    description="基于FastAPI的流浪动物救助智能问答系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# app.include_router(health.router, tags=["健康检查"])
# app.include_router(api_v1.router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "欢迎使用流浪动物救助智能问答平台",
        "docs": "/docs",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )