from loguru import logger
from typing import List
from langchain_core.documents import Document
from app.config import settings
from app.knowledge_base.reranker import get_reranker
from app.knowledge_base.vector_store import get_vector_store


class HybridRetriever:
    """
    基于 Qdrant 原生 Hybrid 的检索器
    """

    def __init__(
            self,
            collection_name: str = "animal_rescue_collection",
            top_k: int = 5,
    ):
        self.collection_name = collection_name
        self.top_k = top_k
        self.reranker = get_reranker(top_n=top_k)
        self.vector_store = get_vector_store(collection_name)

    def retrieve(self, query: str, species: str = None) -> List[Document]:
        logger.info(f"Hybrid 检索查询: {query}")

        base_retriever = self.vector_store.get_retriever(
            k=15,
            species=species
        )
        # 获取粗排结果
        initial_docs = base_retriever.invoke(query)
        if not initial_docs:
            return []

        final_docs = self.reranker.rerank(query, initial_docs)

        return final_docs


_retriever_cache: dict[int, HybridRetriever] = {}


# 未来可以扩展不同name的collection
def get_retriever(top_k: int | None = None) -> HybridRetriever:
    """
    根据 top_k 获取（或复用）HybridRetriever
    """
    global _retriever_cache

    top_k = top_k or settings.RETRIEVAL_TOP_K

    if top_k not in _retriever_cache:
        _retriever_cache[top_k] = HybridRetriever(top_k=top_k)

    return _retriever_cache[top_k]
