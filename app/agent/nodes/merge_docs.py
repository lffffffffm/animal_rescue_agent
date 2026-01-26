from typing import List, Dict
from loguru import logger
from langchain_core.documents import Document
from app.agent.state import AgentState


def merge_docs(state: AgentState) -> AgentState:
    """
    Evidence Merge 节点：
    - 合并本地 KB 文档 与 WebSearch MCP 结果
    - 统一结构，标注来源与可信度
    """

    merged: List[Dict] = []

    # ===== 1️⃣ 合并 KB 文档 =====
    kb_docs: List[Document] = state.get("kb_docs", [])

    for doc in kb_docs:
        merged.append({
            "type": "kb",
            "content": doc.page_content,
            "source": doc.metadata.get("source", "local_kb"),
            "confidence": doc.metadata.get("score")  # 可为空
        })

    # ===== 2️⃣ 合并 WebSearch 事实 =====
    web_facts = state.get("web_facts", [])

    for fact in web_facts:
        merged.append({
            "type": "web",
            "content": fact.get("content", ""),
            "source": fact.get("source", ""),
            "url": fact.get("url", ""),
            "confidence": fact.get("confidence", "")
        })

    logger.info(
        f"Evidence Merge 完成：KB={len(kb_docs)} | Web={len(web_facts)}"
    )

    return {
        **state,
        "merged_docs": merged
    }
