from __future__ import annotations
import json
import re
from typing import Any, Optional
from loguru import logger
from langchain_core.messages import HumanMessage
from app.agent.state import AgentState
from app.llm import get_llm


INTENTS = {"real_help", "learn_only", "unclear"}


LEARN_ONLY_KEYWORDS = [
    "不是实际情况",
    "并不是实际情况",
    "不是我遇到的",
    "不是我的",
    "网上看到",
    "转发",
    "科普",
    "了解一下",
    "想了解",
    "只是想知道",
    "这是什么病",
    "这是什么症状",
    "这是什么情况",
    "不需要救助",
    "不用救助",
]
# todo: 规则具有局限性，后续修改
REAL_HELP_KEYWORDS = [
    "救命",
    "快不行了",
    "很严重",
    "流血",
    "大量出血",
    "止不住血",
    "骨折",
    "抽搐",
    "昏迷",
    "呼吸困难",
    "不能呼吸",
    "吐血",
    "休克",
    "低温",
    "附近医院",
    "宠物医院",
    "救助站",
    "怎么办",
    "现在该怎么办",
    "急",
    "紧急",
]


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _format_chat_history_for_prompt(chat_history: Any, limit_turns: int = 6) -> str:
    """
    假设 normalize_input_node 已经把 chat_history 清洗成 list[tuple[str,str]]
    这里仅做 prompt 格式化。
    """
    if not chat_history:
        return ""
    if not isinstance(chat_history, list):
        return ""

    recent = chat_history[-limit_turns:]
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


def _keyword_rule_intent(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    返回 (intent, reason)。如果无法规则判定，则 intent=None。
    """
    t = text

    for kw in LEARN_ONLY_KEYWORDS:
        if kw in t:
            return "learn_only", f"hit_learn_only_keyword:{kw}"

    for kw in REAL_HELP_KEYWORDS:
        if kw in t:
            return "real_help", f"hit_real_help_keyword:{kw}"

    return None, None


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    从 LLM 输出中提取 JSON，对模型偶尔输出多余文字做兜底。
    """
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
        return text[start : end + 1].strip()

    return None


def _llm_classify_intent(query: str, chat_history_str: str) -> tuple[str, str]:
    """
    用 LLM 做意图分类，返回 (intent, reason)
    """
    llm = get_llm().llm

    prompt = f"""
你是一个“动物救助对话意图分类器”。请判断用户当前请求属于哪类意图，仅输出严格 JSON。

意图类型:
- real_help: 用户正在真实遇到情况，需要救助/急救/行动建议（倾向立即处理）
- learn_only: 用户明确表示非真实情况、仅科普/了解病症/讨论案例（不需要紧急短路，但可给安全提醒）
- unclear: 无法判断

要求:
- 只输出 JSON，不要输出多余文字。
- intent 必须是 real_help / learn_only / unclear 三者之一。

输出 JSON schema:
{{
  "intent": "real_help|learn_only|unclear",
  "reason": "一句话说明依据"
}}

当前用户问题:
{query}

最近对话历史(可能为空):
{chat_history_str}
""".strip()

    resp = llm.invoke([HumanMessage(content=prompt)])
    raw = resp.content or ""
    json_str = _extract_first_json_object(raw)
    if not json_str:
        return "unclear", "llm_output_no_json"

    try:
        obj = json.loads(json_str)
    except Exception:
        return "unclear", "llm_json_parse_failed"

    intent = _clean_text(obj.get("intent")).lower()
    reason = _clean_text(obj.get("reason")) or "llm_classified"

    if intent not in INTENTS:
        return "unclear", "llm_invalid_intent_value"

    return intent, reason


def intent_classifier(state: AgentState) -> AgentState:
    """
    intent_classifier_node（规则 + LLM）：
    - 先用关键词规则快速判定（省钱、稳定）
    - 规则不命中，再用 LLM 分类（更智能）
    """
    # 优先用 rewrite_query，其次 normalized_query
    query = _clean_text(state.get("rewrite_query") or state.get("normalized_query") or state.get("query"))
    chat_history = state.get("chat_history") or []
    chat_history_str = _format_chat_history_for_prompt(chat_history)

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    if not query:
        # 没有 query 的情况下，无法分类，默认 unclear
        decision_trace.append({
            "node": "intent_classifier_node",
            "status": "no_query",
            "intent": "unclear",
        })
        return {**state, "user_intent": "unclear", "decision_trace": decision_trace}

    # 1) 规则优先
    intent, reason = _keyword_rule_intent(query)
    if intent:
        logger.info(f"intent_classifier_node(rule): intent={intent}, reason={reason}")
        decision_trace.append({
            "node": "intent_classifier_node",
            "status": "rule",
            "intent": intent,
            "reason": reason,
        })
        return {**state, "user_intent": intent, "decision_trace": decision_trace}

    # 2) LLM 分类兜底
    try:
        intent2, reason2 = _llm_classify_intent(query=query, chat_history_str=chat_history_str)
        logger.info(f"intent_classifier_node(llm): intent={intent2}, reason={reason2}")
        decision_trace.append({
            "node": "intent_classifier_node",
            "status": "llm",
            "intent": intent2,
            "reason": reason2,
        })
        return {**state, "user_intent": intent2, "decision_trace": decision_trace}

    except Exception as e:
        logger.exception(f"intent_classifier_node(llm) failed: {e}")
        decision_trace.append({
            "node": "intent_classifier_node",
            "status": "fallback_exception",
            "intent": "unclear",
            "error": str(e),
        })
        return {**state, "user_intent": "unclear", "decision_trace": decision_trace}


if __name__ == "__main__":
    # 简单自测
    s1: AgentState = {"rewrite_query": "这不是实际情况，只是想了解这种症状是什么病。", "decision_trace": []}
    print(intent_classifier(s1).get("user_intent"), intent_classifier(s1).get("decision_trace")[-1])

    s2: AgentState = {"rewrite_query": "假如猫流血怎么办？", "decision_trace": []}
    print(intent_classifier(s2).get("user_intent"), intent_classifier(s2).get("decision_trace")[-1])