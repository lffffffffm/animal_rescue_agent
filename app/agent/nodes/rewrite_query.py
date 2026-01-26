from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from loguru import logger
from app.agent.prompts import REWRITE_QUERY_PROMPT
from app.agent.state import AgentState
from app.llm import get_llm


def rewrite_query(state: AgentState) -> AgentState:
    """
    重写用户查询以改善搜索效果

    该函数使用大语言模型根据对话历史对当前查询进行重写，
    使查询更加明确和完整，有助于后续的检索操作。

    Args:
        state (AgentState): 包含当前对话状态的字典，主要包括：
            - query (str): 用户的原始查询
            - chat_history (list): 对话历史记录

    Returns:
        dict: 包含重写后查询的状态更新字典
            - rewrite_query (str): 重写后的查询字符串
    """
    llm = get_llm().llm  # 这里的LLM不能是封装的类，否则会报错
    prompt = PromptTemplate(
        template=REWRITE_QUERY_PROMPT,
        input_variables=["query", "chat_history"],
    )
    chain = prompt | llm | StrOutputParser()
    new_query = chain.invoke({
        "query": state["query"],
        "chat_history": format_chat_history(state["chat_history"]),
    })
    logger.info(f"重写后的查询：{new_query}")
    return {**state, "rewrite_query": new_query}


def format_chat_history(chat_history: list) -> str:
    """
    格式化对话历史为字符串

    Args:
        chat_history: 对话历史列表

    Returns:
        格式化的对话历史字符串
    """
    if not chat_history:
        return ""

    formatted_history = []
    for i, turn in enumerate(chat_history[-5:], 1):  # 只取最近5轮对话
        if isinstance(turn, tuple):
            role, content = turn
            formatted_history.append(f"[{i}] {role}: {content}")
        else:
            formatted_history.append(f"[{i}] {str(turn)}")

    return "\n".join(formatted_history)


if __name__ == "__main__":
    from app.agent.state import AgentState

    # 创建示例状态
    example_state = AgentState(
        query="它们有哪些要求？",  # 当前查询
        chat_history=[  # 对话历史
            ("user", "我想领养一只金毛犬"),
            ("assistant", "我们有2只金毛犬可供领养，一只是3个月大的幼犬，另一只是成年犬"),
            ("user", "它们有哪些要求？")
        ],
    )

    print("原始查询:", example_state["query"])
    print("对话历史:")
    for i, turn in enumerate(example_state["chat_history"]):
        if isinstance(turn, tuple):
            role, content = turn
            print(f"  [{i + 1}] {role}: {content}")
        else:
            print(f"  [{i + 1}] {turn}")

    # 执行查询重写
    result = rewrite_query(example_state)

    print("\n重写后的查询:", result["rewrite_query"])
    print("重写完成！")
