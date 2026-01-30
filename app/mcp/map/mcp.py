# app/mcp/map/mcp.py
from typing import Dict, List
import re
from app.config import settings
from app.mcp.base import BaseMCP
from app.mcp.map.client import AmapClient
from app.mcp.map.normalizer import normalize_pois
from app.mcp.map.schemas import MapSearchResult, RescueResource


# 不同救助资源类型对应的搜索关键词
RESOURCE_KEYWORDS: Dict[str, List[str]] = {
    "hospital": ["宠物医院", "动物医院"],
    "shelter": ["动物救助站", "流浪动物救助", "动物收容所"],
    "volunteer": ["动物保护协会", "流浪动物救助"],
    "gov": ["动物管理", "农业农村局", "城管执法"]
}


class MapMCP(BaseMCP):
    """
    Map MCP（高德地图版）

    能力说明：
    - 根据用户提供的地址（城市 / 区域 / 详细地址）
    - 查询附近的动物救助相关资源
    - 支持宠物医院、救助站、志愿组织、政府机构
    """

    name = "map_search"

    description = """
    地图 MCP（高德地图）：
    用于根据用户位置，查找附近可提供动物救助帮助的资源。

    支持的资源类型：
    - hospital：宠物医院 / 动物医院
    - shelter：动物救助站 / 收容所
    - volunteer：民间动物保护组织
    - gov：动物管理相关政府部门

    返回结构化结果（名称 / 地址 / 距离 / 联系方式），
    用于辅助救助决策，而非导航或路径规划。
    """

    def __init__(self):
        if not settings.AMAP_API_KEY:
            raise RuntimeError("❌ 未配置 AMAP_API_KEY")

        self.client = AmapClient(settings.AMAP_API_KEY)

    def _get_keywords(self, resource_type: str) -> List[str]:
        """根据资源类型获取搜索关键词"""
        return RESOURCE_KEYWORDS.get(resource_type, [])

    def invoke(
        self,
        address: str | None,
        resource_type: str = "hospital",
        radius_km: int = 5,
        max_results: int = 5,
    ) -> dict:
        """
        调用地图 MCP

        Args:
            address: 用户提供的位置（如：城市 / 区 / 详细地址）
            resource_type: 资源类型（hospital / shelter / volunteer / gov）
            radius_km: 搜索半径（公里）
            max_results: 最大返回结果数

        Returns:
            MapSearchResult（dict）
        """

        # 0️⃣ 参数兜底：address 为空时直接返回空结果（不中断 Agent）
        address = (address or "").strip()
        if not address:
            return MapSearchResult(
                query_address="",
                resource_type=resource_type,
                resources=[]
            ).model_dump()

        # 1️⃣ 校验资源类型
        keywords = self._get_keywords(resource_type)
        if not keywords:
            raise ValueError(f"不支持的资源类型: {resource_type}")

        # 2️⃣ 地址 → 经纬度 (或直接使用经纬度)
        location = ""
        # 检查 address 是否为 "lat,lon" 格式
        if re.match(r"^-?\d{1,2}\.\d+,-?\d{1,3}\.\d+$", address):
            try:
                lat, lon = address.split(',')
                location = f"{lon},{lat}"  # 高德API需要 lon,lat 格式
            except ValueError:
                location = self.client.geocode(address) # 解析失败则回退
        else:
            location = self.client.geocode(address)

        if not location:
            # 地址无法解析，直接返回空结果（不中断 Agent）
            return MapSearchResult(
                query_address=address,
                resource_type=resource_type,
                resources=[]
            ).model_dump()

        # 3️⃣ POI 搜索
        raw_pois = self.client.search_rescue_resources(
            location=location,
            keywords="|".join(keywords),
            radius=radius_km * 1000,
        )

        # 4️⃣ 结果标准化
        resources = normalize_pois(
            raw_pois,
            max_results=max_results,
            category=resource_type
        )

        # 5️⃣ 构造结构化返回
        result = MapSearchResult(
            query_address=address,
            resource_type=resource_type,
            resources=[RescueResource(**r) for r in resources]
        )

        return result.model_dump()


if __name__ == "__main__":
    mcp = MapMCP()

    test_cases = [
        ("上海市浦东新区", "hospital"),
        ("北京市海淀区", "shelter"),
        ("杭州市", "volunteer"),
    ]

    for addr, rtype in test_cases:
        print(f"\n📍 地址: {addr} | 类型: {rtype}")
        res = mcp.invoke(
            address=addr,
            resource_type=rtype,
            radius_km=5,
            max_results=3
        )
        for i, item in enumerate(res["resources"], 1):
            print(f"{i}. {item['name']} ({item['distance_m']}m)")
            print(f"   地址: {item['address']}")
            print(f"   电话: {item.get('tel')}")
