from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from loguru import logger
from app.agent.prompts import REWRITE_QUERY_PROMPT
from app.agent.state import AgentState
from app.llm import get_llm


def format_chat_history_for_prompt(chat_history: list[tuple[str, str]]) -> str:
    """
    将干净的对话历史格式化为字符串，用于 LLM prompt。
    输入已经是 normalize_input_node 清理过的格式。
    """
    if not chat_history:
        return ""

    # 只取最近5轮对话，避免 prompt 过长
    recent_history = chat_history[-5:]

    formatted_lines = [
        f"[{i + 1}] {role}: {content}"
        for i, (role, content) in enumerate(recent_history)
    ]

    return "\n".join(formatted_lines)


def rewrite_query(state: AgentState) -> AgentState:
    """
    重写用户查询以改善搜索效果

    设计要点：
    - 优先使用 normalize_input_node 产出的 normalized_query（更稳定、支持“只上传图片不输入文字”的场景）
    - 若 normalized_query 不存在，则回退到原 query
    - 重写失败时兜底：rewrite_query = input_query（保证后续检索可用）
    """
    input_query = state.get("normalized_query") or state.get("query") or ""
    chat_history = state.get("chat_history") or []

    if not input_query:
        logger.warning("rewrite_query_node: 输入 query 为空，跳过重写")
        return {**state, "rewrite_query": ""}
    try:
        llm = get_llm().llm  # 这里的LLM不能是封装的类，否则会报错
        prompt = PromptTemplate(
            template=REWRITE_QUERY_PROMPT,
            input_variables=["query", "chat_history"],
        )
        chain = prompt | llm | StrOutputParser()
        new_query = chain.invoke({
            "query": input_query,
            "chat_history": format_chat_history_for_prompt(chat_history),
        })
        new_query = (new_query or "").strip()
        if not new_query:
            logger.warning("rewrite_query_node: LLM 返回空字符串，使用兜底 query")
            new_query = input_query

        logger.info(f"重写后的查询：{new_query}")
        decision_trace = state.get("decision_trace")
        if isinstance(decision_trace, list):
            decision_trace.append({
                "node": "rewrite_query_node",
                "input_query": input_query,
                "output_query": new_query,
                "history_len": len(chat_history) if isinstance(chat_history, list) else None,
            })

        return {**state, "rewrite_query": new_query}
    except Exception as e:
        logger.exception(f"rewrite_query_node: 重写失败，使用兜底 query: {e}")

        decision_trace = state.get("decision_trace")
        if isinstance(decision_trace, list):
            decision_trace.append({
                "node": "rewrite_query_node",
                "error": str(e),
                "fallback_query": input_query,
            })

        return {**state, "rewrite_query": input_query}


if __name__ == "__main__":
    # 本地快速自测用
    example_state: AgentState = {
        "normalized_query": "它们有哪些要求？",
        "chat_history": [
            ("user", "我想领养一只金毛犬"),
            ("assistant", "我们有2只金毛犬可供领养，一只是3个月大的幼犬，另一只是成年犬"),
            ("user", "它们有哪些要求？"),
        ],
        "decision_trace": [],
    }

    result = rewrite_query(example_state)
    print("rewrite_query =", result.get("rewrite_query"))
    print("decision_trace =", result.get("decision_trace"))
