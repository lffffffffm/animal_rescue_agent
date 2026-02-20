from __future__ import annotations

import json
from typing import Optional

from langchain_core.messages import HumanMessage
from loguru import logger

from app.agent.state import AgentState
from app.llm import get_llm
from app.utils.common import clean_text, normalize_urgency, normalize_red_flags, extract_first_json_object

# 保持不变：硬红旗指标（触发紧急模式的生物学特征）
_RED_FLAG_HARD = {
    "heavy_bleeding",
    "open_fracture",
    "respiratory_distress",
    "seizure_or_unconscious",
}


def _urgency_rank(level: str) -> int:
    """
    定义紧急度权重：info=0, common=1, critical=2
    """
    order = {"info": 0, "common": 1, "critical": 2}
    return order.get(level, 1)


def _llm_need_map(query: str, history_str: str) -> tuple[bool, str]:
    """判定用户是否在寻找线下资源"""
    llm = get_llm().llm
    prompt = f"""
    你是一个工具路由判定器。请判断用户是否在询问“附近线下资源”，例如：附近宠物医院/救助站/联系方式/地址/导航等。
    只输出严格 JSON。
    输出 schema: {{"need_map": true/false, "reason": "原因"}}
    当前问题: {query}
    最近对话: {history_str}
    """.strip()
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw = resp.content or ""
        js = extract_first_json_object(raw)
        if not js: return False, "no_json"
        obj = json.loads(js)
        return bool(obj.get("need_map")), clean_text(obj.get("reason"))
    except Exception as e:
        return False, f"error:{str(e)}"


def gate(state: AgentState) -> AgentState:
    """
    gate_node：根据意图和分诊结果决定模式与工具准入
    """
    # 1. 数据对齐与准备
    intent = clean_text(state.get("user_intent") or "unclear").lower()
    urgency = normalize_urgency(state.get("urgency"))
    red_flags = normalize_red_flags(state.get("red_flags"))

    enable_web = bool(state.get("enable_web_search", False))
    enable_map = bool(state.get("enable_map", False))
    location = clean_text(state.get("location"))

    reasons: list[str] = []

    # ========== 2) 核心决策逻辑 (基于 3 级体系) ==========

    # 是否命中硬性生物特征红旗
    hard_flag_hit = any(f in _RED_FLAG_HARD for f in red_flags)
    if hard_flag_hit:
        reasons.append("hit_hard_red_flag")

    # 是否属于高风险 (critical 或 有红旗)
    is_high_risk = _urgency_rank(urgency) >= _urgency_rank("common") or bool(red_flags)

    # 模式分流判定
    if urgency == "critical" or hard_flag_hit:
        # 只要是最高级别危急，强制 emergency
        mode = "emergency"
        reasons.append("mode=emergency_due_to_critical_condition")
    elif is_high_risk:
        # 风险高但非极度危急：
        # 若意图是科普/了解情况 -> hybrid (给专业建议但不禁用网页搜索)
        # 若是求助或不确定 -> emergency
        if intent == "learn_only":
            mode = "hybrid"
            reasons.append("mode=hybrid_high_risk_but_learn_intent")
        else:
            mode = "emergency"
            reasons.append("mode=emergency_high_risk_rescue_intent")
    else:
        mode = "normal"
        reasons.append("mode=normal_stable_condition")

    # ========== 3) 工具许可管控 ==========

    # 只有在非紧急模式下，才通过 LLM 判定地图需求（急救模式默认按需全开）
    need_map = False
    need_map_reason = "auto_skip"

    query_for_map = clean_text(state.get("rewrite_query") or state.get("query"))

    if enable_map and bool(location) and mode != "emergency" and query_for_map:
        history_str = str(state.get("chat_history", [])[-3:])
        need_map, need_map_reason = _llm_need_map(query_for_map, history_str)
        reasons.append(f"llm_map_check:{need_map_reason}")

    # 工具开关矩阵
    tools = {
        "kb": True,  # 永远开启知识库
        "web": bool(enable_web and mode != "emergency"),  # 紧急模式禁用 Web 以提速
        "map": bool(enable_map and bool(location) and need_map),
    }

    # 构造输出对象
    gate_obj = {
        "mode": mode,
        "tools": tools,
        "map_params": {
            "radius_km": 10, # 默认 10 km
            "resource_type": "hospital",
        },
        "reasons": reasons,
    }

    # 记录追踪
    decision_trace = list(state.get("decision_trace") or [])
    decision_trace.append({
        "node": "gate_node",
        "mode": mode,
        "urgency_snapshot": urgency,
        "intent_snapshot": intent,
        "tools_allowed": [t for t, v in tools.items() if v]
    })

    logger.info(f"Gate Decision: Mode={mode}, Tools={tools}, Reasons={reasons}")

    return {
        **state,
        "gate": gate_obj,
        "decision_trace": decision_trace,
    }
