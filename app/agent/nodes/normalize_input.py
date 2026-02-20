from typing import Any
from loguru import logger
from app.agent.prompts import DEFAULT_QUERY_WITH_IMAGE, DEFAULT_QUERY_NO_INPUT
from app.agent.state import AgentState
from app.utils.common import clean_text


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
    """
    if not v:
        return []

    if not isinstance(v, list):
        return []

    normalized: list[tuple[str, str]] = []

    for item in v:
        # (role, content)
        if isinstance(item, tuple) and len(item) == 2:
            role = clean_text(item[0])
            content = clean_text(item[1])
            if role and content:
                normalized.append((role, content))
            continue

        # {"role": "...", "content": "..."}
        if isinstance(item, dict):
            if "role" in item and "content" in item:
                role = clean_text(item.get("role"))
                content = clean_text(item.get("content"))
                if role and content:
                    normalized.append((role, content))
                continue

            # {"user": "...", "assistant": "..."} 这种也尽量拆成两条
            u = item.get("user")
            a = item.get("assistant")
            if u:
                normalized.append(("user", clean_text(u)))
            if a:
                normalized.append(("assistant", clean_text(a)))
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
    """
    raw_query = clean_text(state.get("query"))
    image_ids = _normalize_image_ids(state.get("image_ids"))

    # 生成 normalized_query
    if raw_query:
        normalized_query = raw_query
    else:
        normalized_query = DEFAULT_QUERY_WITH_IMAGE if image_ids else DEFAULT_QUERY_NO_INPUT

    chat_history = _normalize_chat_history(state.get("chat_history"))

    enable_web_search = _to_bool(state.get("enable_web_search"), default=False)
    enable_map = _to_bool(state.get("enable_map"), default=False)

    location = clean_text(state.get("location")) or None
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
        "query": raw_query or None,
        "chat_history": chat_history,
        "image_ids": image_ids,
        "enable_web_search": enable_web_search,
        "enable_map": enable_map,
        "location": location,
        "radius_km": radius_km,
        "decision_trace": decision_trace,
    }
