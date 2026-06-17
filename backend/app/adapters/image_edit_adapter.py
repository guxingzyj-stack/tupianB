"""指令式图像编辑 adapter (老照片生成式修复, 任务 4.2)。

经 relay 的 /v1/images/edits (OpenAI images-edit 格式, multipart) 调用,
默认模型 qwen-image-edit-2509 (relay 实测可用; 无 GFPGAN/ESRGAN, 用指令编辑器替代)。

同步实现 (像参数化引擎一样, 由上层用 asyncio.to_thread 调用)。失败抛 AdapterFailure,
上层 (enhance) 会优雅降级到参数化修图 (PRD §6.5 红线)。
"""

from __future__ import annotations

import base64

import httpx

from app.adapters.base import AdapterFailure
from app.config import settings


class ImageEditAdapter:
    def __init__(self, endpoint: str, api_key: str, model: str, timeout: float = 180.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def edit(
        self,
        image_bytes: bytes,
        prompt: str,
        mime: str = "image/jpeg",
        size: str | None = None,
    ) -> bytes:
        """编辑/修复一张图, 返回结果图字节。失败抛 AdapterFailure。

        size: 如 "1024x768", 让模型保持原比例 (否则即梦会输出方图)。
        """
        files = {"image": ("photo.jpg", image_bytes, mime)}
        data = {"model": self.model, "prompt": prompt, "n": "1"}
        # gpt-image 系列只接受 auto / 1024x1024 / 1536x1024 / 1024x1536; 传任意 WxH 会被拒。
        # 用 "auto" 让它按原图比例自动选档 (实测保持横/竖构图)。其他模型 (如即梦) 用精确尺寸。
        if self.model.startswith("gpt-image"):
            data["size"] = "auto"
        elif size:
            data["size"] = size
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = httpx.post(
                self.endpoint, files=files, data=data, headers=headers, timeout=self.timeout
            )
        except httpx.HTTPError as exc:
            raise AdapterFailure(f"图像编辑网络错误: {exc}") from exc

        if resp.status_code != 200:
            raise AdapterFailure(f"图像编辑 HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            body = resp.json()
            items = body.get("data") or []
        except (ValueError, AttributeError) as exc:
            raise AdapterFailure(f"图像编辑返回结构异常: {exc}") from exc
        if not items:
            raise AdapterFailure("图像编辑无结果")

        first = items[0]
        if first.get("b64_json"):
            try:
                return base64.b64decode(first["b64_json"])
            except Exception as exc:  # noqa: BLE001
                raise AdapterFailure(f"结果 b64 解码失败: {exc}") from exc
        if first.get("url"):
            try:
                r2 = httpx.get(first["url"], timeout=60)
                r2.raise_for_status()
                return r2.content
            except httpx.HTTPError as exc:
                raise AdapterFailure(f"下载结果图失败: {exc}") from exc
        raise AdapterFailure("图像编辑返回既无 b64_json 也无 url")


def make_image_edit_adapter() -> ImageEditAdapter:
    return ImageEditAdapter(
        endpoint=settings.image_edits_url,
        api_key=settings.relay_api_key,
        model=settings.image_edit_model,
        timeout=settings.image_edit_timeout,
    )
