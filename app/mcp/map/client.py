# app/mcp/map/client.py
import requests


class AmapClient:
    BASE_URL = "https://restapi.amap.com/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def geocode(self, address: str) -> str:
        """
        地址 → 经纬度
        """
        url = f"{self.BASE_URL}/geocode/geo"
        params = {
            "key": self.api_key,
            "address": address,
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        geocodes = data.get("geocodes")
        if not geocodes:
            raise ValueError("高德地理编码失败")

        return geocodes[0]["location"]  # "lng,lat"

    def search_rescue_resources(
        self,
        location: str,
        radius: int = 5000,
        keywords: str = "动物医院",
    ):
        url = f"{self.BASE_URL}/place/around"
        params = {
            "key": self.api_key,
            "location": location,
            "keywords": keywords,
            "radius": radius,
            "sortrule": "distance",
            "offset": 10,
            "extensions": "all",
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json().get("pois", [])
