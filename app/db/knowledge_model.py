# 知识库中模型数据也存入mysql
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Document(Base):
    """
    存储原始文章信息（文章级）
    """
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True, doc="文档ID，使用 md5(url)")
    title = Column(Text, nullable=False, doc="文章标题")
    url = Column(Text, nullable=False, doc="原文链接")

    author = Column(String(255), doc="文章作者")
    species = Column(String(20), index=True, doc="适用物种: cat/dog/rabbit/general")
    category = Column(String(100), index=True, doc="知识分类: poisoning/behavior/skin/...")

    source_platform = Column(String(50), doc="来源平台，如 MSD Manuals")
    source_version = Column(String(50), doc="版本，如 Pet Owner Edition")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="创建时间")

    # 关系定义
    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Chunk.chunk_index"
    )

    def __repr__(self):
        return f"<Document(id='{self.id}', title='{self.title}')>"


class Chunk(Base):
    """
    存储文档切分后的文本片段（片段级）
    """
    __tablename__ = "chunks"

    id = Column(String(64), primary_key=True, index=True, doc="片段ID，md5(document_id + index)")

    document_id = Column(
        String(64),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
        doc="所属文档ID"
    )

    content = Column(Text, nullable=False, doc="文本片段内容")

    chunk_index = Column(Integer, nullable=False, doc="当前片段序号")
    total_chunks = Column(Integer, nullable=False, doc="该文档总片段数")

    """
    critical  —— 需要立即处理，可能危及生命
    common    —— 常规处理建议
    info      —— 背景知识、介绍性内容
    """
    urgency = Column(
        String(20),
        index=True,
        doc="紧急程度: critical/common/info"
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="创建时间")

    # 关系定义
    document = relationship(
        "Document",
        back_populates="chunks"
    )

    def __repr__(self):
        return f"<Chunk(id='{self.id}', document_id='{self.document_id}', index={self.chunk_index})>"

# from app.db.base import init_db
# init_db()