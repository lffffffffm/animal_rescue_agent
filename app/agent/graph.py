from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes.normalize_input import normalize_input
from app.agent.nodes.rewrite_query import rewrite_query
from app.agent.nodes.vision_triage import vision_triage
from app.agent.nodes.intent_classifier import intent_classifier
from app.agent.nodes.gate import gate
from app.agent.nodes.collect_evidence import collect_evidence
from app.agent.nodes.sufficiency_judge import sufficiency_judge
from app.agent.nodes.respond import respond
from langsmith import traceable
import inspect

# 定义白名单字段，用于上报到 LangSmith
TRACE_WHITELIST = {
    "query", "normalized_query", "rewrite_query", "user_intent",
    "urgency", "red_flags", "gate", "sufficiency",
    "retry_count", "force_top_k",
}


def trace_node(name: str):
    """节点监控包装器：使用 LangSmith 的 @traceable 装饰器。"""

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @traceable(name=name, run_type="chain")
            async def async_wrapper(state: AgentState):
                return await func(state)

            return async_wrapper

        @traceable(name=name, run_type="chain")
        def sync_wrapper(state: AgentState):
            return func(state)

        return sync_wrapper

    return decorator


def build_graph():
    """LangGraph 工作流定义。"""

    workflow = StateGraph(AgentState)

    # 应用包装器进行节点注册
    workflow.add_node("normalize_input_node", trace_node("normalize_input")(normalize_input))
    workflow.add_node("rewrite_query_node", trace_node("rewrite_query")(rewrite_query))
    workflow.add_node("vision_triage_node", trace_node("vision_triage")(vision_triage))
    workflow.add_node("intent_classifier_node", trace_node("intent_classifier")(intent_classifier))
    workflow.add_node("gate_node", trace_node("gate")(gate))
    workflow.add_node("collect_evidence_node", trace_node("collect_evidence")(collect_evidence))
    workflow.add_node("sufficiency_judge_node", trace_node("sufficiency_judge")(sufficiency_judge))
    workflow.add_node("respond_node", trace_node("respond")(respond))

    workflow.set_entry_point("normalize_input_node")

    workflow.add_edge("normalize_input_node", "rewrite_query_node")
    workflow.add_edge("rewrite_query_node", "vision_triage_node")
    workflow.add_edge("vision_triage_node", "intent_classifier_node")
    workflow.add_edge("intent_classifier_node", "gate_node")
    workflow.add_edge("gate_node", "collect_evidence_node")
    workflow.add_edge("collect_evidence_node", "sufficiency_judge_node")
    workflow.add_edge("sufficiency_judge_node", "respond_node")
    workflow.add_edge("respond_node", END)

    return workflow.compile()


app = build_graph()

if __name__ == "__main__":
    graph = build_graph()

    # 输出 Mermaid 文本
    print(graph.get_graph().draw_mermaid())

    # 或者直接生成 PNG
    with open("./agent_graph.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
