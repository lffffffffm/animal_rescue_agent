from typing import Any
from loguru import logger
from app.agent.prompts import DEFAULT_QUERY_WITH_IMAGE, DEFAULT_QUERY_NO_INPUT
from app.agent.state import AgentState


def _clean_text(v: Any) -> str:
    """清洗输入query"""
    if v is None:
        return ""
    if not isinstance(v, str):
        v = str(v)
    return v.strip()


def _normalize_image_ids(v: Any) -> list[str]:
    """
    这里不做有效性校验，只保证是 list[str]。
    """
    if not v:
        return []
    if isinstance(v, str):
        # 允许传单个 image_id
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            if x is None:
                continue
            if isinstance(x, str):
                s = x.strip()
                if s:
                    out.append(s)
            else:
                s = str(x).strip()
                if s:
                    out.append(s)
        return out
    return []


def _normalize_radius_km(v: Any, default: int = 5, min_km: int = 1, max_km: int = 20) -> int:
    """
    地图半径：做一个安全的 clamp，避免传 999 这种。
    """
    if v is None or v == "":
        return default
    try:
        r = int(v)
    except Exception:
        return default

    if r < min_km:
        return min_km
    if r > max_km:
        return max_km
    return r


def _normalize_chat_history(v: Any) -> list[tuple[str, str]]:
    """
    目标：返回 list[tuple[str,str]]，并尽量容错不同格式。
    接受的输入可能是：
    - None
    - [(role, content), ...]
    - [{"role": "...", "content": "..."}, ...]
    - [{"user": "...", "assistant": "..."}, ...]  (尽量兼容)
    - 其他乱格式（丢弃）
    """
    if not v:
        return []

    if not isinstance(v, list):
        return []

    normalized: list[tuple[str, str]] = []

    for item in v:
        # (role, content)
        if isinstance(item, tuple) and len(item) == 2:
            role = _clean_text(item[0])
            content = _clean_text(item[1])
            if role and content:
                normalized.append((role, content))
            continue

        # {"role": "...", "content": "..."}
        if isinstance(item, dict):
            if "role" in item and "content" in item:
                role = _clean_text(item.get("role"))
                content = _clean_text(item.get("content"))
                if role and content:
                    normalized.append((role, content))
                continue

            # {"user": "...", "assistant": "..."} 这种也尽量拆成两条
            u = item.get("user")
            a = item.get("assistant")
            if u:
                normalized.append(("user", _clean_text(u)))
            if a:
                normalized.append(("assistant", _clean_text(a)))
            continue

        # 其他类型：忽略
        continue

    return normalized


def _to_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return default


def normalize_input(state: AgentState) -> AgentState:
    """
    normalize_input_node：Agent 入口防呆层/适配层

    目标：
    - 统一 query/chat_history/开关/定位/半径/图片列表 的格式
    - 生成 normalized_query，保证后续节点不用担心空值
    - 初始化 decision_trace（用于可解释与调试）
    """
    raw_query = _clean_text(state.get("query"))
    image_ids = _normalize_image_ids(state.get("image_ids"))

    # 生成 normalized_query（支持“只传图不传字”）
    if raw_query:
        normalized_query = raw_query
    else:
        normalized_query = DEFAULT_QUERY_WITH_IMAGE if image_ids else DEFAULT_QUERY_NO_INPUT

    chat_history = _normalize_chat_history(state.get("chat_history"))

    enable_web_search = _to_bool(state.get("enable_web_search"), default=False)
    enable_map = _to_bool(state.get("enable_map"), default=False)

    location = _clean_text(state.get("location")) or None
    radius_km = _normalize_radius_km(state.get("radius_km"), default=5)

    decision_trace = state.get("decision_trace") or []
    if not isinstance(decision_trace, list):
        decision_trace = []

    decision_trace.append({
        "node": "normalize_input_node",
        "raw_query_empty": not bool(raw_query),
        "normalized_query": normalized_query,
        "chat_history_len": len(chat_history),
        "has_images": bool(image_ids),
        "enable_web_search": enable_web_search,
        "enable_map": enable_map,
        "has_location": bool(location),
        "radius_km": radius_km,
    })

    logger.info(
        "normalize_input_node: "
        f"query_len={len(normalized_query)} "
        f"history={len(chat_history)} "
        f"images={len(image_ids)} "
        f"web={enable_web_search} map={enable_map} "
        f"location={'yes' if location else 'no'} radius_km={radius_km}"
    )

    return {
        **state,
        "normalized_query": normalized_query,
        "query": raw_query or None,  # 保留原 query（可空）
        "chat_history": chat_history,
        "image_ids": image_ids,
        "enable_web_search": enable_web_search,
        "enable_map": enable_map,
        "location": location,
        "radius_km": radius_km,
        # 追踪
        "decision_trace": decision_trace,
    }


if __name__ == "__main__":
    # 用于快速本地自测 normalize_input_node（不依赖 graph）
    cases: list[tuple[str, dict]] = [
        (
            "case1: 纯文本 + 开关为字符串",
            {
                "query": "  猫受伤流血怎么办？  ",
                "chat_history": [],
                "enable_web_search": "true",
                "enable_map": "false",
                "location": "  北京  ",
                "radius_km": "15",
                "decision_trace": [],
            },
        ),
        (
            "case2: 仅图片（无query）",
            {
                "query": "",
                "image_ids": ["https://example.com/cat.png"],
                "chat_history": None,
                "enable_web_search": False,
                "enable_map": True,
                "location": "上海",
                "radius_km": None,
                "decision_trace": [],
            },
        ),
        (
            "case3: 脏 chat_history（dict/tuple混合）",
            {
                "query": "它严重吗？",
                "chat_history": [
                    {"role": "user", "content": "我捡到一只猫"},
                    {"role": "assistant", "content": "它有什么症状？"},
                    ("user", "它严重吗？"),
                    {"user": "我在北京", "assistant": "好的"},
                ],
                "enable_web_search": 1,
                "enable_map": 0,
                "location": None,
                "radius_km": 999,
                "decision_trace": [],
            },
        ),
    ]

    for name, st in cases:
        print("=" * 30)
        print(name)
        out = normalize_input(st)  # type: ignore
        print("normalized_query:", out.get("normalized_query"))
        print("query:", out.get("query"))
        print("chat_history:", out.get("chat_history"))
        print("image_ids:", out.get("image_ids"))
        print("enable_web_search:", out.get("enable_web_search"))
        print("enable_map:", out.get("enable_map"))
        print("location:", out.get("location"))
        print("radius_km:", out.get("radius_km"))
        print("decision_trace_last:", (out.get("decision_trace") or [])[-1])
