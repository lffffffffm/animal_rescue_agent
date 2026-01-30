from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


def get_db():
    """
    FastAPI DB Session 依赖
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库（仅在开发 / 脚本中调用）
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.success("数据库表初始化完成")
    except Exception as e:
        logger.exception("数据库初始化失败")
        raise
