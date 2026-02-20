from app.agent.state import AgentState
from app.config import settings
from app.knowledge_base.retriever import get_retriever


def retrieve_documents(state: AgentState) -> AgentState:
    """
    从向量知识库中检索相关文档

    改进点：
    - 支持上层（如 collect_evidence_node）通过 state["force_top_k"] 强制指定召回数量
    - 保持旧逻辑兼容：未提供 force_top_k 时，仍使用 settings.RETRIEVAL_TOP_K + 5*retry_count
    """

    query = state.get("rewrite_query") or state.get("query")
    retry_count = state.get("retry_count", 0)

    if not query:
        return {**state, "kb_docs": []}

    force_top_k = state.get("force_top_k")
    try:
        top_k = int(force_top_k) if force_top_k is not None else (settings.RETRIEVAL_TOP_K + 5 * retry_count)
    except Exception:
        top_k = settings.RETRIEVAL_TOP_K + 5 * retry_count

    retriever = get_retriever(top_k=top_k)
    docs = retriever.retrieve(query, species=state.get("vision_facts", {}).get("species"), urgency=state.get("urgency"))

    return {
        "kb_docs": docs,
        "retry_count": retry_count + 1
    }
