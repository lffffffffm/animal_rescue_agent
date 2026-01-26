from abc import ABC, abstractmethod
from typing import List
from langchain_core.messages import BaseMessage


class BaseChatModel(ABC):

    @abstractmethod
    def invoke(self, messages: List[BaseMessage]) -> str:
        pass
