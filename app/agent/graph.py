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


def build_graph():
    """
    LangGraph

    流程：
      normalize_input -> rewrite_query -> vision_triage -> intent_classifier -> gate
        -> collect_evidence -> sufficiency_judge -> respond -> END

    说明：
    - gate_node：单点决策，产出 gate={mode/tools/reasons}
    - collect_evidence_node：按 gate.tools 执行 KB/Web/Map，并在 KB 不足时扩大召回（重试）
    - sufficiency_judge_node：
        * emergency：不阻塞回答，只输出免责声明强度 + 关键追问
        * hybrid/normal：判断信息充足度 ENOUGH/PARTIAL/INSUFFICIENT
    - respond_node：根据 gate.mode + sufficiency 生成最终 response（模板策略）
    """

    workflow = StateGraph(AgentState)

    workflow.add_node("normalize_input_node", normalize_input)
    workflow.add_node("rewrite_query_node", rewrite_query)
    workflow.add_node("vision_triage_node", vision_triage)
    workflow.add_node("intent_classifier_node", intent_classifier)
    workflow.add_node("gate_node", gate)
    workflow.add_node("collect_evidence_node", collect_evidence)
    workflow.add_node("sufficiency_judge_node", sufficiency_judge)
    workflow.add_node("respond_node", respond)

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
    initial_state: AgentState = {
        "query": "这只猫严重吗？需要马上去医院吗？",
        "chat_history": [],
        "image_ids": ["https://gips1.baidu.com/it/u=297928608,3541284941&fm=3074&app=3074&f=JPEG?w=1080&h=1410&type=normal&func="],
        "enable_web_search": True,
        "enable_map": True,
        "location": "北京",
        "radius_km": 5,
        "decision_trace": [],
    }

    result = app.invoke(initial_state)

    print("最终 state keys:", list(result.keys()))
    print("mode:", (result.get("gate") or {}).get("mode"))
    print("user_intent:", result.get("user_intent"))
    print("urgency_level:", result.get("urgency_level"))
    print("red_flags:", result.get("red_flags"))
    print("response:\n", result.get("response"))
    print("decision_trace:", result.get("decision_trace"))
