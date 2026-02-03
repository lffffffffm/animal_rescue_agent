# 初始化处理器
from app.knowledge_base.document_processor import DocumentProcessor
from app.knowledge_base.vector_store import get_vector_store
from app.knowledge_base.retriever import HybridRetriever
from app.knowledge_base.reranker import Reranker

# 文档处理
processor = DocumentProcessor()
chunks = processor.process_file("./data/mock_rescue_data.txt")
print(f"处理得到 {len(chunks)} 个文档块")

# 文档入库（对齐 Agent 默认使用的 collection）
vector_store = get_vector_store("animal_rescue_collection")
vector_store.add_documents(chunks)
print("文档已入库")

# 检索测试（使用救助相关 query，便于验证召回效果）
retriever = HybridRetriever(collection_name="animal_rescue_collection")
results = retriever.retrieve("猫受伤流血怎么办？")
print(f"检索到 {len(results)} 条相关文档")

# 重排测试
reranker = Reranker()
reranked_results = reranker.rerank(
    query="猫受伤流血怎么办？",
    documents=results
)
print(f"\n重排后返回 {len(reranked_results)} 条文档")
