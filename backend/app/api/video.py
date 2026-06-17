"""POST /api/video (异步) + GET /api/jobs/{id} (任务 5.2)。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.jobs.queue import queue
from app.storage import db
from app.storage.files import sanitize_id

router = APIRouter()

_MOTIONS = {"slow_zoom", "env_breeze", "subtle_human"}


class VideoRequest(BaseModel):
    device_id: str
    image_url: str
    motion: str = "slow_zoom"


@router.post("/video")
async def create_video(req: VideoRequest):
    device_id = sanitize_id(req.device_id)
    device = db.get_or_create_device(device_id)

    if not int(device.get("enable_video", 1)):
        raise HTTPException(status_code=403, detail="视频功能没开，找家人帮忙打开")

    limit = int(device.get("daily_video_limit", 10))
    if db.count_jobs_today(device_id, "video") >= limit:
        raise HTTPException(status_code=429, detail="今天的视频次数用完了，明天再来")

    motion = req.motion if req.motion in _MOTIONS else "slow_zoom"
    job_id = queue.enqueue(
        "video",
        device_id,
        {"device_id": device_id, "image_url": req.image_url, "motion": motion},
        id_prefix="v_",
    )
    return {"job_id": job_id, "status": "pending", "estimated_seconds": 120}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str):
    st = queue.get_status(job_id)
    if st is None:
        raise HTTPException(status_code=404, detail="找不到这个任务")
    return st
