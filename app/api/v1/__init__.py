from fastapi import APIRouter
from . import rescue, session, auth, rescue_stream

api_router = APIRouter()
api_router.include_router(rescue.router, prefix="/query", tags=["query"])
api_router.include_router(rescue_stream.router, prefix="/query", tags=["query"])
api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
