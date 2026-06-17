"""POST /api/upload (架构 §5.3): 上传一张图, 存到 Volume, 返回可访问 URL。

模板流程需要把新选的本地图先变成后端 URL 才能 apply。
"""

from __future__ import annotations

import asyncio
import io

from fastapi import APIRouter, HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from app.storage import db
from app.storage.files import decode_image_b64, input_path, sanitize_id, to_url

router = APIRouter()


class UploadRequest(BaseModel):
    device_id: str
    image: str  # base64 (可带 data: 前缀)


def _save(raw: bytes, path) -> None:
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=95)


@router.post("/upload")
async def upload(req: UploadRequest):
    device_id = sanitize_id(req.device_id)
    db.get_or_create_device(device_id)
    try:
        raw = decode_image_b64(req.image)
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
    except (ValueError, UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="图片格式不对，请换一张试试")

    upload_id = db.new_id("u_")
    path = input_path(device_id, upload_id)
    await asyncio.to_thread(_save, raw, path)
    return {"image_url": to_url(path), "upload_id": upload_id}
