import re
import json
from typing import Any, Optional, List


def clean_text(v: Any) -> str:
    """清洗输入文本，去空并转为字符串"""
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def extract_first_json_object(text: str) -> Optional[str]:
    """从文本中提取第一个完整的 JSON 对象"""
    if not text:
        return None

    # 1. 优先寻找 Markdown 代码块包裹的 JSON
    codeblock = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if codeblock:
        candidate = codeblock.group(1).strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

    # 2. 备选方案：寻找第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start: end + 1].strip()

    return None


def normalize_urgency(level: Any) -> str:
    """统一紧急程度标识：critical, common, info"""
    if not level:
        return "common"
    s = str(level).strip().lower()
    if s in {"info", "common", "critical"}:
        return s

    # 中文映射
    mapping = {
        "紧急": "critical",
        "高": "critical",
        "一般": "common",
        "中": "common",
        "轻微": "info",
        "低": "info",
    }
    return mapping.get(s, "common")


def normalize_red_flags(v: Any) -> List[str]:
    """统一危险信号列表格式"""
    if not v:
        return []
    if isinstance(v, list):
        out = [clean_text(x) for x in v if clean_text(x)]
        return list(dict.fromkeys(out))  # 去重且保序
    if isinstance(v, str):
        s = clean_text(v)
        return [s] if s else []
    return []
