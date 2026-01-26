# app/mcp/web_search/schemas.py
from typing import List
from pydantic import BaseModel


class WebFact(BaseModel):
    content: str
    source: str
    url: str
    confidence: float


class WebSearchResult(BaseModel):
    query: str
    facts: List[WebFact]
