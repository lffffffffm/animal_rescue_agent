from typing import List, Optional
from typing_extensions import TypedDict
from langchain.schema import Document


class AgentState(TypedDict, total=False):
    # ===== 输入字段 =====
    query: Optional[str]
    chat_history: Optional[list[tuple[str, str]]]
    image_ids: Optional[list[str]]          # A1：图片URL列表
    enable_web_search: bool
    enable_map: bool
    location: Optional[str]
    radius_km: Optional[int]

    # ===== normalize/rewrite =====
    normalized_query: str
    rewrite_query: Optional[str]

    # ===== vision =====
    vision_facts: Optional[dict]
    urgency_level: Optional[str]            # LOW/MEDIUM/HIGH/CRITICAL
    red_flags: Optional[list[str]]          # e.g. heavy_bleeding/respiratory_distress

    # ===== intent/gate =====
    user_intent: str                        # real_help/learn_only/unclear
    gate: Optional[dict]                    # {mode, tools, map_params, reasons}

    # ===== evidence collection =====
    force_top_k: Optional[int]              # 用于控制 retrieve 的 top_k
    retry_count: int                        # KB 重试/扩大召回轮数（你现在会写回）
    kb_docs: List[Document]
    web_facts: List[dict]
    map_result: Optional[object]            # 兼容 list[dict] 或 dict（看 MapMCP 返回）

    # ===== sufficiency =====
    sufficiency: Optional[dict]             # {level, strong_warning, followup_questions, ...}

    # ===== old flow / optional =====
    merged_docs: List[dict]                 # 旧流程字段（如不用可删）
    evidences: Optional[list[dict]]         # 未来 evidence_pack_node 可用

    # ===== output =====
    response: Optional[str]
    decision_trace: list[dict]