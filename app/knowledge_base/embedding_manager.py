from loguru import logger
from typing import List, Union

from langchain_core.embeddings import Embeddings

from app.config import settings

_default_embedding_manager = None


class EmbeddingManager:
    """
    嵌入模型管理类
    用于初始化和管理本地嵌入模型（离线优先）
    """

    def __init__(self, model_name: str):
        """
        初始化嵌入模型管理器

        Args:
            model_name: 嵌入模型名称 (可以是 HF repo_id 或本地路径)
        """
        self.model_name = model_name
        self._embeddings = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """
        初始化嵌入模型（离线优先）。
        - 优先使用 settings.EMBEDDING_MODEL_PATH
        - settings.EMBEDDING_OFFLINE=true 时，强制只用本地文件，禁止联网
        """
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            from sentence_transformers import SentenceTransformer

            offline = str(settings.EMBEDDING_OFFLINE).lower() == 'true'
            local_path = settings.EMBEDDING_MODEL_PATH

            # 优先使用本地路径配置，否则使用传入的 model_name
            model_to_load = local_path if local_path else self.model_name

            if not model_to_load:
                raise ValueError("未指定嵌入模型。请设置 EMBEDDING_MODEL_PATH 或 EMBEDDING_MODEL。")

            # 验证模型能否加载
            try:
                # 关键：local_files_only=offline 决定是否联网
                SentenceTransformer(model_to_load, local_files_only=offline)
            except Exception as e:
                logger.error(f"无法加载嵌入模型 '{model_to_load}' (offline={offline})。错误: {e}")
                if offline:
                    raise RuntimeError(
                        f"离线模式下加载模型失败。请检查 EMBEDDING_MODEL_PATH ('{local_path}') 是否正确，或设置 EMBEDDING_OFFLINE=false 以允许下载。"
                    )
                # 如果允许联网但失败，直接抛出异常，不再回退
                raise e

            # 初始化 LangChain Embeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=model_to_load,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )

            logger.info(f"已加载 Embedding 模型: {model_to_load} (offline={offline})")

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
        """
        if self._embeddings is None:
            self._initialize_embeddings()
        return self._embeddings

    def embed_texts(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        对文本进行嵌入编码
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
        """
        try:
            embedding_result = self._embeddings.embed_query(query)
            logger.debug(f"成功生成查询 '{query[:50]}...' 的嵌入向量")
            return embedding_result
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {str(e)}")
            raise


def get_embedding() -> Embeddings:
    """
    获取全局唯一的 Embeddings 实例（单例）
    从 settings 中读取模型名称。
    """
    global _default_embedding_manager

    if _default_embedding_manager is None:
        logger.info("🔧 初始化全局 EmbeddingManager ...")
        # 从 settings 读取模型名，而不是硬编码
        model_name_from_settings = settings.EMBEDDING_MODEL
        _default_embedding_manager = EmbeddingManager(model_name=model_name_from_settings)

    return _default_embedding_manager.embeddings


def initialize_embedding_model() -> EmbeddingManager:
    """
    初始化嵌入模型的便捷函数
    """
    # 从 settings 读取模型名
    model_name_from_settings = settings.EMBEDDING_MODEL
    return EmbeddingManager(model_name=model_name_from_settings)


if __name__ == "__main__":
    # 这个测试现在会依赖 .env 里的配置
    # 请确保 .env 中有 EMBEDDING_MODEL 或 EMBEDDING_MODEL_PATH
    print("🚀 初始化嵌入模型中...")
    embedder = initialize_embedding_model()

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
