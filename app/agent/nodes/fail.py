from app.agent.state import AgentState


def fail(state: AgentState) -> AgentState:
    return {
        **state,
        "response": (
            "抱歉，目前知识库和网络上中暂时没有找到足够可靠的信息来回答你的问题。"
            "你可以尝试换一种问法，或者提供更多具体细节。"
        )
    }
