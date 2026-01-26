from langgraph.graph import StateGraph, END
from app.agent.nodes.low_confidence_generate import low_confidence_generate
from app.agent.nodes.merge_docs import merge_docs
from app.agent.nodes.rejudge import rejudge
from app.agent.nodes.rescue_action_judge import rescue_action_judge
from app.agent.nodes.web_search import web_search_node
from app.agent.state import AgentState
from app.agent.nodes.rewrite_query import rewrite_query
from app.agent.nodes.retrieve import retrieve_documents
from app.agent.nodes.rerank import rerank_documents
from app.agent.nodes.judge import judge_retrieval_result
from app.agent.nodes.generate import generate_response
from app.agent.nodes.fail import fail
from app.config import settings


def build_graph():
    """
    构建 LangGraph 问答 Agent 流程图（标准 Judge 决策版）
    """

    workflow = StateGraph(AgentState)

    # ========= 注册节点 =========
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("rerank", rerank_documents)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("generate", generate_response)
    workflow.add_node("merge_docs", merge_docs)
    workflow.add_node("low_confidence_generate", low_confidence_generate)
    workflow.add_node("rescue_action_judge", rescue_action_judge)
    workflow.add_node("fail", fail)

    # ========= 设置入口 =========
    workflow.set_entry_point("rewrite_query")

    # ========= 主流程 =========
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("retrieve", "rerank")
    # workflow.add_edge("rescue_action_judge", "generate")
    workflow.add_edge("web_search", "merge_docs")

    # ========= Judge 条件分支（唯一分支点） =========
    workflow.add_conditional_edges(
        "rerank",
        judge_retrieval_result,
        path_map={
            "retrieve": "retrieve",
            "web_search": "web_search",
            "merge_docs": "merge_docs",
        },
    )

    workflow.add_conditional_edges(
        "merge_docs",
        rejudge,
        {
            # "rescue_action_judge": "rescue_action_judge",
            "generate": "generate",
            "low_confidence_generate": "low_confidence_generate",
            "fail": "fail"
        }
    )

    # ========= 结束 =========
    workflow.add_edge("low_confidence_generate", END)
    workflow.add_edge("generate", END)
    workflow.add_edge("fail", END)

    return workflow.compile()


def visualize_graph():
    """
    生成并显示流程图
    """
    app = build_graph()

    # 方法1: 获取图的可视化表示
    graph_image = app.get_graph().draw_mermaid_png()
    with open("animal_rescue_flow.png", "wb") as f:
        f.write(graph_image)
    print("流程图已保存为 animal_rescue_flow.png")


if __name__ == "__main__":
    # 构建图
    app = build_graph()

    # 创建初始状态
    initial_state = AgentState(
        query="怎么救助流浪猫",
        chat_history=[]
    )

    print("开始测试 LangGraph 流程...")
    print(f"初始查询: {initial_state['query']}")

    # 运行图
    result = app.invoke(initial_state)

    print("\n流程执行完成！")
    print(f"最终状态包含的字段: {list(result.keys())}")

    if "response" in result:
        print(f"生成的回答: {result['response']}")
    elif "error" in result:
        print(f"错误信息: {result['error']}")

    print("\n测试完成！")


