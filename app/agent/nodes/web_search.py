from app.agent.state import AgentState
from app.mcp.web_search.mcp import WebSearchMCP
from app.config import settings
from loguru import logger

web_search_mcp = WebSearchMCP(api_key=settings.TAVILY_API_KEY)


def web_search_node(state: AgentState) -> AgentState:
    query = state.get("rewrite_query") or state["query"]

    logger.info(f"🔍 WebSearch MCP 查询: {query}")

    result = web_search_mcp.invoke(
        query=query,
        max_results=settings.WEB_SEARCH_MAX_RESULTS,
    )

    return {
        **state,
        "web_facts": result["facts"]
    }
