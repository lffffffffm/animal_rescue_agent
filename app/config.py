import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "动物救助平台"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # LLM 配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")

    # 向量数据库配置
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/vectors")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

    # Qdrant 配置
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "animal_rescue_collection")

    # 地图相关配置
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", None)

    # 爬虫相关配置
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", None)

    # 知识库配置
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge")

    # API配置
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # 检索配置
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.6

    # Judge相关配置
    MAX_RETRY: int = 2  # 最大重试次数
    MIN_EVIDENCE_CONFIDENCE: float = 0.6
    MIN_DOCS_REQUIRED: int = 6  # 至少需要的文档数量
    MIN_RERANK_SCORE: float = 0.25  # rerank 相关性阈值（经验值）

    class Config:
        env_file = ".env"


settings = Settings()
