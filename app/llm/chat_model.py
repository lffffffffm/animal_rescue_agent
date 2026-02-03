from typing import List
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
        )

    def invoke(self, messages: List[BaseMessage]) -> str:
        response = self.llm.invoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

