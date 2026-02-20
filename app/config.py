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
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    EMBEDDING_OFFLINE: bool = os.getenv("EMBEDDING_OFFLINE", "true").lower() == "true"
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "")

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")

    # Qdrant 配置
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "animal_rescue_collection")

    # 稀疏嵌入模型配置
    SPARSE_EMBEDDING_MODEL: str = os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25")
    SPARSE_EMBEDDING_CACHE_DIR: str = os.getenv("SPARSE_EMBEDDING_CACHE_DIR", "./models")
    SPARSE_EMBEDDING_LOCAL_ONLY: bool = os.getenv("SPARSE_EMBEDDING_LOCAL_ONLY", "True").lower() == "true"

    # 知识库配置
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge_base")

    # 地图相关配置
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", None)

    # 爬虫相关配置
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", None)

    # 知识库配置
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "")

    # API配置
    API_V1_STR: str = "/api/v1"

    # 检索配置
    RETRIEVAL_TOP_K: int = 15
    SIMILARITY_THRESHOLD: float = 0.6

    MAX_RETRY: int = 2  # 最大重试次数
    MIN_DOCS_REQUIRED: int = 5  # 至少需要的文档数量

    # rerank相关配置
    RERANK_TOP_K: int = 5
    MIN_RERANK_SCORE: float = 0.55
    RERANK_MODEL_PATH: str = os.getenv("RERANK_MODEL_PATH", "")

    # 认证配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10000"))

    # Vision
    VISION_BASE_URL: str = os.getenv("VISION_BASE_URL", "")
    VISION_API_KEY: str = os.getenv("VISION_API_KEY", "")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "")
    VISION_TIMEOUT_SEC: int = int(os.getenv("VISION_TIMEOUT_SEC", "30"))

    # COS配置
    COS_BASE_URL: str = os.getenv("COS_BASE_URL", "")
    COS_SECRET_ID: str = os.getenv("COS_SECRET_ID", "")
    COS_SECRET_KEY: str = os.getenv("COS_SECRET_KEY", "")
    COS_REGION: str = os.getenv("COS_REGION", "")
    COS_BUCKET: str = os.getenv("COS_BUCKET", "")
    # WebSearch 配置
    WEB_SEARCH_MAX_RESULTS: int = 8

    class Config:
        env_file = ".env"


settings = Settings()
