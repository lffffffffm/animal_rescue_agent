# 初始化处理器
from app.knowledge_base.document_processor import DocumentProcessor
from app.knowledge_base.vector_store import get_vector_store
from app.knowledge_base.retriever import HybridRetriever
from app.knowledge_base.reranker import Reranker

# 文档处理
processor = DocumentProcessor()
chunks = processor.process_file("./data/mock_rescue_data.txt")
print(f"处理得到 {len(chunks)} 个文档块")

# 文档入库
vector_store = get_vector_store("animal_rescue_test")
vector_store.add_documents(chunks)
print("文档已入库")

# 检索测试
retriever = HybridRetriever(collection_name="animal_rescue_test")
results = retriever.retrieve("1 + 1 = ?")
print(f"检索到 {len(results)} 条相关文档")

# 重排测试
reranker = Reranker()
reranked_results = reranker.rerank(
    query="1 + 1 = ?",
    documents=[{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
)
print(f"\n重排后返回 {len(reranked_results)} 条文档")
