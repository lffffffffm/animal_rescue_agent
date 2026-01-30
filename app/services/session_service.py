from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4
from app.db.model import Session as SessionModel, Conversation
from app.db.model import User


class SessionService:
    """
    会话管理服务类
    """
    
    @staticmethod
    def create_session(db: Session, user_id: str, title: Optional[str] = None) -> SessionModel:
        """
        创建新会话
        """
        session_id = str(uuid4())
        db_session = SessionModel(
            session_id=session_id,
            user_id=user_id,
            title=title or f"会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return db_session
    
    @staticmethod
    def get_session_by_id(db: Session, session_id: str) -> Optional[SessionModel]:
        """
        根据ID获取会话
        """
        return db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    
    @staticmethod
    def get_sessions_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[SessionModel]:
        """
        获取用户的所有会话
        """
        return db.query(SessionModel)\
                 .filter(SessionModel.user_id == user_id)\
                 .offset(skip)\
                 .limit(limit)\
                 .all()
    
    @staticmethod
    def update_session_title(db: Session, session_id: str, title: str) -> Optional[SessionModel]:
        """
        更新会话标题
        """
        db_session = SessionService.get_session_by_id(db, session_id)
        if db_session:
            db_session.title = title
            db_session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_session)
        return db_session
    
    @staticmethod
    def delete_session(db: Session, session_id: str) -> bool:
        """
        删除会话及其所有对话记录
        """
        # 先删除相关的对话记录
        db.query(Conversation).filter(Conversation.session_id == session_id).delete()
        
        # 再删除会话记录
        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_conversation_history(db: Session, session_id: str) -> List[Conversation]:
        """
        获取会话的对话历史
        """
        return db.query(Conversation)\
                 .filter(Conversation.session_id == session_id)\
                 .order_by(Conversation.created_at)\
                 .all()
    
    @staticmethod
    def add_conversation(db: Session, session_id: str, user_input: str, agent_response: str) -> Conversation:
        """
        添加对话记录到会话
        """
        conversation = Conversation(
            session_id=session_id,
            user_input=user_input,
            agent_response=agent_response
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def get_recent_sessions(db: Session, user_id: str, limit: int = 10) -> List[SessionModel]:
        """
        获取用户的最近会话
        """
        return db.query(SessionModel)\
                 .filter(SessionModel.user_id == user_id)\
                 .order_by(SessionModel.updated_at.desc())\
                 .limit(limit)\
                 .all()
    
    @staticmethod
    def get_session_count(db: Session, user_id: str) -> int:
        """
        获取用户会话总数
        """
        return db.query(SessionModel).filter(SessionModel.user_id == user_id).count()