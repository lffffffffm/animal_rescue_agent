from __future__ import annotations

from typing import Any

from loguru import logger

from app.agent.state import AgentState
from app.config import settings


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _mode_from_gate(state: AgentState) -> str:
    g = state.get("gate") or {}
    if isinstance(g, dict):
        m = _clean_text(g.get("mode"))
        if m in {"emergency", "hybrid", "normal"}:
            return m
    return "normal"


def sufficiency_judge(state: AgentState) -> AgentState:
    """
    sufficiency_judge_node：评估证据是否足够支持回答，并产出回复策略。

    设计：
    - emergency：不做“是否回答”判断，只产出需要强调的不确定性强度 + 关键追问
    - hybrid/normal：输出 sufficiency_level: ENOUGH/PARTIAL/INSUFFICIENT

    写回字段：
    - sufficiency: {
        "mode": emergency|hybrid|normal,
        "level": ENOUGH|PARTIAL|INSUFFICIENT|EMERGENCY,
        "missing": [..],
        "followup_questions": [..]
      }
    """

    mode = _mode_from_gate(state)

    query = _clean_text(state.get("rewrite_query") or state.get("normalized_query") or state.get("query"))

    kb_docs = state.get("kb_docs") or []
    if not isinstance(kb_docs, list):
        kb_docs = []

    web_facts = state.get("web_facts") or []
    if not isinstance(web_facts, list):
        web_facts = []

    vision_facts = state.get("vision_facts") or {}
    if not isinstance(vision_facts, dict):
        vision_facts = {}

    vision_conf = vision_facts.get("confidence")
    try:
        vision_conf = float(vision_conf) if vision_conf is not None else None
    except Exception:
        vision_conf = None

    red_flags = state.get("red_flags") or vision_facts.get("red_flags") or []
    if not isinstance(red_flags, list):
        red_flags = []

    location = _clean_text(state.get("location"))

    missing: list[str] = []
    followup: list[str] = []

    # ===== 缺失信息检查（通用） =====
    if not query:
        missing.append("query")

    if not vision_facts:
        missing.append("vision_facts")

    if not location:
        missing.append("location")

    # 关键追问（工程取舍：采用“可执行的最小问诊集”，避免过度诊断）
    # 原则：
    # - 紧急：优先获取是否存在危及生命红旗信号 + 可操作的处置条件
    # - 非紧急：优先补全症状与时间线，便于判断是否需要进一步检索/就医
    followup.extend([
        "当前最担心的症状是什么（出血/跛行/呼吸异常/抽搐/呕吐腹泻/精神差）？",
        "症状大概从什么时候开始、是突然发生还是逐渐加重？",
        "动物目前精神状态与进食饮水情况如何？",
        "是否存在红旗信号：大量持续出血、呼吸困难、抽搐/昏迷、明显骨折/开放性伤口？",
        "你所在城市/大致位置是哪里？是否需要我帮你查询附近医院/救助站？",
    ])

    # ===== emergency：只输出安全提示强度与关键追问 =====
    if mode == "emergency":
        level = "EMERGENCY"
        # 紧急时：证据不足则更强提醒
        strong_warning = (
            len(kb_docs) < max(1, settings.MIN_DOCS_REQUIRED // 2)
            and (vision_conf is None or vision_conf < 0.6)
        )

        suff = {
            "mode": mode,
            "level": level,
            "strong_warning": strong_warning,
            "missing": missing,
            "followup_questions": followup[:3],
            "kb_docs_len": len(kb_docs),
            "web_facts_len": len(web_facts),
            "vision_confidence": vision_conf,
            "red_flags": red_flags,
        }

    else:
        # ===== hybrid/normal：做“够不够回答”判断 =====
        kb_ok = len(kb_docs) >= settings.MIN_DOCS_REQUIRED
        vision_ok = (vision_conf is None) or (vision_conf >= 0.6)  # None 表示模型没给，暂时不扣分
        web_ok = len(web_facts) > 0

        if kb_ok:
            level = "ENOUGH"
        elif vision_ok or web_ok:
            level = "PARTIAL"
        else:
            level = "INSUFFICIENT"

        suff = {
            "mode": mode,
            "level": level,
            "missing": missing,
            "followup_questions": followup[:3] if level != "ENOUGH" else [],
            "kb_docs_len": len(kb_docs),
            "web_facts_len": len(web_facts),
            "vision_confidence": vision_conf,
        }

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    decision_trace.append({
        "node": "sufficiency_judge_node",
        "sufficiency": suff,
    })

    logger.info(f"sufficiency_judge_node: mode={mode} level={suff.get('level')}")

    return {
        **state,
        "sufficiency": suff,
        "decision_trace": decision_trace,
    }

