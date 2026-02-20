from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from loguru import logger
from langchain_core.messages import HumanMessage
from app.agent.state import AgentState
from app.llm import get_llm
from app.utils.common import clean_text

class IntentResponse(BaseModel):
    """动物救助对话意图分类结果"""
    intent: Literal["real_help", "learn_only", "unclear"] = Field(
        description="意图分类：real_help(真实急需救助), learn_only(知识科普/假设/转发/了解情况), unclear(信息不足)"
    )
    reason: str = Field(description="分类的简要依据，包括对用户情绪或关键信息的捕捉")


def _format_chat_history(chat_history: list, limit: int = 5) -> str:
    """格式化最近几轮对话，为 LLM 提供上下文"""
    if not chat_history or not isinstance(chat_history, list):
        return "无历史对话"

    recent = chat_history[-limit:]
    lines = []
    for i, turn in enumerate(recent, 1):
        if isinstance(turn, tuple) and len(turn) == 2:
            lines.append(f"[{i}] {turn[0]}: {turn[1]}")
        elif isinstance(turn, dict):
            lines.append(f"[{i}] {turn.get('role', 'user')}: {turn.get('content', '')}")
        else:
            lines.append(f"[{i}] {str(turn)}")
    return "\n".join(lines)


def intent_classifier(state: AgentState) -> dict:
    """
    意图分类 Node：全部委托给 LLM 处理。
    使用 common.utils 统一文本清洗逻辑。
    """
    # 优先获取重写后的 Query
    query = clean_text(state.get("rewrite_query") or state.get("query") or "")
    chat_history = state.get("chat_history") or []
    decision_trace = list(state.get("decision_trace") or [])

    if not query:
        return {"user_intent": "unclear"}

    try:
        raw_llm = get_llm().llm
        structured_llm = raw_llm.with_structured_output(IntentResponse)

        prompt = f"""你是一个专业的动物救助意图分析员。请严谨判断用户当前问题的意图。

【意图定义】
1. real_help (真实救助): 
   - 用户正面临真实的动物伤病（流血、骨折、抽搐、不吃东西等）。
   - 表现出焦虑、急迫，正在寻求立即的行动建议或寻找医院。
   - 即便有错别字，只要语义指向实时求助，均属此类。

2. learn_only (知识科普/假设): 
   - 明确提到“网上看到”、“转发”、“听说”、“科普”。
   - 纯学术/原理探讨（如“为什么骨折不能动”）。
   - 假设性提问（如“如果以后遇到这种情况该怎么办”）。
   - 用户明确表示“不是实际情况”。

3. unclear (不明确): 
   - 输入过于简短、无意义或无法判断场景。

【待分析数据】
当前问题: {query}
最近上下文: 
{_format_chat_history(chat_history)}

请分析语义，直接返回 JSON 格式结果。"""

        response: IntentResponse = structured_llm.invoke([HumanMessage(content=prompt)])
        intent = response.intent
        reason = response.reason
        status = "llm_success"

    except Exception as e:
        logger.error(f"Intent Classifier Failed: {str(e)}")
        intent = "unclear"
        reason = f"LLM 推理异常: {str(e)}"
        status = "llm_fallback"

    logger.info(f"Intent: {intent} | Reason: {reason}")
    decision_trace.append({
        "node": "intent_classifier",
        "status": status,
        "intent": intent,
        "reason": reason,
    })

    return {
        "user_intent": intent,
        "decision_trace": decision_trace
    }
