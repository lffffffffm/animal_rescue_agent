import json
from loguru import logger
from langchain_core.messages import HumanMessage
from app.agent.state import AgentState
from app.llm import get_llm
from app.agent.prompts import RESCUE_ACTION_JUDGE_PROMPT


def rescue_action_judge(state: AgentState) -> AgentState:
    llm = get_llm().llm

    query = state.get("query", "")
    answer = state.get("response", "")

    prompt = RESCUE_ACTION_JUDGE_PROMPT.format(
        query=query,
        answer=answer
    )

    resp = llm.invoke([HumanMessage(content=prompt)])

    try:
        decision = json.loads(resp.content)
        need_map = bool(decision.get("need_map", False))
        reason = decision.get("reason", "")

    except Exception as e:
        logger.warning(f"ActionJudge 解析失败，默认不调用 Map: {e}")
        need_map = False
        reason = "parse_failed"

    logger.info(
        f"RescueActionJudge: need_map={need_map}, reason={reason}"
    )

    return {
        **state,
        "need_map": need_map,
    }
