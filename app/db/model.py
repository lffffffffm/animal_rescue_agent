from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Session(Base):
    """
    存储对话会话信息的模型类
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True, doc="唯一会话ID")
    user_id = Column(String(255), index=True, doc="用户ID（未登录可为空）")
    title = Column(String(500), doc="对话标题")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, doc="更新时间")

    # 关系定义
    conversations = relationship(
        "Conversation",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Conversation.created_at"
    )

    def __repr__(self):
        return f"<Session(id={self.id}, session_id='{self.session_id}', user_id='{self.user_id}')>"


class Conversation(Base):
    """
    存储智能助手对话记录的模型类
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False, index=True, doc="对话会话ID")
    user_input = Column(Text, nullable=False, doc="用户输入内容")
    agent_response = Column(Text, nullable=False, doc="助手响应内容")
    agent_meta = Column(
        JSON,
        nullable=True,
        doc="""
            Agent 执行信息：
            - used_web
            - used_map
            - evidences
            - confidence
            - latency
            - tool_calls
            """
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, doc="更新时间")

    # 关系定义
    session = relationship("Session", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id='{self.session_id}', created_at={self.created_at})>"


class User(Base):
    """
    存储用户信息的模型类
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True, doc="用户名")
    email = Column(String(255), unique=True, nullable=False, index=True, doc="用户邮箱")
    hashed_password = Column(String(255), nullable=False, doc="哈希后的密码")
    is_active = Column(Boolean, default=True, doc="用户是否激活")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, doc="更新时间")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
