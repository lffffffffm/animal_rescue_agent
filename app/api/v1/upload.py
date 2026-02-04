import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from qcloud_cos import CosConfig, CosS3Client

from app.config import settings
from app.db.base import get_db
from app.db.model import User, Session as DBSession, UploadedImage
from app.services.session_service import SessionService
from app.utils.auth import get_current_active_user

router = APIRouter()

# =========================
# COS Client 初始化
# =========================
cos_config = CosConfig(
    Region=settings.COS_REGION,
    SecretId=settings.COS_SECRET_ID,
    SecretKey=settings.COS_SECRET_KEY,
    Scheme="https"
)
cos_client = CosS3Client(cos_config)

# =========================
# 配置
# =========================
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp"
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/image")
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    session_id: Optional[str] = Form(None, description="Optional session ID to associate with this image"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    上传图片到 COS，并关联到指定会话
    """

    # 1. 校验文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"
        )

    # 2. 处理会话
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
        db_session = SessionService.create_session(
            db=db,
            user_id=current_user.id,
            title=f"Image upload {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    try:
        # 3. 读取文件 & 校验大小
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (max 5MB)"
            )

        # 4. 生成 COS Object Key
        file_ext = ALLOWED_CONTENT_TYPES[file.content_type]
        image_uuid = uuid.uuid4().hex
        object_key = f"uploads/{datetime.now().strftime('%Y/%m/%d')}/{image_uuid}.{file_ext}"

        # 5. 上传到 COS
        try:
            cos_client.put_object(
                Bucket=settings.COS_BUCKET,
                Key=object_key,
                Body=contents,
                ContentType=file.content_type
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"COS upload failed: {str(e)}"
            )

        # 6. 生成公网访问 URL（前端 & LLM 使用）
        image_url = f"{settings.COS_BASE_URL}/{object_key}"

        # 7. 写入数据库
        db_image = UploadedImage(
            image_id=image_uuid,
            session_id=db_session.session_id,
            user_id=current_user.id,
            file_path=object_key,     # COS Object Key
            url_path=image_url,       # 公网 URL
            original_filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(contents)
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        # 8. 返回
        return {
            "session_id": db_session.session_id,
            "image_id": image_uuid,
            "image_url": image_url,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents),
            "uploaded_at": db_image.created_at.isoformat()
        }

    finally:
        await file.seek(0)
