from qdrant_client import QdrantClient
import os

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

client = QdrantClient(url="http://127.0.0.1:6333")

collection_name = "animal_rescue_collection"

categories = set()

scroll_result = client.scroll(
    collection_name=collection_name,
    limit=1000,        # 每批拉多少
    with_payload=True,
    with_vectors=False
)

points, next_page_offset = scroll_result

while points:
    for point in points:
        payload = point.payload
        category = payload.get("metadata", {}).get("category")
        if category:
            categories.add(category)

    if not next_page_offset:
        break

    points, next_page_offset = client.scroll(
        collection_name=collection_name,
        offset=next_page_offset,
        limit=1000,
        with_payload=True,
        with_vectors=False
    )

print(categories)
