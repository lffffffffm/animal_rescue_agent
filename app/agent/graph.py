from langgraph.graph import StateGraph, END

from app.agent.state import AgentState

from app.agent.nodes.rewrite_query import rewrite_query
from app.agent.nodes.retrieve import retrieve_documents
from app.agent.nodes.rerank import rerank_documents
from app.agent.nodes.judge import judge_retrieval_result
from app.agent.nodes.web_search import web_search_node
from app.agent.nodes.merge_docs import merge_docs
from app.agent.nodes.rejudge import rejudge
from app.agent.nodes.rescue_action_judge import rescue_action_judge
from app.agent.nodes.generate import generate_response
from app.agent.nodes.low_confidence_generate import low_confidence_generate
from app.agent.nodes.fail import fail


def build_graph():
    """
    LangGraph 问答 Agent 流程图（Retry + WebSearch + Judge 版）

    核心逻辑：
    1. rewrite query
    2. retrieve → rerank
    3. judge：
        - KB 不足 & 可重试 → retrieve
        - KB 穷尽 & enable_web_search → web_search → merge
        - KB 充足：
            - enable_web_search → web_search → merge
            - 否则 → merge
    4. merge → rejudge → generate / low_confidence / fail
    """

    workflow = StateGraph(AgentState)

    # ========= 注册节点（node 名字 ≠ state key） =========
    workflow.add_node("rewrite_query_node", rewrite_query)
    workflow.add_node("retrieve_node", retrieve_documents)
    workflow.add_node("rerank_node", rerank_documents)
    workflow.add_node("web_search_node", web_search_node)
    workflow.add_node("merge_docs_node", merge_docs)
    workflow.add_node("rescue_action_judge_node", rescue_action_judge)
    workflow.add_node("generate_node", generate_response)
    workflow.add_node("low_confidence_generate_node", low_confidence_generate)
    workflow.add_node("fail_node", fail)

    # ========= 入口 =========
    workflow.set_entry_point("rewrite_query_node")

    # ========= 主流程 =========
    workflow.add_edge("rewrite_query_node", "retrieve_node")
    workflow.add_edge("retrieve_node", "rerank_node")

    # ========= Judge：唯一的 routing 决策点 =========
    workflow.add_conditional_edges(
        "rerank_node",
        judge_retrieval_result,
        path_map={
            "retrieve": "retrieve_node",
            "web_search": "web_search_node",
            "merge_docs": "merge_docs_node",
        },
    )

    # ========= Web Search 后一定进入 merge =========
    workflow.add_edge("web_search_node", "merge_docs_node")

    # ========= Merge 后二次判断 =========
    workflow.add_conditional_edges(
        "merge_docs_node",
        rejudge,
        path_map={
            "rescue_action_judge": "rescue_action_judge_node",
            "low_confidence_generate": "low_confidence_generate_node",
            "fail": "fail_node",
        },
    )

    # ========= 生成 =========
    workflow.add_edge("rescue_action_judge_node", "generate_node")

    # ========= 结束 =========
    workflow.add_edge("generate_node", END)
    workflow.add_edge("low_confidence_generate_node", END)
    workflow.add_edge("fail_node", END)

    return workflow.compile()


def visualize_graph():
    """
    生成并保存流程图
    """
    app = build_graph()
    graph_image = app.get_graph().draw_mermaid_png()
    with open("animal_rescue_flow.png", "wb") as f:
        f.write(graph_image)
    print("流程图已保存为 animal_rescue_flow.png")

app = build_graph()

if __name__ == "__main__":
    app = build_graph()

    initial_state = AgentState(
        query="如何救助流浪猫",
        chat_history=[],
        enable_web_search=False,   # 可切换测试
        retry_count=0,
        location="北京"
    )

    print("开始测试 LangGraph 流程...")
    result = app.invoke(initial_state)

    print("\n流程执行完成")
    print("最终 state keys:", list(result.keys()))
    if "response" in result:
        print("回答：", result["response"])
