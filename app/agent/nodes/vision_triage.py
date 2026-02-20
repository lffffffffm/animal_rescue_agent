from __future__ import annotations
import json
from typing import Any, Optional
import requests
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from loguru import logger

from app.agent.prompts import VISION_TRIAGE_PROMPT_TEMPLATE, VISION_TRIAGE_PROMPT_TEMPLATE_WITHOUT_IMAGE
from app.agent.state import AgentState
from app.config import settings
from app.llm import get_llm
from app.utils.common import clean_text, extract_first_json_object, normalize_urgency, normalize_red_flags

_DEFAULT_VISION_FACTS: dict = {
    "species": "uncertain",
    "summary": "未能从图片获得可靠伤情信息，请结合文字描述补充症状。",
    "injuries": [],
    "urgency": "common",
    "red_flags": [],
    "confidence": 0.2,
}

def _validate_vision_facts(obj: Any) -> dict:
    """将模型输出规范成固定结构，并应用通用归一化逻辑"""
    if not isinstance(obj, dict):
        return dict(_DEFAULT_VISION_FACTS)

    # 提取并清洗字段
    species = clean_text(obj.get("species")) or "uncertain"
    breed = clean_text(obj.get("breed")) or None

    try:
        breed_confidence = max(0.0, min(1.0, float(obj.get("breed_confidence", 0.0))))
    except (TypeError, ValueError):
        breed_confidence = 0.0

    summary = clean_text(obj.get("summary")) or _DEFAULT_VISION_FACTS["summary"]

    injuries = obj.get("injuries")
    if not isinstance(injuries, list):
        injuries = []

    # 使用共通工具函数归一化
    urgency = normalize_urgency(obj.get("urgency"))
    red_flags = normalize_red_flags(obj.get("red_flags"))

    try:
        confidence = max(0.0, min(1.0, float(obj.get("confidence", 0.2))))
    except (TypeError, ValueError):
        confidence = 0.2

    return {
        "species": species,
        "breed": breed,
        "breed_confidence": breed_confidence,
        "summary": summary,
        "injuries": injuries,
        "urgency": urgency,
        "red_flags": red_flags,
        "confidence": confidence,
    }

def _call_vision_model_batch(image_urls: list[str], prompt: str) -> dict:
    """批量多模态调用：单次请求发送所有图片"""
    if not settings.VISION_BASE_URL or not settings.VISION_API_KEY or not settings.VISION_MODEL:
        raise RuntimeError("Vision API 未配置")

    url = f"{settings.VISION_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.VISION_API_KEY}",
        "Content-Type": "application/json",
    }

    # 构建多图消息内容
    content_list = [{"type": "text", "text": prompt}]
    for img_url in image_urls:
        content_list.append({"type": "image_url", "image_url": {"url": img_url}})

    payload = {
        "model": settings.VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": content_list}],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=settings.VISION_TIMEOUT_SEC)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    json_str = extract_first_json_object(content)
    if not json_str:
        raise ValueError(f"Vision model output has no JSON. Raw: {content[:200]}")

    return json.loads(json_str)

def vision_triage(state: AgentState) -> AgentState:
    """vision_triage_node：支持多图批处理分诊"""
    image_ids = state.get("image_ids") or []
    decision_trace = list(state.get("decision_trace") or [])
    query = state.get("rewrite_query") or state.get("normalized_query") or state.get("query")

    # 1. 无图片场景：走语义分诊
    if not image_ids:
        llm = get_llm().llm
        prompt = PromptTemplate(
            template=VISION_TRIAGE_PROMPT_TEMPLATE_WITHOUT_IMAGE,
            input_variables=["query"],
        )
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"query": query})

        vf = _validate_vision_facts(result)
        decision_trace.append({
            "node": "vision_triage_node",
            "status": "ok_no_image",
            "urgency": vf["urgency"],
            "red_flags": vf["red_flags"]
        })
        logger.info(f"vision_triage_node: ok_no_image, vision_facts: {vf}")
        return {**state, "vision_facts": vf, "urgency": vf["urgency"], "red_flags": vf["red_flags"],
                "decision_trace": decision_trace}

    # 2. 有图片场景：执行批量视觉识别
    try:
        prompt = VISION_TRIAGE_PROMPT_TEMPLATE.format(query=query)
        # 过滤空链接并去重
        valid_urls = list(set(clean_text(url) for url in image_ids if clean_text(url)))

        if not valid_urls:
            raise ValueError("没有有效的图片URL")

        # 单次请求发送所有图片
        raw_result = _call_vision_model_batch(valid_urls, prompt)
        vf = _validate_vision_facts(raw_result)

        decision_trace.append({
            "node": "vision_triage_node",
            "status": "ok_batch",
            "image_count": len(valid_urls),
            "urgency": vf["urgency"],
            "red_flags": vf["red_flags"]
        })
        logger.info(f"vision_triage_node: ok_batch, image_count: {len(valid_urls)}, vision_facts: {vf}")
        return {
            **state,
            "vision_facts": vf,
            "urgency": vf["urgency"],
            "red_flags": vf["red_flags"],
            "decision_trace": decision_trace
        }

    except Exception as e:
        logger.exception(f"vision_triage_node failed: {e}")
        vf = dict(_DEFAULT_VISION_FACTS)
        vf["summary"] = f"图片分析失败: {str(e)}。请补充文字描述。"

        decision_trace.append({
            "node": "vision_triage_node",
            "status": "error",
            "error": str(e)
        })
        return {**state, "vision_facts": vf, "urgency": vf["urgency"], "red_flags": vf["red_flags"],
                "decision_trace": decision_trace}

if __name__ == "__main__":
    # 模拟多图测试
    import os
    
    # 确保本地测试时不走代理（如有必要）
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"

    # 准备测试数据
    test_state: AgentState = {
        "query": "这几张图片里的动物是什么",
        "image_ids": [
            'https://image-bucket-lfm-1402311803.cos.ap-guangzhou.myqcloud.com/uploads/2026/02/20/0347155d0903440c810d7cba6af9f3f1.jpg',
            'https://image-bucket-lfm-1402311803.cos.ap-guangzhou.myqcloud.com/uploads/2026/02/20/2727f9eabcad4c0aa4fd7ae9ea75b9f3.jpg'
        ],
        "decision_trace": []
    }

    print("--- 开始多图分诊测试 ---")
    try:
        final_result = vision_triage(test_state)
        print("\n[测试结果]")
        print(f"紧急程度: {final_result['urgency']}")
        print(f"危险信号: {final_result['red_flags']}")
        print(f"视觉摘要: {final_result['vision_facts']['summary']}")
        print(f"置信度: {final_result['vision_facts']['confidence']}")
        print("\n[决策链路]")
        for trace in final_result['decision_trace']:
            print(trace)
    except Exception as e:
        print(f"测试过程中出现异常: {e}")
