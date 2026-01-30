import json
from loguru import logger
from langchain_core.messages import HumanMessage
from app.agent.state import AgentState
from app.llm import get_llm
from app.agent.prompts import RESCUE_ACTION_JUDGE_PROMPT
from app.mcp.map.mcp import MapMCP


def rescue_action_judge(state: AgentState) -> AgentState:
    llm = get_llm().llm

    query = state.get("query", "")
    answer = state.get("response", "")
    enable_map = state.get("enable_map", False)

    # 不允许调用地图
    if not enable_map:
        return state

    prompt = RESCUE_ACTION_JUDGE_PROMPT.format(
        query=query,
        answer=answer
    )

    resp = llm.invoke([HumanMessage(content=prompt)])

    try:
        decision = json.loads(resp.content)
        need_map = bool(decision.get("need_map", False))

    except Exception as e:
        logger.warning(f"ActionJudge 解析失败，默认不调用 Map: {e}")
        need_map = False

    logger.info(
        f"RescueActionJudge: need_map={need_map}"
    )

    if need_map:
        map_mcp = MapMCP()
        address = state.get("location")

        radius = 5

        # 调用 MapMCP
        result = map_mcp.invoke(
            address=address,
            resource_type="hospital",
            radius_km=radius,
            max_results=3
        )
        return {
            **state,
            "map_result": result.get("resources", []) if enable_map else None
        }
    else:
        return state
