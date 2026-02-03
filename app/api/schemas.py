from pydantic import BaseModel, Field
from typing import Optional, List, Literal

"""
用户相关接口
"""


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


"""健康检查"""


class HealthStatusResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


"""chat接口"""


class AnimalRescueQueryRequest(BaseModel):
    """
    动物救助查询请求模型
    """
    query: str = Field(..., description="用户问题")

    # 会话：不传则后端新建；传入则追加到同一会话
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID（用于多轮对话）"
    )

    # 历史对话（给 Agent 用）
    # 约定为字符串列表：['user: ...', 'assistant: ...', ...]
    # 历史对话，支持多种格式：['user: ...', 'assistant: ...'] 或 [{"role":"user","content":"..."}, ...]
    chat_history: Optional[List] = Field(
        default_factory=list,
        description="历史对话"
    )
    # Agent 行为控制
    enable_web_search: bool = Field(
        default=False,
        description="是否允许联网搜索"
    )
    enable_map: bool = Field(
        default=False,
        description="是否允许调用地图服务")
    # 地理信息（给 Map MCP 用）
    location: Optional[str] = Field(
        default=None,
        description="城市或地址，例如：深圳"
    )
    radius_km: int = Field(
        default=5,
        description="地图搜索半径（公里）"
    )

    # 图片输入（先上传拿 image_id，再在 query 时引用）
    # 最多支持 4 张
    image_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="图片ID列表（最多4张）"
    )


class RescueResource(BaseModel):
    """救助资源"""
    name: str
    address: str
    tel: Optional[str] = None
    distance_m: Optional[int] = None


class Evidence(BaseModel):
    type: Literal["kb", "web"]
    source: str
    confidence: Optional[float] = None
    url: Optional[str] = None
    content: str


class AnimalRescueQueryResponse(BaseModel):
    answer: str

    # Agent 行为回溯
    used_web_search: bool
    used_map: bool

    # 结构化证据
    evidences: List[Evidence]

    # 地图资源（可选）
    rescue_resources: Optional[List[RescueResource]] = None
