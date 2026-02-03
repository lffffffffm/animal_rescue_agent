from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from loguru import logger

from app.agent.state import AgentState
from app.agent.prompts import FINAL_RESPONSE_PROMPT_TEMPLATE
from string import Template
from app.llm import get_llm


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _build_context(state: AgentState) -> str:
    """将所有证据打包成一个 context 字符串，供 LLM 参考。"""
    context_parts: list[str] = []

    # 1. 视觉证据
    vf = state.get("vision_facts")
    if vf and isinstance(vf, dict):
        summary = _clean_text(vf.get("summary"))
        if summary:
            context_parts.append(f"### 图片观察\n- {summary}")

    # 2. 知识库证据
    kb_docs = state.get("kb_docs")
    if kb_docs and isinstance(kb_docs, list):
        kb_texts = []
        for i, doc in enumerate(kb_docs):
            if isinstance(doc, Document) and doc.page_content:
                source = doc.metadata.get("source", "未知来源")
                kb_texts.append(f"[{i + 1}] (来源: {source})\n{doc.page_content}")
        if kb_texts:
            context_parts.append("### 知识库参考资料\n" + "\n".join(kb_texts))

    # 3. 网络搜索证据
    web_facts = state.get("web_facts")
    if web_facts and isinstance(web_facts, list):
        web_texts = []
        for i, fact in enumerate(web_facts):
            if isinstance(fact, dict) and fact.get("content"):
                source = fact.get("source", "网络")
                url = fact.get("url", "")
                web_texts.append(f"[{i + 1}] (来源: {source}, URL: {url})\n{fact['content']}")
        if web_texts:
            context_parts.append("### 网络搜索结果\n" + "\n".join(web_texts))

    # 4. 地图资源
    map_result = state.get("map_result")
    if map_result and isinstance(map_result, list):
        map_texts = []
        for i, place in enumerate(map_result):
            if isinstance(place, dict):
                name = _clean_text(place.get("name"))
                address = _clean_text(place.get("address"))
                tel = _clean_text(place.get("tel"))
                if name:
                    map_texts.append(f"- {name} (地址: {address or '未知'}, 电话: {tel or '无'})")
        if map_texts:
            context_parts.append("### 附近救助资源\n" + "\n".join(map_texts))

    if not context_parts:
        return "无可用参考资料。"

    return "\n\n".join(context_parts)


def _generate_instruction(state: AgentState) -> str:
    """根据场景动态生成回答指令。"""
    mode = (state.get("gate") or {}).get("mode", "normal")
    suff = state.get("sufficiency") or {}
    suff_level = (suff.get("level") or "").upper()
    followups = suff.get("followup_questions") or []

    instructions: list[str] = [
        "1. 严格依据【参考资料】回答，不得编造、补充或假设。",
        "2. 回答需准确、清晰、结构化，优先使用分点说明。",
        "3. 全程使用中文回答，风格专业、冷静、富有同情心。",
        "4. 不要使用“作为AI模型”之类的表述。",
    ]

    if mode == "emergency":
        instructions.extend([
            "5. **最高优先级**：立即从【参考资料】中提炼出【立即可做】的急救步骤清单，语言必须直接、清晰。",
            "6. 如果资料中有【附近救助资源】，请在回答末尾清晰列出。",
            "7. 附带强烈的安全提醒，敦促用户尽快就医。",
        ])
        if suff.get("strong_warning"):
            instructions.append("8. 在开头强调【信息有限但可能存在较高风险】，敦促用户不要等待。")

    elif mode == "hybrid":
        instructions.extend([
            "5. **先**给出一个简短的【安全提醒】，告知用户在何种情况下应立即就医。",
            "6. **然后**，基于【参考资料】对用户的问题进行科普解释，可以探讨多种可能性。",
            "7. **明确指出**：由于是线上咨询/非真实场景，结论存在不确定性。",
        ])
        if suff_level in {"PARTIAL", "INSUFFICIENT"} and followups:
            instructions.append("8. 在回答末尾，礼貌地提出以下【关键补充信息】问题，以帮助更准确地判断：\n" + "\n".join(
                [f"- {q}" for q in followups]))

    else:  # normal
        if suff_level == "INSUFFICIENT":
            instructions.extend([
                "5. **不要猜测答案**。明确告知用户【当前信息不足】。",
                "6. 以礼貌、引导的方式，提出以下问题以获取更多信息：\n" + "\n".join([f"- {q}" for q in followups]),
            ])
        elif suff_level == "PARTIAL":
            instructions.extend([
                "5. 基于有限的【参考资料】给出一个保守的、倾向性的建议。",
                "6. **明确说明**你的回答存在不确定性。",
                "7. 在结尾附上需要补充的问题，以获得更准确的建议。",
            ])
        else:  # ENOUGH
            instructions.append("5. 提供一个全面、自信的回答。")

    return "\n".join(instructions)


def respond(state: AgentState) -> AgentState:
    """
    respond_node (LLM驱动版)：
    1. 打包所有证据 (context)
    2. 动态生成指令 (instruction)
    3. 调用 LLM 生成最终回复
    4. 失败时回退到安全模板
    """
    query = _clean_text(state.get("rewrite_query") or state.get("normalized_query") or state.get("query"))
    mode = (state.get("gate") or {}).get("mode", "normal")

    # 1. 打包证据
    context = _build_context(state)

    # 2. 生成指令
    instruction = _generate_instruction(state)

    # 3. 调用 LLM
    try:
        # 使用 Template.safe_substitute 避免花括号冲突
        prompt = FINAL_RESPONSE_PROMPT_TEMPLATE.format(
            context=context,
            query=query,
            instruction=instruction
        )
        llm = get_llm().llm
        resp = llm.invoke([HumanMessage(content=prompt)])
        response = (resp.content or "").strip()

        if not response:
            raise ValueError("LLM returned empty response.")

        logger.info(f"respond_node (LLM): mode={mode} response_len={len(response)}")

    except Exception as e:
        logger.exception(f"respond_node (LLM) failed: {e}. Falling back to template.")
        # 4. 失败兜底：回退到安全的模板回复
        if mode == "emergency":
            response = "【紧急情况】检测到高风险信号，请立即行动！\n1. 确保自身安全。\n2. 对动物进行必要的初步处理（如止血、保暖）。\n3. 尽快联系或送往专业兽医机构。"
        else:
            response = "抱歉，处理您的问题时遇到了一些麻烦。请检查您的输入，或稍后重试。如果情况紧急，请直接联系兽医。"

    decision_trace = state.get("decision_trace") or []
    decision_trace.append({
        "node": "respond_node",
        "mode": mode,
        "sufficiency_level": (state.get("sufficiency") or {}).get("level"),
        "used_llm": True,
    })

    return {
        **state,
        "response": response,
        "decision_trace": decision_trace,
    }
