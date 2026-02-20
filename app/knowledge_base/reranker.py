from typing import List
from langchain_core.documents import Document
from loguru import logger
from sentence_transformers import CrossEncoder

from app.config import settings

_default_reranker = None


class Reranker:
    """
    文档重排序（Rerank）模块
    使用 CrossEncoder 对 query-document 进行精排
    """

    def __init__(
            self,
            model_name: str = settings.RERANK_MODEL_PATH,
            top_n: int = 5
    ):
        """
        Args:
            model_name: rerank 模型名称
            top_n: rerank 后保留的文档数量
        """
        self.model_name = model_name
        self.top_n = top_n
        self._model = None

        self._load_model()

    def _load_model(self):
        """加载 rerank 模型"""
        try:
            self._model = CrossEncoder(
                self.model_name,
                device="cpu"
            )
            logger.info(f"Rerank 模型加载成功: {self.model_name}")
        except Exception as e:
            logger.error(f"Rerank 模型加载失败: {e}")
            raise

    def rerank(
            self,
            query: str,
            documents: List[Document],
    ) -> List[Document]:
        """
        对检索到的 Document 进行重排序（CrossEncoder）

        Args:
            query: 用户查询
            documents: LangChain Document 列表

        Returns:
            rerank 后的 Document 列表（按相关度降序）
        """

        if not documents:
            logger.warning("Rerank 输入文档为空")
            return []

        if not query:
            logger.warning("Rerank query 为空，跳过 rerank")
            return documents[: self.top_n]

        # 过滤空文本 Document，防止模型报错
        valid_docs: List[Document] = []
        for doc in documents:
            if isinstance(doc.page_content, str) and doc.page_content.strip():
                valid_docs.append(doc)
            else:
                logger.warning("发现 page_content 为空的 Document，已跳过")

        if not valid_docs:
            logger.warning("没有可用于 rerank 的有效文档")
            return []
        logger.info(f"开始 Rerank，共 {len(valid_docs)} 条候选文档")

        # 构造 (query, doc_text) 对
        pairs = [
            (query, doc.page_content)
            for doc in valid_docs
        ]

        try:
            scores = self._model.predict(pairs)
        except Exception as e:
            logger.error(f"Rerank 预测失败: {e}")
            return valid_docs[: self.top_n]

        # 将 rerank_score 写入 Document.metadata
        for doc, score in zip(valid_docs, scores):
            doc.metadata["rerank_score"] = float(score)

        # 按分数排序
        valid_docs.sort(
            key=lambda d: d.metadata.get("rerank_score", 0.0),
            reverse=True
        )

        reranked_docs = valid_docs[: self.top_n]

        logger.info(f"Rerank 完成，返回 Top-{len(reranked_docs)} 文档")

        return reranked_docs


def get_reranker(
        model_name: str = settings.RERANK_MODEL_PATH,
        top_n: int = 5
) -> Reranker:
    """
    获取全局唯一的 Reranker 实例（单例）

    Args:
        model_name: rerank 模型名称
        top_n: rerank 后保留的文档数量

    Returns:
        Reranker 实例
    """
    global _default_reranker

    if _default_reranker is None:
        logger.info("🔧 初始化全局 Reranker ...")
        _default_reranker = Reranker(
            model_name=model_name,
            top_n=top_n
        )

    return _default_reranker
