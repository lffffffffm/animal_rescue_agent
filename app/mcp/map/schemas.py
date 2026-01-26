from typing import List
from pydantic import BaseModel


class RescueResource(BaseModel):
    name: str
    category: str
    address: str
    location: str  # "lng,lat"
    distance_m: int
    source: str = "Amap"


class MapSearchResult(BaseModel):
    query_address: str
    resource_type: str
    resources: List[RescueResource]
