from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger
from app.db.base import get_db
from app.db.model import User
from app.utils.auth import get_current_active_user
from app.services.session_service import SessionService
from app.api.schemas import (
    AnimalRescueQueryRequest,
    AnimalRescueQueryResponse,
    Evidence,
    RescueResource
)

from app.agent.graph import app as agent_app

router = APIRouter()


@router.post("", response_model=AnimalRescueQueryResponse)
def rescue_query(
        req: AnimalRescueQueryRequest,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    # 1️⃣ Session（先假设前端以后会传 session_id，这里先省略）
    session = SessionService.create_session(
        db=db,
        user_id=current_user.username,
        title=req.query[:20]  # todo: 后续修改

    )

    # 2️⃣ 调 Agent
    try:
        result = agent_app.invoke({
            "query": req.query,
            "chat_history": req.chat_history or [],
            "enable_web_search": req.enable_web_search,
            "enable_map": req.enable_map,
            "location": req.location,
            "radius_km": req.radius_km,
        })
    except Exception as e:
        logger.exception("Agent 执行失败")
        raise HTTPException(status_code=500, detail="Agent 执行失败")

    answer = result.get("response", "")

    # 3️⃣ 记录对话
    SessionService.add_conversation(
        db=db,
        session_id=session.session_id,
        user_input=req.query,
        agent_response=answer
    )

    # 4️⃣ 构造 response（⚠️ 关键）
    return AnimalRescueQueryResponse(
        answer=answer,
        used_web_search=result.get("used_web_search", False),
        used_map=result.get("used_map", False),
        evidences=[
            Evidence(**e) for e in result.get("merged_docs", [])
        ],
        rescue_resources=[
            RescueResource(**r) for r in result.get("rescue_resources", [])
        ] if result.get("map_result") else None
    )
