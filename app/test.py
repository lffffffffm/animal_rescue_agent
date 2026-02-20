from qdrant_client import QdrantClient
import os

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

client = QdrantClient(url="http://127.0.0.1:6333")

collection_name = "animal_rescue_collection"

points, _ = client.scroll(
    collection_name=collection_name,
    limit=5000,
    with_payload=True,
    with_vectors=False,
)

species_set = {
    point.payload.get("metadata", {}).get("urgency")
    for point in points
    if point.payload.get("metadata", {}).get("urgency")
}

print('|'.join(species_set))
