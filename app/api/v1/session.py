from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.model import User
from app.utils.auth import get_current_active_user
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/create")
def create_session(
    title: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新会话
    """
    try:
        session = SessionService.create_session(db, current_user.id, title)
        return {"session_id": session.session_id, "title": session.title, "created_at": session.created_at}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/{session_id}")
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取会话详情
    """
    session = SessionService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    # 检查会话是否属于当前用户
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    return {
        "id": session.id,
        "session_id": session.session_id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@router.get("")
def get_sessions(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """
    获取当前用户的所有会话
    """
    sessions = SessionService.get_sessions_by_user(db, current_user.id, skip, limit)
    return [
        {
            "id": session.id,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
        for session in sessions
    ]


@router.put("/{session_id}/title")
def update_session_title(
    session_id: str,
    title: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新会话标题
    """
    session = SessionService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此会话")
    
    updated_session = SessionService.update_session_title(db, session_id, title)
    return {
        "session_id": updated_session.session_id,
        "title": updated_session.title,
        "updated_at": updated_session.updated_at
    }


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除会话及其所有对话记录
    """
    session = SessionService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此会话")
    
    success = SessionService.delete_session(db, session_id)
    if success:
        return {"message": "会话删除成功"}
    else:
        raise HTTPException(status_code=500, detail="会话删除失败")


@router.get("/{session_id}/history")
def get_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """
    获取会话的对话历史
    """
    session = SessionService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    conversations = SessionService.get_conversation_history(db, session_id)
    return [
        {
            "id": conv.id,
            "session_id": conv.session_id,
            "user_input": conv.user_input,
            "user_images": conv.user_images,
            "agent_response": conv.agent_response,
            "agent_meta": conv.agent_meta,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at
        }
        for conv in conversations
    ]