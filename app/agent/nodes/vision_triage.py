from __future__ import annotations
import json
import re
from typing import Any, Optional
import requests
from loguru import logger

from app.agent.prompts import VISION_TRIAGE_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.config import settings

_DEFAULT_VISION_FACTS: dict = {
    "animal_type": "unknown",
    "summary": "未能从图片获得可靠伤情信息，请结合文字描述补充症状。",
    "injuries": [],
    "urgency_level": "MEDIUM",
    "red_flags": [],
    "confidence": 0.2,
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _normalize_urgency(level: Any) -> str:
    if not level:
        return "MEDIUM"
    s = str(level).strip().upper()
    if s in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return s
    mapping = {
        "紧急": "HIGH",
        "非常紧急": "CRITICAL",
        "一般": "MEDIUM",
        "轻微": "LOW",
        "严重": "HIGH",
    }
    return mapping.get(s, "MEDIUM")


def _normalize_animal_type(v: Any) -> str:
    if not v:
        return "unknown"
    s = str(v).strip().lower()
    if s in {"cat", "猫"}:
        return "cat"
    if s in {"dog", "犬", "狗"}:
        return "dog"
    return "unknown"


def _normalize_red_flags(v: Any) -> list[str]:
    if not v:
        return []
    if isinstance(v, list):
        out: list[str] = []
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
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    return []


def _validate_vision_facts(obj: Any) -> dict:
    """
    将模型输出规范成固定结构，避免后续 KeyError。
    """
    if not isinstance(obj, dict):
        return dict(_DEFAULT_VISION_FACTS)

    animal_type = _normalize_animal_type(obj.get("animal_type"))
    summary = _clean_text(obj.get("summary")) or _DEFAULT_VISION_FACTS["summary"]

    injuries = obj.get("injuries")
    if not isinstance(injuries, list):
        injuries = []

    urgency_level = _normalize_urgency(obj.get("urgency_level"))
    red_flags = _normalize_red_flags(obj.get("red_flags"))
    confidence = _clamp(_safe_float(obj.get("confidence", 0.2), 0.2), 0.0, 1.0)

    return {
        "animal_type": animal_type,
        "summary": summary,
        "injuries": injuries,
        "urgency_level": urgency_level,
        "red_flags": red_flags,
        "confidence": confidence,
    }


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    从模型返回文本中提取第一个 JSON 对象字符串，增强鲁棒性。
    允许模型输出：
    - 纯 JSON
    - 前后带解释文字/代码块
    """
    if not text:
        return None

    # 1) 去掉 on ``` 代码块包裹
    codeblock = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if codeblock:
        candidate = codeblock.group(1).strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

    # 2) 直接找第一个 { ... }（贪婪可能过头，这里尽量取“最外层”）
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start: end + 1].strip()
        return candidate

    return None


def _call_vision_model_by_url(image_url: str, prompt: str) -> dict:
    """
    DashScope OpenAI-compatible 多模态调用（A1: image_url）
    """
    if not settings.VISION_BASE_URL or not settings.VISION_API_KEY or not settings.VISION_MODEL:
        raise RuntimeError("Vision API not configured. Please set VISION_BASE_URL/VISION_API_KEY/VISION_MODEL in .env")

    url = settings.VISION_BASE_URL + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.VISION_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.VISION_MODEL,  # qwen3-vl-plus
        "temperature": 0,  # 强烈建议 0，保证 JSON 稳定
        "max_tokens": 800,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=settings.VISION_TIMEOUT_SEC)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]

    json_str = _extract_first_json_object(content)
    if not json_str:
        raise ValueError(f"Vision model output has no JSON object. Raw content: {content[:200]}...")

    return json.loads(json_str)


def vision_triage(state: AgentState) -> AgentState:
    """
    vision_triage_node：图片伤情分诊（image_id 为 URL）

    输入：
    - image_ids: list[str]  (其中每个元素都是图片URL)
    - rewrite_query/normalized_query/query（作为参考）

    输出：
    - vision_facts: dict
    - urgency_level: str
    - red_flags: list[str]
    - decision_trace: list[dict] 增加一条记录
    """
    image_ids = state.get("image_ids") or []

    # 没有图片
    if not isinstance(image_ids, list) or len(image_ids) == 0:
        return {
            **state,
            "vision_facts": None,
            "urgency_level": None,
            "red_flags": [],
        }

    # 有图片
    image_url = _clean_text(image_ids[0])  # todo: 后续扩展为处理多张图片
    if not image_url:
        return {
            **state,
            "vision_facts": None,
            "urgency_level": None,
            "red_flags": [],
        }

    q = state.get("rewrite_query") or state.get("normalized_query") or state.get("query")
    prompt = VISION_TRIAGE_PROMPT_TEMPLATE.format(query=q)

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    try:
        raw = _call_vision_model_by_url(image_url=image_url, prompt=prompt)
        vf = _validate_vision_facts(raw)

        decision_trace.append({
            "node": "vision_triage_node",
            "status": "ok",
            "image_url": image_url,
            "urgency_level": vf["urgency_level"],
            "red_flags": vf["red_flags"],
            "confidence": vf["confidence"],
        })

        logger.info(
            f"vision_triage_node: urgency={vf['urgency_level']} "
            f"red_flags={vf['red_flags']} conf={vf['confidence']}"
        )

        return {
            **state,
            "vision_facts": vf,
            "urgency_level": vf["urgency_level"],
            "red_flags": vf["red_flags"],
            "decision_trace": decision_trace,
        }

    except Exception as e:
        logger.exception(f"vision_triage_node failed: {e}")

        vf = dict(_DEFAULT_VISION_FACTS)
        vf["summary"] = "图片分析失败（视觉服务异常或输出不可解析）。请补充文字描述症状。"
        vf = _validate_vision_facts(vf)

        decision_trace.append({
            "node": "vision_triage_node",
            "status": "fallback_exception",
            "image_url": image_url,
            "error": str(e),
            "urgency_level": vf["urgency_level"],
            "red_flags": vf["red_flags"],
            "confidence": vf["confidence"],
        })

        return {
            **state,
            "vision_facts": vf,
            "urgency_level": vf["urgency_level"],
            "red_flags": vf["red_flags"],
            "decision_trace": decision_trace,
        }


if __name__ == "__main__":
    # 你可在本地用一个可访问的图片URL做自测
    demo_state: AgentState = {
        "image_ids": [
            "https://qcloud.dpfile.com/pc/2yCl0myww0xMAuBmOMKSzr2PjWcSwVRWokoVmwHS45PPtsyGgKBNWJSqduoKO-QQ.jpg"],
        "normalized_query": "这只猫的伤严不严重？",
        "decision_trace": [],
    }
    out = vision_triage(demo_state)
    print(out.get("urgency_level"), out.get("red_flags"))
    print(out.get("vision_facts"))
