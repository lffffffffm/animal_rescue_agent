from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from app.config import settings
from app.knowledge_base.embedding_manager import initialize_embedding_model
from qdrant_client.http import models as rest_models

_vector_store_cache = {}


class QdrantHybridStore:
    """
    Qdrant 原生 Hybrid 向量库封装（Dense + Sparse）
    """

    def __init__(
            self,
            collection_name: str = "animal_rescue_collection",
            vector_size: int = 768,
            distance: str = "Cosine",
            recreate: bool = False,
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.recreate = recreate

        # 连接 Qdrant
        if settings.QDRANT_URL:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=getattr(settings, "QDRANT_API_KEY", None),
            )
        else:
            self.client = QdrantClient(location=":memory:")

        # 配置embedding模型（离线优先，由 embedding_manager 内部读取 settings 配置）
        self.embedding_manager = initialize_embedding_model()

        # 初始化collection
        self._init_collection()

        # 创建混合检索的向量数据库
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embedding_manager.embeddings,
            sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
            retrieval_mode=RetrievalMode.HYBRID,
            sparse_vector_name="sparse",
        )

    def _init_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists and self.recreate:
            self.client.delete_collection(self.collection_name)
            logger.info(f"已删除集合 {self.collection_name}")
            exists = False

        if not exists:
            # 为混合检索创建包含密集和稀疏向量的集合
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance[self.distance.upper()],
                ),
                sparse_vectors_config={
                    "sparse": rest_models.SparseVectorParams()
                }
            )
            logger.info(f"已创建混合检索集合 {self.collection_name}")

    def add_documents(self, documents):
        # 检查输入格式并转换为Document对象
        from langchain_core.documents import Document

        if documents and isinstance(documents[0], dict):
            # 将字典格式转换为Document对象
            converted_docs = []
            for doc in documents:
                converted_docs.append(Document(
                    page_content=doc["text"],
                    metadata={
                        "source": doc.get("source", ""),
                        "tags": doc.get("tags", [])
                    }
                ))
            documents = converted_docs

        # 使用langchain-qdrant的标准方法，它会自动处理混合检索
        self.vector_store.add_documents(documents)
        logger.info(f"成功入库 {len(documents)} 条文档")

    def get_retriever(self, k: int = 5):
        return self.vector_store.as_retriever(search_kwargs={"k": k})


def get_vector_store(collection_name="animal_rescue_collection"):
    if collection_name not in _vector_store_cache:
        # bge-small-zh-v1.5 的维度是 512
        # recreate=True 会删除并重建 collection，解决维度不匹配问题
        _vector_store_cache[collection_name] = QdrantHybridStore(
            collection_name=collection_name,
            vector_size=512,  # 明确指定新维度
            recreate=False     # 强制重建
        )
    return _vector_store_cache[collection_name]
