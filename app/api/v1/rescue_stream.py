from __future__ import annotations
import asyncio
import json
from typing import Generator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session
from app.agent.graph import app as agent_app
from app.api.schemas import AnimalRescueQueryRequest
from app.db.base import get_db
from app.db.model import User, UploadedImage
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
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此会话")
        return session

    return SessionService.create_session(
        db=db,
        user_id=current_user.id,
        title=req.query[:20]
    )


@router.post("/stream")
async def rescue_query_stream(
    req: AnimalRescueQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = _validate_or_create_session(db, current_user, req)

    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def writer(delta: str):
        if not delta:
            return
        loop.call_soon_threadsafe(queue.put_nowait, _sse("delta", {"text": delta}))

    async def event_stream():
        final_meta: Optional[dict] = None
        answer: str = ""
        images_meta = []

        # 先发一个连接确认事件，便于前端知道 SSE 已建立
        yield _sse("start", {"status": "connected"})

        try:
            raw_image_ids = list(req.image_ids or [])
            if len(raw_image_ids) > 4:
                raise HTTPException(status_code=400, detail="最多支持4张图片")

            if raw_image_ids:
                imgs = db.query(UploadedImage).filter(
                    UploadedImage.image_id.in_(raw_image_ids),
                    UploadedImage.user_id == current_user.id,
                    UploadedImage.session_id == session.session_id,
                ).all()
                found = {i.image_id: i for i in imgs}
                missing = [i for i in raw_image_ids if i not in found]
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
                    for i in raw_image_ids
                ]

            # 并行执行：一边跑图，一边持续消费队列
            async def run_agent():
                nonlocal final_meta, answer
                result = await agent_app.ainvoke({
                    "query": req.query,
                    "chat_history": req.chat_history or [],
                    "enable_web_search": req.enable_web_search,
                    "enable_map": req.enable_map,
                    "location": req.location,
                    "radius_km": req.radius_km,
                    "image_ids": [img["url"] for img in images_meta] if images_meta else [],
                    "images": images_meta,
                    "writer": writer,
                })
                answer = result.get("response", "") or ""
                final_meta = {
                    "used_web_search": result.get("used_web_search", False),
                    "used_map": result.get("used_map", False),
                    "evidences": result.get("merged_docs", []),
                    "rescue_resources": result.get("rescue_resources", []) if result.get("map_result") else None,
                    "images": images_meta,
                }

            # 启动后台任务
            agent_task = asyncio.create_task(run_agent())

            # 持续消费队列，直到 agent_task 完成
            while not agent_task.done():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield msg
                except asyncio.TimeoutError:
                    # 定期发心跳，防止缓冲区不动
                    yield _sse("heartbeat", {"status": "waiting"})
                    continue

            # 等待 agent_task 结束（如果有异常会在这里抛出）
            await agent_task

        except Exception as e:
            logger.exception("Agent 执行失败（stream），返回兜底答案")
            answer = emergency_rescue_template(req.query)
            final_meta = {
                "used_web_search": False,
                "used_map": False,
                "evidences": [],
                "rescue_resources": None,
                "images": images_meta,
                "fallback": True,
                "error": str(e),
            }
            # 兜底也走一次性输出（不拆字符）
            yield _sse("delta", {"text": answer})

        # 吐出队列里剩余的 delta（防止最后几 token 丢失）
        while not queue.empty():
            yield await queue.get()

        # 落库
        try:
            SessionService.add_conversation(
                db=db,
                session_id=session.session_id,
                user_input=req.query,
                user_images=[img['url'] for img in images_meta] if images_meta else None,
                agent_response=answer,
                agent_meta=final_meta,
            )
        except Exception:
            logger.exception("对话落库失败")

        yield _sse("done", {"session_id": session.session_id, **(final_meta or {})})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )
