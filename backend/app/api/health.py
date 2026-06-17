"""探活接口。被鉴权和频次限制中间件排除在外, 供 Zeabur / 负载探测使用。"""

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": __version__}
