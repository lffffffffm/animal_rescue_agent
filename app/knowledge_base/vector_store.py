from typing import List
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from app.config import settings
from app.db.knowledge_model import Chunk
from app.knowledge_base.embedding_manager import initialize_embedding_model
from qdrant_client.http import models as rest_models
from langchain_core.documents import Document

_vector_store_cache = {}


class QdrantHybridStore:
    """
    Qdrant 原生 Hybrid 向量库封装（Dense + Sparse）
    """

    def __init__(
            self,
            collection_name: str = "animal_rescue_collection",
            vector_size: int = 512,  # BGE 模型默认向量维度
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
            self.client = QdrantClient(location=":memory:", host="localhost")

        # 配置embedding模型（离线优先，由 embedding_manager 内部读取 settings 配置）
        self.embedding_manager = initialize_embedding_model()

        # 初始化collection
        self._init_collection()

        # 创建混合检索的向量数据库
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embedding_manager.embeddings,  # 配置embedding模型
            sparse_embedding=FastEmbedSparse(
                model_name="Qdrant/bm25",
                cache_dir="C:/models",
                local_files_only=True
            ),
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
            logger.info(f"已初始化集合 {self.collection_name} (Size: {self.vector_size})")

    def add_documents(self, chunks: List[Chunk], batch_size=50):
        """
        将 MySQL 中的 Chunk 对象数组批量存入 Qdrant。
        实现了 Metadata 6大维度的完整映射。
        """
        converted_docs = []
        for chunk in chunks:
            source_info = {
                "platform": chunk.document.source_platform,
                "url": chunk.document.url,
                "author": chunk.document.author or "Unknown",
                "version": chunk.document.source_version or "Pet Owner Edition"
            }

            metadata = {
                "species": chunk.document.species,  # 物种: cat/dog等
                "urgency": chunk.urgency,  # 紧急度: critical等
                "category": chunk.document.category,  # 分类: poisoning等
                "source_info": source_info,  # 来源对象
                "parent_id": chunk.document_id,  # 文章序号 (md5_hash)
                "chunk_id": chunk.id,  # 片段唯一ID
                "index": chunk.chunk_index,  # 片段索引
                "total": chunk.total_chunks,  # 总片段数
                "title": chunk.document.title
            }

            # 3. 创建 LangChain Document 对象
            converted_docs.append(Document(
                page_content=chunk.content,
                metadata=metadata
            ))

        for i in range(0, len(converted_docs), batch_size):
            batch = converted_docs[i: i + batch_size]
            self.vector_store.add_documents(batch)

        logger.info(f"已成功将 {len(converted_docs)} 条带完整元数据的 Chunk 同步至 Qdrant")

    def get_retriever(
            self,
            k: int = 5,
            species: list | str = None,
            min_urgency: str = None,
    ):
        URGENCY = {
            "info": 1,
            "common": 2,
            "critical": 3,
        }
        search_kwargs = {"k": k}
        filter_conditions = []

        if species:
            species_list = [species] if isinstance(species, str) else species

            if "uncertain" not in species_list:
                species_list.append("uncertain")

            filter_conditions.append(
                rest_models.FieldCondition(
                    key="metadata.species",
                    match=rest_models.MatchAny(any=species_list),
                )
            )

        if min_urgency:
            min_level = URGENCY.get(min_urgency, 1)

            allowed_urgencies = [
                key for key, level in URGENCY.items()
                if level >= min_level
            ]

            filter_conditions.append(
                rest_models.FieldCondition(
                    key="metadata.urgency",
                    match=rest_models.MatchAny(any=allowed_urgencies),
                )
            )

        if filter_conditions:
            search_kwargs["filter"] = rest_models.Filter(must=filter_conditions)

        return self.vector_store.as_retriever(search_kwargs=search_kwargs)


def get_vector_store(collection_name="animal_rescue_collection", recreate=False):
    if collection_name not in _vector_store_cache:
        # bge-small-zh-v1.5 的维度是 512
        # recreate=True 会删除并重建 collection，解决维度不匹配问题
        _vector_store_cache[collection_name] = QdrantHybridStore(
            collection_name=collection_name,
            vector_size=512,
            recreate=recreate
        )
    return _vector_store_cache[collection_name]
