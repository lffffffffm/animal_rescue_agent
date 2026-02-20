from typing import List
from loguru import logger
from langchain_core.documents import Document
from app.agent.state import AgentState
from app.config import settings
from app.knowledge_base.reranker import get_reranker


def rerank_documents(state: AgentState) -> AgentState:
    query: str = state.get("rewrite_query") or state.get("query")
    docs: List[Document] = state.get("kb_docs", [])
    retry_count: int = state.get("retry_count", 0)

    # 1. 增加重试时的衰减系数 (核心：让重试有意义)
    # 比如每重试一次，阈值下降 0.1，最低不低于 0.3
    current_threshold = max(settings.MIN_RERANK_SCORE - ((retry_count - 1) * 0.1), 0.3)

    if not query or not docs:
        return state

    # 2. 文档太少时直接返回，避免浪费 8s 做 Rerank
    if len(docs) <= 3:
        logger.info(f"候选文档数({len(docs)})过少，跳过 Rerank 直接透传")
        return state

    logger.info(f"🔁 开始 Rerank (重试轮次: {retry_count}, 当前阈值: {current_threshold:.2f})")

    # 根据重试次数动态扩大 Top_N
    top_n = settings.RERANK_TOP_K + 5 * retry_count
    reranker = get_reranker(top_n=top_n)

    reranked_docs = reranker.rerank(query=query, documents=docs)

    # 3. 过滤并增加保底逻辑
    filtered_docs = []
    for doc in reranked_docs:
        score = float(doc.metadata.get("rerank_score", 0.0))
        doc.metadata["rerank_score"] = score

        # 记录日志方便 Debug
        logger.info(f"文档 {doc.metadata.get('source', 'ID:' + str(doc.id))} 分数: {score:.3f}")

        if score >= current_threshold:
            # 顺便更新置信度
            doc.metadata["confidence"] = round(min(max(score, 0.0), 1.0), 3)
            filtered_docs.append(doc)

    # 4. 【关键】保底机制：如果过滤后一个都不剩，强制保留原始排序的前 2 条
    # 防止 sufficiency_judge 再次触发循环
    if not filtered_docs and reranked_docs:
        logger.warning(f"⚠️ 所有文档均低于阈值 {current_threshold}，触发保底机制保留 Top-2")
        filtered_docs = reranked_docs[:2]
        for d in filtered_docs:
            d.metadata["confidence"] = 0.3  # 给一个较低的默认置信度

    logger.info(f"✅ Rerank 完成，保留文档数: {len(filtered_docs)}")

    return {
        **state,
        "kb_docs": filtered_docs
    }
