# app/agent/nodes/collect_evidence.py

from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from app.agent.state import AgentState
from app.config import settings
from app.agent.nodes.retrieve import retrieve_documents
from app.agent.nodes.rerank import rerank_documents
from app.agent.nodes.web_search import web_search_node
from app.mcp.map.mcp import MapMCP


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _get_gate(state: AgentState) -> dict:
    g = state.get("gate")
    return g if isinstance(g, dict) else {}


def _get_gate_tools(state: AgentState) -> dict:
    tools = _get_gate(state).get("tools")
    return tools if isinstance(tools, dict) else {}


def _get_map_params(state: AgentState) -> dict:
    params = _get_gate(state).get("map_params")
    return params if isinstance(params, dict) else {}


def collect_evidence(state: AgentState) -> AgentState:
    """
    collect_evidence_node：根据 gate.tools 执行工具调用（KB/Web/Map）并写回 state。

    重点：本地 KB 检索支持 retry 扩大召回：
    - MAX_RETRY = 3
    - STEP = 5
    - 每轮 top_k = settings.RETRIEVAL_TOP_K + attempt*STEP
    - 用 rerank 后保留文档数量是否 >= settings.MIN_DOCS_REQUIRED 判断“是否够用”
    """

    start = time.time()

    tools = _get_gate_tools(state)
    map_params = _get_map_params(state)

    use_kb = bool(tools.get("kb", True))
    use_web = bool(tools.get("web", False))
    use_map = bool(tools.get("map", False))

    base_query = _clean_text(state.get("rewrite_query") or state.get("normalized_query") or state.get("query"))

    # ===== 基于图片信息的 query 增强（enriched_query） =====
    # 目的：当用户文本很泛时，用 vision_facts 的结构化要点提升检索命中率。
    # 原则：
    # - 只融合短摘要 + 结构化标签（不引入新推断）
    # - 控制长度，避免稀释检索语义
    vf = state.get("vision_facts") or {}
    if not isinstance(vf, dict):
        vf = {}

    try:
        vision_conf = float(vf.get("confidence")) if vf.get("confidence") is not None else None
    except Exception:
        vision_conf = None

    animal_type = _clean_text(vf.get("animal_type"))
    urgency_level = _clean_text(vf.get("urgency_level") or state.get("urgency_level")).upper()

    red_flags = vf.get("red_flags") or state.get("red_flags") or []
    if not isinstance(red_flags, list):
        red_flags = []

    injuries = vf.get("injuries") or []
    if not isinstance(injuries, list):
        injuries = []

    # 将所有伤情要点都加入 hint
    injury_hints = []
    for injury in injuries:  # 遍历所有伤情
        if isinstance(injury, dict):
            part = _clean_text(injury.get("part"))
            itype = _clean_text(injury.get("type"))
            # 只拼接 part 和 type，避免过长
            if part or itype:
                injury_hints.append(f"{part} {itype}".strip())

    injury_hint = ", ".join(injury_hints)

    # 将所有 red_flags 添加到 hint 中
    red_flag_hint = ", ".join([_clean_text(x) for x in red_flags if _clean_text(x)])

    # 只在视觉置信度较高时增强（避免错误引导检索）
    should_enrich = (vision_conf is None) or (vision_conf >= 0.6)

    vision_hint_parts = []
    if animal_type:
        vision_hint_parts.append(f"animal={animal_type}")
    if urgency_level:
        vision_hint_parts.append(f"urgency={urgency_level}")
    if red_flag_hint:
        vision_hint_parts.append(f"red_flags={red_flag_hint}")
    if injury_hint:
        vision_hint_parts.append(f"injury={injury_hint}")

    vision_hint = " | ".join(vision_hint_parts)

    # enriched_query：主问题 + 视觉要点（短）
    query = base_query
    if should_enrich and vision_hint:
        query = f"{base_query}\n{vision_hint}"

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    kb_docs = []
    web_facts = []
    map_result = None

    kb_attempts = []
    kb_error: Optional[str] = None
    web_error: Optional[str] = None
    map_error: Optional[str] = None

    # ===== 1) KB：retrieve + rerank + retry 扩大召回 =====
    if use_kb:
        base_top_k = settings.RETRIEVAL_TOP_K
        step = 5
        max_retry = settings.MAX_RETRY

        # 创建一个可变的状态副本进行操作，确保状态不会丢失
        mutable_state = dict(state)

        for attempt in range(max_retry):
            top_k = base_top_k + attempt * step
            try:
                # 直接在 mutable_state 上更新和传递
                mutable_state["query"] = query
                mutable_state["force_top_k"] = top_k

                retrieved_state = retrieve_documents(mutable_state)
                reranked_state = rerank_documents(retrieved_state)

                # 从返回的状态中更新 mutable_state
                mutable_state.update(reranked_state)

                current_kb_docs = mutable_state.get("kb_docs", [])
                enough = len(current_kb_docs) >= settings.MIN_DOCS_REQUIRED

                kb_attempts.append({
                    "attempt": attempt + 1,
                    "top_k": top_k,
                    "kept": len(current_kb_docs),
                    "enough": enough,
                })

                if enough:
                    break

            except Exception as e:
                kb_error = str(e)
                kb_attempts.append({
                    "attempt": attempt + 1,
                    "top_k": top_k,
                    "error": kb_error,
                    "enough": False,
                })
                logger.exception("collect_evidence_node: KB 检索失败")

        # 将最终结果从 mutable_state 中提取
        kb_docs = mutable_state.get("kb_docs", [])
        final_retry_count = len(kb_attempts)
        mutable_state["retry_count"] = final_retry_count

    # ===== 2) WebSearch =====
    if use_web:
        try:
            web_state = web_search_node({**mutable_state, "query": query})
            mutable_state.update(web_state)
            web_facts = mutable_state.get("web_facts", [])
        except Exception as e:
            web_error = str(e)
            logger.exception("collect_evidence_node: WebSearch 失败")

    # ===== 3) MapSearch =====
    if use_map:
        try:
            location = _clean_text(mutable_state.get("location"))
            if not location:
                raise ValueError("location 为空，无法调用 map")

            radius_raw = map_params.get("radius_km") or mutable_state.get("radius_km") or 5
            try:
                radius_km = int(radius_raw)
            except Exception:
                radius_km = 5
            radius_km = max(1, min(20, radius_km))

            resource_type = map_params.get("resource_type") or "hospital"

            map_mcp = MapMCP()
            result = map_mcp.invoke(
                address=location,
                resource_type=resource_type,
                radius_km=radius_km,
                max_results=3,
            )

            map_result = result.get("resources", result)

        except Exception as e:
            map_error = str(e)
            logger.exception("collect_evidence_node: Map 调用失败")

    elapsed_ms = int((time.time() - start) * 1000)

    # 确保 decision_trace 是列表
    decision_trace = mutable_state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    decision_trace.append({
        "node": "collect_evidence_node",
        "use_kb": use_kb,
        "use_web": use_web,
        "use_map": use_map,
        "kb_attempts": kb_attempts,
        "kb_docs_len": len(kb_docs),
        "web_facts_len": len(web_facts),
        "map_has_result": bool(map_result),
        "kb_error": kb_error,
        "web_error": web_error,
        "map_error": map_error,
        "latency_ms": elapsed_ms,
    })

    logger.info(
        f"collect_evidence_node: kb={use_kb} web={use_web} map={use_map} "
        f"kb_docs={len(kb_docs)} web_facts={len(web_facts)} map={'yes' if map_result else 'no'} "
        f"latency_ms={elapsed_ms}"
    )

    # ✅ 正确：返回最终更新后的完整状态
    return {
        **mutable_state,
        "kb_docs": kb_docs,
        "web_facts": web_facts,
        "map_result": map_result,
        "decision_trace": decision_trace,
    }