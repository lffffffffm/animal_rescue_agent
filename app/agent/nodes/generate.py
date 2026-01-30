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
    merged = state.get("merged_docs", [])
    kb_docs = state.get("kb_docs", [])
    web_docs = state.get("web_facts", [])
    enable_map = state.get("enable_map")

    logger.info(f"🧠 Generate：KB={len(kb_docs)}, Web={len(web_docs)}")

    # ===== 生成 context，保留来源、类型、置信度和 url（若存在） =====
    context = "\n\n".join(
        f"[{i + 1}] (type: {doc.get('type', 'unknown')}, "
        f"source: {doc.get('source', '')}, "
        f"confidence: {doc.get('confidence', '')}"
        + (f", url: {doc.get('url', '')}" if doc.get('url') else "")
        + f")\n{doc.get('content', '')}"
        for i, doc in enumerate(merged)
    )

    if enable_map:
        for i, hospital in enumerate(state.get("map_result", []), 1):
            context += (
                f"\n{i}. {hospital['name']} "
                f"({hospital.get('distance_m', '?')}m)\n"
                f"   地址: {hospital.get('address', '未知')}\n"
                f"   电话: {hospital.get('tel', '无')}"
            )

    logger.info(f"Context: {context}")
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
