from loguru import logger
from app.agent.state import AgentState
from app.config import settings


def rejudge(state: AgentState) -> str:
    """
    ReJudge 节点（Evidence Judge）：
    判断 merge 后的证据是否足以支撑生成回答

    返回：
        - "generate"
        - "low_confidence_generate"
        - "fail"
    """

    merged_docs = state.get("merged_docs", [])

    logger.info(f"ReJudge：merged_docs 数量 = {len(merged_docs)}")

    # ① 完全没有证据
    if not merged_docs:
        logger.warning("ReJudge 判定：无任何证据")
        return "fail"

    # ② 统计高可信证据
    high_conf_docs = []
    low_conf_docs = []

    for doc in merged_docs:
        confidence = doc.get("confidence")

        if confidence is None:
            high_conf_docs.append(doc)
        elif confidence >= settings.MIN_EVIDENCE_CONFIDENCE:
            high_conf_docs.append(doc)
        else:
            low_conf_docs.append(doc)

    logger.info(
        f"ReJudge：高可信={len(high_conf_docs)}, 低可信={len(low_conf_docs)}"
    )

    # ③ 至少有一条高可信证据 → 正常生成
    if len(high_conf_docs) >= settings.MIN_HIGH_CONF_DOCS:
        return "rescue_action_judge"

    # ④ 只有低可信 web 证据 → 降级生成
    return "low_confidence_generate"
