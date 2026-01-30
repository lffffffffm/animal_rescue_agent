from typing import List
from loguru import logger
from langchain_core.documents import Document
from app.agent.state import AgentState
from app.config import settings


def judge_retrieval_result(state: AgentState) -> str:
    enable_web_search: bool = state.get("enable_web_search", False)
    docs: List[Document] = state.get("kb_docs", [])
    retry_count: int = state.get("retry_count", 0)

    can_retry = retry_count < settings.MAX_RETRY
    kb_insufficient = len(docs) < settings.MIN_DOCS_REQUIRED

    logger.info(
        f"Judge: docs={len(docs)}, retry={retry_count}, "
        f"can_retry={can_retry}, web={enable_web_search}"
    )

    # ① KB 不足，且还能再试 → 重试 KB
    if kb_insufficient and can_retry:
        return "retrieve"

    # ② KB 已穷尽 或 KB 已充足
    #    是否进入 WebSearch 只由 enable_web_search 决定
    if enable_web_search:
        return "web_search"

    # ③ 否则直接合并
    return "merge_docs"
