from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import health, v1
from loguru import logger
from app.db import init_db
import os

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        logger.info("🚀 正在启动流浪动物救助平台...")

        # 1. 检查基础配置
        from app.config import settings
        if not settings.LLM_API_KEY:
            logger.warning("⚠️ 未检测到 LLM_API_KEY，模型对话功能可能无法正常使用")
        
        # 2. 初始化数据库
        logger.info("📦 初始化数据库...")
        init_db()
        logger.info("✅ 数据库初始化成功")

        # 3. 检查/初始化向量数据库 (Qdrant)
        try:
            logger.info("🔍 检查向量数据库连接...")
            from app.knowledge_base.vector_store import get_vector_store
            # get_vector_store 会触发 QdrantHybridStore 的初始化和集合检查
            _ = get_vector_store()
            logger.info("✅ 向量数据库连接正常")
        except Exception as e:
            logger.error(f"❌ 向量数据库连接失败: {e}")
            # 本地使用时不强制退出，仅报错

        logger.info("✨ 应用启动成功，准备就绪")
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    
    yield

    # 关闭时：清理资源
    logger.info("⚰️ 关闭应用，清理资源...")


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
