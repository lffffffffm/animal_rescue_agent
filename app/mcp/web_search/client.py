import requests
from typing import List, Dict


class WebSearchClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"

    def search(
            self,
            query: str,
            domains: List[str],
            max_results: int = 5,
    ) -> List[Dict]:
        payload = {
            "query": query,
            "max_results": max_results,
            "include_domains": domains,
        }  # 载荷， 请求中真正携带的数据内容

        resp = requests.post(
            self.endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        resp.raise_for_status()  # 如果请求失败立刻抛出异常
        return resp.json().get("results", [])
