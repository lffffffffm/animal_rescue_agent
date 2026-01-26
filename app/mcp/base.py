# app/mcp/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMCP(ABC):
    """所有 MCP 的统一抽象"""

    name: str
    description: str

    @abstractmethod
    def invoke(self, **kwargs) -> Dict[str, Any]:
        pass
