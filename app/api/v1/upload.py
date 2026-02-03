import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.config import settings
from app.db.base import get_db
from app.db.model import User, Session as DBSession, UploadedImage
from app.services.session_service import SessionService
from app.utils.auth import get_current_active_user

router = APIRouter()

# 确保上传目录存在：基于文件路径定位，避免因启动目录不同写到错误位置
# 当前文件: app/api/v1/upload.py
# parents[2] -> app/
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 允许的图片类型
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp"
}

# 最大文件大小：5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/image")
async def upload_image(
        file: UploadFile = File(..., description="Image file to upload"),
        session_id: Optional[str] = Form(None, description="Optional session ID to associate with this image"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    上传图片并关联到指定会话（如不存在则创建新会话）
    """
    # 1. 检查文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"
        )

    # 2. 处理会话
    db_session = None
    if session_id:
        db_session = SessionService.get_session_by_id(db, session_id)
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        if db_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
    else:
        # 创建新会话
        db_session = SessionService.create_session(
            db=db,
            user_id=current_user.id,
            title=f"Image upload {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    try:
        # 3. 读取并验证文件大小
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
            )

        # 4. 生成安全文件名
        file_ext = ALLOWED_CONTENT_TYPES[file.content_type]
        file_id = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = UPLOAD_DIR / file_id
        # 生成对外可访问 URL；如果未配置 PUBLIC_BASE_URL 则退化为相对路径，前端需自行代理
        base_url = (settings.PUBLIC_BASE_URL or "").rstrip("/")
        url_path = f"{base_url}/uploads/{file_id}" if base_url else f"/uploads/{file_id}"

        # 5. 保存文件
        with open(file_path, "wb") as f:
            f.write(contents)

        # 6. 写入 UploadedImage（落库可回溯）
        image_uuid = file_id.split('.')[0]
        db_image = UploadedImage(
            image_id=image_uuid,
            session_id=db_session.session_id,
            user_id=current_user.id,
            file_path=str(file_path),
            url_path=url_path,
            original_filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(contents)
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        # 7. 返回响应
        return {
            "session_id": db_session.session_id,
            "image_id": image_uuid,
            "image_url": url_path,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents),
            "uploaded_at": db_image.created_at.isoformat()
        }

    except Exception as e:
        # 清理可能已创建的文件
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )
    finally:
        # 重置文件指针，避免资源泄露
        await file.seek(0)
