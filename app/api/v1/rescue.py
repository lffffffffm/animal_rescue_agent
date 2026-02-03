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
    # 1️⃣ Session：支持前端传 session_id 续聊
    if req.session_id:
        session = SessionService.get_session_by_id(db, req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话未找到")
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此会话")
    else:
        session = SessionService.create_session(
            db=db,
            user_id=current_user.id,
            title=req.query[:20]  # todo: 后续修改
            )

    image_ids = list(req.image_ids or [])
    if len(image_ids) > 4:
        raise HTTPException(status_code=400, detail="最多支持4张图片")

    images_meta = []
    if image_ids:
        from app.db.model import UploadedImage

        imgs = db.query(UploadedImage).filter(
            UploadedImage.image_id.in_(image_ids),
            UploadedImage.user_id == current_user.id,
        ).all()
        found = {i.image_id: i for i in imgs}
        missing = [i for i in image_ids if i not in found]
        if missing:
            raise HTTPException(status_code=404, detail=f"图片不存在或无权限: {missing}")

        images_meta = [
            {
                "image_id": found[i].image_id,
                "url": found[i].url_path,
                "filename": found[i].original_filename,
                "content_type": found[i].content_type,
                "size_bytes": found[i].size_bytes,
                "uploaded_at": found[i].created_at.isoformat(),
            }
            for i in image_ids
        ]

    # 2️⃣ 调 Agent
    try:
        result = agent_app.invoke({
            "query": req.query,
            "chat_history": req.chat_history or [],
            "enable_web_search": req.enable_web_search,
            "enable_map": req.enable_map,
            "location": req.location,
            "radius_km": req.radius_km,
            "image_ids": image_ids,
            "images": images_meta,
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
        agent_response=answer,
        agent_meta={
            "used_web_search": result.get("used_web_search", False),
            "used_map": result.get("used_map", False),
            "evidences": result.get("merged_docs", []),
            "images": images_meta,
        }
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
