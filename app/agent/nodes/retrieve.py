from app.agent.state import AgentState
from app.config import settings
from app.knowledge_base.retriever import get_retriever


def retrieve_documents(state: AgentState) -> AgentState:
    """
    从向量知识库中检索相关文档
    """

    query = state.get("rewrite_query") or state["query"]

    if not query:
        return {"kb_docs": []}

    retriever = get_retriever(top_k=settings.RETRIEVAL_TOP_K)
    docs = retriever.retrieve(query)

    return {
        **state,
        "kb_docs": docs,
        "retry_count": state.get("retry_count", 0) + 1
    }
