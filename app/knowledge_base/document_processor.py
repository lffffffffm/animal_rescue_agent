import hashlib
from pathlib import Path
import os
from langchain_community.document_loaders import TextLoader, UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


class DocumentProcessor:
    def __init__(self, upload_dir: str = "./data", chunk_size: int = 500, chunk_overlap: int = 50):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
        )

    def load_document(self, file_path: str):
        """从文件加载文档内容"""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)  # 只获取文件名

        if ext == '.txt':
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            # 其他格式使用通用加载器
            loader = UnstructuredFileLoader(file_path)

        documents = loader.load()
        return documents, filename

    def split_document(self, text: str, source_filename: str = ""):
        """将文档切分为多个小段落"""
        chunks = self.text_splitter.split_text(text)

        return [
            {
                "id": get_doc_id(chunk),
                "text": chunk,
                "source": source_filename,
                "tag": ["chunk"]
            }
            for chunk in chunks
        ]

    def process_file(self, file_path: str):
        """处理整个文件：加载 -> 切分"""
        documents, filename = self.load_document(file_path)

        all_chunks = []
        for doc in documents:
            chunks = self.split_document(doc.page_content, filename)
            all_chunks.extend(chunks)

        return all_chunks


def get_doc_id(text: str):
    """根据文本生成唯一 ID，保证重复文档不会重复入库"""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (10 ** 18)
