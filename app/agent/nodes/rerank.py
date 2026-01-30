from typing import List
from loguru import logger
from langchain_core.documents import Document
from app.agent.state import AgentState
from app.config import settings
from app.knowledge_base.reranker import get_reranker


def rerank_documents(state: AgentState) -> AgentState:
    """
    Rerank 节点：对检索到的 Document 进行精排
    """

    query: str = state.get("rewrite_query") or state.get("query")
    docs: List[Document] = state.get("kb_docs", [])
    retry_count: int = state.get("retry_count", 0)

    if not query:
        logger.warning("Rerank 节点未获取到 query，跳过 rerank")
        return state

    if not docs:
        logger.warning("Rerank 节点 docs 为空，跳过 rerank")
        return state

    # 文档太少时没必要 rerank（工程优化）
    if len(docs) <= 3:
        logger.info("候选文档数量较少，跳过 Rerank")
        return state

    logger.info(f"🔁 开始 Rerank，候选文档数: {len(docs)}")

    reranker = get_reranker(top_n=settings.RETRIEVAL_TOP_K + 5 * retry_count)

    reranked_docs = reranker.rerank(
        query=query,
        documents=docs
    )

    filtered_docs = [doc for doc in reranked_docs if doc.metadata.get("rerank_score", 0) >= settings.MIN_RERANK_SCORE]

    # 给文档添加置信度
    for doc in filtered_docs:
        score = doc.metadata.get("rerank_score", 0.0)

        confidence = min(max(score, 0.0), 1.0)

        doc.metadata.update({
            "confidence": round(confidence, 3),
        })

    logger.info(f"✅ Rerank 完成，保留文档数: {len(filtered_docs)}")

    return {
        **state,
        "kb_docs": filtered_docs
    }
