from typing import List
from loguru import logger
from langchain_core.documents import Document
from app.agent.state import AgentState
from app.config import settings


def judge_retrieval_result(state: AgentState) -> str:
    """
    Judge 节点（Routing Node）

    返回值：
    - retrieve : KB 结果不足，允许重试
    - web_search    : KB 已穷尽，转 WebSearch
    - merge_docs    : 证据充足，进入合并文档
    """

    docs: List[Document] = state.get("kb_docs", [])
    retry_count: int = state.get("retry_count", 0)

    logger.info(
        f"Judge: docs={len(docs)}, retry_count={retry_count}"
    )

    # 是否还能再试一次 KB
    can_retry = retry_count < settings.MAX_RETRY

    # 1️⃣ 完全没有文档
    if not docs:
        logger.info("Judge: 无 KB 文档")
        return "retrieve" if can_retry else "web_search"

    # 2️⃣ 文档数量不足
    if len(docs) < settings.MIN_DOCS_REQUIRED:
        logger.info("Judge: 文档数量不足")
        return "retrieve" if can_retry else "web_search"

    # 3️⃣ rerank 分数判断（如果存在）
    top_doc = docs[0]
    score = top_doc.metadata.get("rerank_score")

    if score is not None:
        logger.info(f"Judge: rerank_score={score:.4f}")
        if score < settings.MIN_RERANK_SCORE:
            logger.info("Judge: 相关性偏低")
            return "retrieve" if can_retry else "web_search"

    # 4️⃣ 通过所有检查
    logger.info("Judge: KB 覆盖充足，进入 merge_docs")
    return "merge_docs"
