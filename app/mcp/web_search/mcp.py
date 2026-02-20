from app.config import settings
from app.mcp.base import BaseMCP
from app.mcp.web_search.client import WebSearchClient
from app.mcp.web_search.normalizer import normalize_results
from app.mcp.web_search.schemas import WebSearchResult


class WebSearchMCP(BaseMCP):
    name = "web_search"
    description = """
        WebSearchMCP：用于在中文互联网上搜索权威、可靠的信息。
        
        使用场景：
        - 当本地知识库无法回答用户问题
        - 当需要补充最新或外部事实信息
        
        能力特点：
        - 仅返回可信中文网站内容（政府 / 教育 / 百科 / 知乎 / 公众号）
        - 返回结构化事实，而非原始网页
        - 每条信息包含来源和可信度评分
        - 不保证一定有结果，信息不足时会明确返回空结果
    """

    def __init__(self, api_key: str):
        self.client = WebSearchClient(api_key)
        self.allowed_domains = [
            "zhihu.com",
            "gov.cn",
            "edu.cn",
            "baike.baidu.com",
            "weibo.com",
            "mp.weixin.qq.com"
        ]

    def invoke(
            self,
            query: str,
            max_results: int = 5,
    ) -> dict:
        raw = self.client.search(
            query=query,
            domains=self.allowed_domains,
            max_results=max_results,
        )

        facts = normalize_results(raw, query)

        result = WebSearchResult(
            query=query,
            facts=facts,
        )

        return result.model_dump()


def main():
    """测试 WebSearchMCP 功能"""
    # 从环境变量获取 API 密钥
    api_key = settings.TAVILY_API_KEY

    if not api_key:
        print("❌ 未找到 TAVILY_API_KEY 环境变量，请先设置 API 密钥")
        print("💡 设置方法: TAVILY_API_KEY='your_api_key'")
        return

    # 创建 MCP 实例
    web_search_mcp = WebSearchMCP(api_key=api_key)

    # 测试查询
    test_queries = [
        "宠物狗的疫苗接种时间表",
        "流浪动物救助流程",
        "猫的日常护理注意事项"
    ]

    print("🔍 开始测试 WebSearchMCP 功能")
    print("=" * 60)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. 查询: {query}")

        try:
            results = web_search_mcp.invoke(
                query=query,
                max_results=3,
            )

            facts = results.get("facts", [])
            print(f"   找到 {len(facts)} 条结果:")

            for j, fact in enumerate(facts, 1):
                print(
                    f"     {j}. [{fact['source']}] 置信度: {fact['confidence']:.2f}"
                )
                print(f"         内容: {fact['content'][:100]}...")
                print(f"         链接: {fact['url']}")

        except Exception as e:
            print(f"   ❌ 查询失败: {str(e)}")

    print(f"\n✅ 测试完成")


if __name__ == "__main__":
    main()
