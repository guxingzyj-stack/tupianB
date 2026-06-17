"""图生视频 adapter — Kling 原生代理 (任务 5.2, 已实测打通)。

接口 (relay 代理 kling 原生 API):
  提交 POST {root}/kling/v1/videos/image2video
       {model_name, image(base64), prompt, mode, duration} -> {data:{task_id, task_status}}
  轮询 GET  {root}/kling/v1/videos/image2video/{task_id}
       -> {data:{task_status: submitted/processing/succeed/failed,
                 task_result:{videos:[{url}]}}}
  实测 kling-v1 / std / 5s 约 3-4 分钟。

image 必须传 base64 (kling 云端取不到我们的 localhost URL)。
运动 prompt 严格按 PRD §8.2 红线。失败抛 AdapterFailure -> 任务标 failed。
"""

from __future__ import annotations

import base64
import time
from typing import Callable

import httpx

from app.adapters.base import AdapterFailure
from app.config import settings

MOTION_PROMPTS = {
    "slow_zoom": "slow zoom in, no content change, stable composition",
    "env_breeze": (
        "subtle environmental motion: grass swaying, leaves moving, water "
        "rippling. People and animals remain still."
    ),
    "subtle_human": (
        "very subtle human motion: hair and clothing slightly moving. "
        "DO NOT change facial expressions. DO NOT move mouth. DO NOT blink. "
        "Keep face static."
    ),
}


def motion_prompt(motion: str) -> str:
    return MOTION_PROMPTS.get(motion, MOTION_PROMPTS["slow_zoom"])


class VideoAdapter:
    def __init__(self, submit_url: str, api_key: str, model_name: str,
                 mode: str = "std", duration: str = "5", timeout: float = 60.0):
        self.submit_url = submit_url
        self.api_key = api_key
        self.model_name = model_name
        self.mode = mode
        self.duration = duration
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit(self, image_b64: str, prompt: str) -> str:
        payload = {
            "model_name": self.model_name,
            "image": image_b64,
            "prompt": prompt,
            "mode": self.mode,
            "duration": self.duration,
        }
        try:
            r = httpx.post(self.submit_url, json=payload, headers=self._headers, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise AdapterFailure(f"视频提交网络错误: {exc}") from exc
        try:
            body = r.json()
        except ValueError as exc:
            raise AdapterFailure(f"视频提交返回非 JSON: {r.text[:200]}") from exc
        # kling: code 0 = ok
        if body.get("code") not in (0, "0", None):
            raise AdapterFailure(f"视频提交失败: {body.get('message')}")
        task_id = (body.get("data") or {}).get("task_id")
        if not task_id:
            raise AdapterFailure(f"视频提交未返回 task_id: {str(body)[:200]}")
        return str(task_id)

    def poll(self, task_id: str) -> dict:
        try:
            r = httpx.get(f"{self.submit_url}/{task_id}", headers=self._headers, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise AdapterFailure(f"视频轮询网络错误: {exc}") from exc
        d = (r.json() or {}).get("data") or {}
        status = d.get("task_status", "processing")
        vids = (d.get("task_result") or {}).get("videos") or d.get("works") or []
        url = vids[0].get("url") if vids else None
        return {"status": status, "result_url": url, "msg": d.get("task_status_msg", "")}

    def generate(
        self,
        image_bytes: bytes,
        motion: str,
        set_progress: Callable[[int], None] | None = None,
        max_wait: float = 420.0,
        interval: float = 10.0,
    ) -> bytes:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        task_id = self.submit(b64, motion_prompt(motion))
        if set_progress:
            set_progress(15)
        waited = 0.0
        while waited < max_wait:
            time.sleep(interval)
            waited += interval
            st = self.poll(task_id)
            if set_progress:
                set_progress(min(90, 15 + int(waited / max_wait * 75)))
            if st["status"] in ("succeed", "success", "completed"):
                if not st["result_url"]:
                    raise AdapterFailure("视频完成但无下载地址")
                vid = httpx.get(st["result_url"], timeout=180)
                vid.raise_for_status()
                return vid.content
            if st["status"] in ("failed", "error"):
                raise AdapterFailure(f"视频任务失败: {st.get('msg')}")
        raise AdapterFailure("视频生成超时")


def make_video_adapter() -> VideoAdapter:
    # 用规范化的 /v1 根 (容错: RELAY_BASE_URL 误填成完整端点也能纠回), 再去掉 /v1 拼 kling 原生路径。
    root = settings.relay_root.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    submit_url = f"{root}/kling/v1/videos/image2video"
    return VideoAdapter(
        submit_url,
        settings.relay_api_key,
        settings.video_model,
        mode=settings.video_mode,
        duration=settings.video_duration,
        timeout=60.0,
    )
