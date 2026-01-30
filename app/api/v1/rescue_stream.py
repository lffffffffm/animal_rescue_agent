from __future__ import annotations
import json
from typing import Generator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session
from app.agent.graph import app as agent_app
from app.api.schemas import AnimalRescueQueryRequest
from app.db.base import get_db
from app.db.model import User
from app.services.session_service import SessionService
from app.utils.auth import get_current_active_user
from app.utils.fallback import emergency_rescue_template

router = APIRouter()


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _validate_or_create_session(db: Session, current_user: User, req: AnimalRescueQueryRequest):
    if req.session_id:
        session = SessionService.get_session_by_id(db, req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话未找到")
        if session.user_id != current_user.username:
            raise HTTPException(status_code=403, detail="无权访问此会话")
        return session

    return SessionService.create_session(
        db=db,
        user_id=current_user.username,
        title=req.query[:20]
    )


@router.post("/stream")
def rescue_query_stream(
    req: AnimalRescueQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = _validate_or_create_session(db, current_user, req)

    def gen() -> Generator[str, None, None]:
        final_meta: Optional[dict] = None

        try:
            result = agent_app.invoke({
                "query": req.query,
                "chat_history": req.chat_history or [],
                "enable_web_search": req.enable_web_search,
                "enable_map": req.enable_map,
                "location": req.location,
                "radius_km": req.radius_km,
            })

            answer = result.get("response", "") or ""
            final_meta = {
                "used_web_search": result.get("used_web_search", False),
                "used_map": result.get("used_map", False),
                "evidences": result.get("merged_docs", []),
                "rescue_resources": result.get("rescue_resources", []) if result.get("map_result") else None,
            }

        except Exception as e:
            logger.exception("Agent 执行失败（stream），返回兜底答案")
            answer = emergency_rescue_template(req.query)
            final_meta = {
                "used_web_search": False,
                "used_map": False,
                "evidences": [],
                "rescue_resources": None,
                "fallback": True,
                "error": str(e),
            }

        # 增量推送（兼容版：按字符推送）
        for ch in answer:
            yield _sse("delta", {"text": ch})

        # 落库
        try:
            SessionService.add_conversation(
                db=db,
                session_id=session.session_id,
                user_input=req.query,
                agent_response=answer,
            )
        except Exception:
            logger.exception("对话落库失败")

        yield _sse("done", {"session_id": session.session_id, **(final_meta or {})})

    return StreamingResponse(gen(), media_type="text/event-stream")
