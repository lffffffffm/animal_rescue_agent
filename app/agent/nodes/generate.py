from langchain_core.messages import HumanMessage
from app.agent.prompts import GENERATE_PROMPT
from app.agent.state import AgentState
from loguru import logger
from app.llm import get_llm


def generate_response(state: AgentState) -> AgentState:
    """
    Generate 节点：
    仅在 Judge 判定“证据充足”后调用
    """

    query = state.get("rewrite_query") or state.get("query")
    merged = state.get("merged_docs", {})
    kb_docs = state.get("kb_docs", [])
    web_docs = state.get("web_facts", [])

    logger.info(f"🧠 Generate：KB={len(kb_docs)}, Web={len(web_docs)}")

    context = "\n\n".join(
        f"[{i+1}]\n{doc.get('content', '')}"
        for i, doc in enumerate(merged)
    )  # todo


    prompt = GENERATE_PROMPT.format(
        context=context,
        question=query
    )

    llm = get_llm()

    response = llm.llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return {
        **state,
        "response": response.content.strip(),
    }
