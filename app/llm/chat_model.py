from typing import List, AsyncIterator
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.llm.base import BaseChatModel


class ChatModel(BaseChatModel):
    def __init__(
            self,
            model_name: str = "qwen-plus-latest",
            temperature: float = 0.3,
            max_tokens: int = 512,
    ):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            max_tokens=max_tokens,
            streaming=True,  # ⭐ 非必须，但强烈建议显式打开
        )

    # ===== 原有同步调用（不动，兼容老逻辑）=====
    def invoke(self, messages: List[BaseMessage]) -> str:
        response = self.llm.invoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

    # ===== 新增：同步流（可选）=====
    def stream(self, messages: List[BaseMessage]):
        """
        同步 token 流（for chunk in llm.stream(...)）
        """
        return self.llm.stream(messages)

    # ===== 新增：异步流（关键）=====
    async def astream(self, messages: List[BaseMessage]) -> AsyncIterator:
        """
        异步 token 流（async for chunk in llm.astream(...)）
        """
        async for chunk in self.llm.astream(messages):
            yield chunk
