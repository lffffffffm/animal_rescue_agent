from loguru import logger
from typing import List, Union
from langchain_core.embeddings import Embeddings

_default_embedding_manager = None


class EmbeddingManager:
    """
    嵌入模型管理类
    用于初始化和管理本地嵌入模型
    """

    def __init__(self, model_name: str = "BAAI/bge-base-zh"):
        """
        初始化嵌入模型管理器

        Args:
            model_name: 嵌入模型名称（默认使用中文 bge-base-zh）
        """
        self.model_name = model_name
        self._embeddings = None

        # 初始化嵌入模型
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """
        初始化本地嵌入模型
        """
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            from sentence_transformers import SentenceTransformer

            # 验证模型是否可加载
            try:
                SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(
                    f"指定模型不可用，已回退到 bge-base-zh: {str(e)}"
                )
                self.model_name = "BAAI/bge-base-zh"

            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )

            logger.info(f"已使用本地中文嵌入模型: {self.model_name}")

        except ImportError as e:
            logger.error(f"缺少必要的依赖: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {str(e)}")
            raise

    @property
    def embeddings(self) -> Embeddings:
        """
        获取嵌入模型实例

        Returns:
            Embeddings: 嵌入模型实例
        """
        if self._embeddings is None:
            self._initialize_embeddings()
        return self._embeddings

    def embed_texts(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        对文本进行嵌入编码

        Args:
            texts: 单个文本或文本列表

        Returns:
            嵌入向量列表
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings_result = self._embeddings.embed_documents(texts)
            logger.info(f"成功生成 {len(texts)} 个文本的嵌入向量")
            return embeddings_result
        except Exception as e:
            logger.error(f"生成文本嵌入失败: {str(e)}")
            raise

    def embed_query(self, query: str) -> List[float]:
        """
        对查询文本进行嵌入编码

        Args:
            query: 查询文本

        Returns:
            单个嵌入向量
        """
        try:
            embedding_result = self._embeddings.embed_query(query)
            logger.debug(f"成功生成查询 '{query[:50]}...' 的嵌入向量")
            return embedding_result
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {str(e)}")
            raise


def get_embedding(model_name: str = "BAAI/bge-base-zh") -> Embeddings:
    """
    获取全局唯一的 Embeddings 实例（单例）

    Args:
        model_name: 嵌入模型名称

    Returns:
        Embeddings 实例
    """
    global _default_embedding_manager

    if _default_embedding_manager is None:
        logger.info("🔧 初始化全局 EmbeddingManager ...")
        _default_embedding_manager = EmbeddingManager(model_name=model_name)

    return _default_embedding_manager.embeddings


def initialize_embedding_model(
        model_name: str = "BAAI/bge-base-zh"
) -> EmbeddingManager:
    """
    初始化嵌入模型的便捷函数

    Args:
        model_name: 嵌入模型名称

    Returns:
        EmbeddingManager 实例
    """
    return EmbeddingManager(model_name=model_name)


if __name__ == "__main__":
    print("🚀 初始化中文嵌入模型中...")
    embedder = initialize_embedding_model("BAAI/bge-base-zh")

    texts = [
        "流浪动物救助需要专业的医疗支持",
        "受伤的猫咪应该尽快送往动物医院",
        "动物救助站需要志愿者协助"
    ]

    print("📌 正在生成文本向量...")
    embeddings = embedder.embed_texts(texts)

    print(f"生成向量数量: {len(embeddings)}")
    print(f"单个向量维度: {len(embeddings[0])}")

    query = "如何救助受伤的流浪猫"
    print("🔍 正在生成查询向量...")
    query_vec = embedder.embed_query(query)

    print(f"查询向量维度: {len(query_vec)}")

    print("✅ 测试完成，一切正常！")
