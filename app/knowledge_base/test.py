import os

from app.knowledge_base.vector_store import QdrantHybridStore
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

retriever = QdrantHybridStore().get_retriever(k=5, species=["cat", "uncertain"], urgency="critical")

results = retriever.invoke("如何捉猫")

for r in results:
    print(r.page_content)
    print(r.metadata)
