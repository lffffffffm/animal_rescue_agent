from typing import List, Optional
from typing_extensions import TypedDict
from langchain.schema import Document


class AgentState(TypedDict, total=False):
    """
    LangGraph 中使用的全局状态（State）

    total=False 表示：
    - 每个字段都不是必须一次性提供
    - 由不同节点逐步补充
    """
    query: str
    chat_history: Optional[list[tuple[str, str]]]
    rewrite_query: Optional[str]
    kb_docs: List[Document]  # 本地知识库检索出的相关文档
    web_facts: List[dict]  # Web 搜索结果
    retry_count: int  # 重试次数, 用于后续循环次数的控制
    enable_web_search: bool
    merged_docs: List[dict]
    enable_map: bool  # 是否需要线下maps
    map_result: Optional[dict]  # 救助资源搜索结果
    response: Optional[str]
    location: Optional[str]  # 当前用户所在地
    radius_km: Optional[int]  # 在地图搜索的半径
