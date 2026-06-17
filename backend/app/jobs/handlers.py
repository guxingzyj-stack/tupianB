"""队列任务处理器 (任务 5.2 / 5.4)。

video: 图生视频 (kling 等, relay 异步)。
template: 模板合成 (图修 + 运镜视频 + 音乐 + 字幕), 需 ffmpeg + 视频通路,
          待视频通路恢复后补完整 compose; 现在会优雅失败 (任务标 failed)。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

import httpx

from app.adapters.video_adapter import make_video_adapter
from app.engine.template_compose import compose
from app.storage.files import to_url, video_path

_video_adapter = make_video_adapter()
_ASSETS = Path(__file__).resolve().parent.parent / "templates" / "assets"


def _fetch_bytes(url: str) -> bytes:
    r = httpx.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def _music_path(name: str | None) -> str | None:
    if not name:
        return None
    p = _ASSETS / name
    return str(p) if p.exists() else None  # 素材没做时返回 None, 不加音乐


async def video_handler(job_id: str, payload: dict, set_progress: Callable[[int], None]) -> dict:
    device_id = payload["device_id"]
    image_url = payload["image_url"]
    motion = payload.get("motion", "slow_zoom")

    set_progress(5)
    # kling 云端取不到 localhost URL, 服务端先把图取成字节再传 base64
    img_bytes = await asyncio.to_thread(_fetch_bytes, image_url)
    data = await asyncio.to_thread(_video_adapter.generate, img_bytes, motion, set_progress)
    out = video_path(device_id, job_id)
    await asyncio.to_thread(out.write_bytes, data)
    return {"output_path": str(out), "result_url": to_url(out)}


async def template_handler(job_id: str, payload: dict, set_progress: Callable[[int], None]) -> dict:
    """模板合成: 取图 -> 运镜视频(kling) -> ffmpeg 叠字幕(+音乐如有素材)。"""
    device_id = payload["device_id"]
    image_url = payload["image_url"]
    text = payload.get("text", "")
    motion = payload.get("video_motion", "slow_zoom")

    set_progress(5)
    img_bytes = await asyncio.to_thread(_fetch_bytes, image_url)
    set_progress(10)
    video_bytes = await asyncio.to_thread(
        _video_adapter.generate, img_bytes, motion,
        lambda p: set_progress(10 + int(p * 0.7)),
    )
    out = video_path(device_id, job_id)
    raw = out.with_suffix(".raw.mp4")
    await asyncio.to_thread(raw.write_bytes, video_bytes)
    set_progress(88)
    music = _music_path(payload.get("music"))
    await asyncio.to_thread(compose, raw, text, out, music)
    raw.unlink(missing_ok=True)
    return {"output_path": str(out), "result_url": to_url(out)}
