from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from loguru import logger

from app.agent.state import AgentState
from app.llm import get_llm

# todo: 找到文学依据/扩展
_RED_FLAG_HARD = {
    "heavy_bleeding",
    "open_fracture",
    "respiratory_distress",
    "seizure_or_unconscious",
}


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _normalize_urgency(level: Any) -> str:
    s = _clean_text(level).upper()
    return s if s in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "MEDIUM"


def _urgency_rank(level: str) -> int:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    return order.get(level, 1)


def _normalize_red_flags(v: Any) -> list[str]:
    if not v:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            s = _clean_text(x)
            if s:
                out.append(s)
        # 去重保序
        seen = set()
        dedup = []
        for x in out:
            if x in seen:
                continue
            seen.add(x)
            dedup.append(x)
        return dedup
    s = _clean_text(v)
    return [s] if s else []


def gate(state: AgentState) -> AgentState:
    """
    gate_node：单点决策（模式 + 允许工具）

    输入（来自前置节点）：
    - user_intent: real_help / learn_only / unclear
    - urgency_level: LOW/MEDIUM/HIGH/CRITICAL（来自 vision_triage）
    - red_flags: list[str]
    - enable_web_search / enable_map / location / radius_km

    输出：
    - gate: {
        mode: emergency|hybrid|normal,
        tools: {kb: bool, web: bool, map: bool},
        map_params: {radius_km:int, resource_type:str},
        reasons: list[str]
      }
    并写入 decision_trace

    设计原则：
    - 决策必须“可解释”（reasons）
    - emergency 只有在高风险且用户意图不是 learn_only 时触发
    - hybrid 用于“高风险但仅科普/不确定”的折中输出
    """

    intent = _clean_text(state.get("user_intent") or "unclear").lower()
    urgency = _normalize_urgency(state.get("urgency_level"))
    red_flags = _normalize_red_flags(state.get("red_flags"))

    enable_web = bool(state.get("enable_web_search", False))
    enable_map = bool(state.get("enable_map", False))
    location = _clean_text(state.get("location"))

    # radius 默认 5，并做简单 clamp
    radius_raw = state.get("radius_km")
    try:
        radius_km = int(radius_raw) if radius_raw is not None else 5
    except Exception:
        radius_km = 5
    radius_km = max(1, min(20, radius_km))

    reasons: list[str] = []

    # ========== 1) 风险判定 ==========
    hard_flag_hit = any(f in _RED_FLAG_HARD for f in red_flags)
    if hard_flag_hit:
        reasons.append("hard_red_flag")

    high_risk = _urgency_rank(urgency) >= _urgency_rank("HIGH") or bool(red_flags)
    if _urgency_rank(urgency) >= _urgency_rank("HIGH"):
        reasons.append(f"urgency>={urgency}")
    if red_flags:
        reasons.append("red_flags_present")

    # ========== 2) mode 决策 ==========
    # 安全优先：视觉红旗/CRITICAL 命中时，强制 emergency（即使 intent_classifier 判成 learn_only）
    if urgency == "CRITICAL" or hard_flag_hit:
        mode = "emergency"
        reasons.append("mode=emergency_vision_override")
    elif high_risk:
        # 高风险但非 CRITICAL：
        # - 若用户明确仅科普/非真实场景 -> hybrid
        # - 其他 -> emergency
        if intent == "learn_only":
            mode = "hybrid"
            reasons.append("mode=hybrid")
        else:
            mode = "emergency"
            reasons.append("mode=emergency")
    else:
        mode = "normal"
        reasons.append("mode=normal")

    # ========== 3) 工具许可（先不执行，后续 collect_evidence 用） ==========
    # hybrid/normal 下是否需要 map：改为 LLM 判定（更鲁棒，覆盖同义表达）
    text_for_need_map = _clean_text(
        state.get("rewrite_query")
        or state.get("normalized_query")
        or state.get("query")
    )

    chat_history = state.get("chat_history") or []

    def _format_history_for_prompt(ch: Any, limit_turns: int = 6) -> str:
        if not ch or not isinstance(ch, list):
            return ""
        recent = ch[-limit_turns:]
        lines = []
        for i, turn in enumerate(recent, 1):
            if isinstance(turn, tuple) and len(turn) == 2:
                role, content = turn
                role = _clean_text(role)
                content = _clean_text(content)
                if role and content:
                    lines.append(f"[{i}] {role}: {content}")
            else:
                lines.append(f"[{i}] {str(turn)}")
        return "\n".join(lines)

    def _extract_first_json_object(text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start: end + 1].strip()
        return None

    def _llm_need_map(query: str, history_str: str) -> tuple[bool, str]:
        llm = get_llm().llm
        prompt = f"""
你是一个工具路由判定器。请判断用户是否在询问“附近线下资源”，例如：附近宠物医院/救助站/联系方式/地址/导航等。

只输出严格 JSON，不要输出多余文字。

输出 schema:
{{
  \"need_map\": true/false,
  \"reason\": \"一句话原因\"
}}

当前用户问题:
{query}

最近对话历史(可能为空):
{history_str}
""".strip()

        resp = llm.invoke([HumanMessage(content=prompt)])
        raw = resp.content or ""
        js = _extract_first_json_object(raw)
        if not js:
            return False, "llm_no_json"
        try:
            obj = json.loads(js)
        except Exception:
            return False, "llm_json_parse_failed"

        need = obj.get("need_map")
        if isinstance(need, bool):
            return need, _clean_text(obj.get("reason")) or "llm_decided"
        return False, "llm_invalid_need_map"

    need_map = False
    need_map_reason = "skip"

    # 只有在 enable_map 且有 location 且非 emergency 才需要 LLM 判定 need_map
    if enable_map and bool(location) and mode != "emergency" and text_for_need_map:
        try:
            need_map, need_map_reason = _llm_need_map(
                query=text_for_need_map,
                history_str=_format_history_for_prompt(chat_history),
            )
        except Exception as e:
            need_map = False
            need_map_reason = f"llm_exception:{e}"

        reasons.append(f"need_map_llm:{need_map_reason}")

    tools = {
        "kb": True,
        # 急救不等 web（先保命再说）；hybrid/normal 才允许 web
        "web": bool(enable_web and mode != "emergency"),
        # map 需要 enable_map + location：
        # - emergency：默认开启（强相关）
        # - hybrid/normal：由 LLM 判定用户是否在问附近资源
        "map": bool(enable_map and bool(location) and (mode == "emergency" or need_map)),
    }

    gate_obj = {
        "mode": mode,
        "tools": tools,
        "map_params": {
            "radius_km": radius_km,
            "resource_type": "hospital",
        },
        "reasons": reasons,
    }

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    decision_trace.append({
        "node": "gate_node",
        "intent": intent,
        "urgency_level": urgency,
        "red_flags": red_flags,
        "enable_web_search": enable_web,
        "enable_map": enable_map,
        "has_location": bool(location),
        "gate": gate_obj,
    })

    logger.info(
        f"gate_node: mode={mode} intent={intent} urgency={urgency} "
        f"red_flags={red_flags} tools={tools}"
    )

    return {
        **state,
        "gate": gate_obj,
        "decision_trace": decision_trace,
    }
