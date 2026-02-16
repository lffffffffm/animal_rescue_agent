from sqlalchemy.orm import Session, joinedload
from loguru import logger

from app.db.base import SessionLocal
from app.db.knowledge_model import Document, Chunk  # 导入数据模型
from app.knowledge_base.vector_store import get_vector_store


def sync_mysql_to_qdrant(recreate: bool = False):
    """
    将 MySQL 中的 608 篇文章及其片段同步到 Qdrant
    :param recreate: 是否清空旧的 Qdrant 集合重新创建
    """
    db: Session = SessionLocal()

    try:
        # 1. 获取 store 实例
        store = get_vector_store(collection_name="animal_rescue_collection", recreate=recreate)

        # 2. 一次性从 MySQL 查出所有数据 (668篇约4000条Chunk)
        logger.info("正在从 MySQL 读取全量数据...")
        chunks = db.query(Chunk).options(joinedload(Chunk.document)).all()

        if not chunks:
            logger.warning("MySQL 中没有数据，请先运行爬虫。")
            return

        # 3. 直接把整列表丢进去，让 vector_store 自己去分批 Embedding
        logger.info(f"🚀 发送 {len(chunks)} 条数据至向量库处理管道...")

        store.add_documents(chunks)

        logger.success("🎉 知识库全量同步指令已完成！")

    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
    finally:
        db.close()


# if __name__ == "__main__":
#     import os
#
#     os.environ["NO_PROXY"] = "127.0.0.1,localhost"
#     os.environ["no_proxy"] = "127.0.0.1,localhost"
#
#     # 第一次运行建议设为 True，以确保维度(512)和索引完全正确
#     sync_mysql_to_qdrant(recreate=True)
