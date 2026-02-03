from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from starlette.staticfiles import StaticFiles
from app.api import health, v1
from app.config import settings
from loguru import logger
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：创建数据库表
    logger.info("启动应用...")
    logger.info("初始化数据库...")
    init_db()
    yield

    # 关闭时：清理资源
    logger.info("关闭应用，清理资源...")


app = FastAPI(
    title="流浪动物救助智能问答平台",
    description="基于FastAPI的流浪动物救助智能问答系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
# 挂载静态文件：如果目录不存在则自动创建，避免启动报错
_base_dir = os.path.dirname(os.path.abspath(__file__))  # .../app
uploads_dir = os.path.join(_base_dir, "data", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static/uploads", StaticFiles(directory=uploads_dir), name="static_uploads")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(v1.api_router, prefix="", tags=["API接口"])


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
