"""POST /api/analyze —— 整个项目最核心的接口 (PRD §5, 架构 §3.6)。

流程:
  1. 建 job (running) + 保存原图
  2. 立刻用参数化引擎生成"基础修复版" (即使 AI 挂了也有结果)
  3. 调 Claude 看图给三选项 (硬超时); 失败/不合格 -> 备用模型 -> 通用三选项
  4. 更新 job, 返回 { job_id, base_image_url, analysis }

红线: 任何失败都退兜底, 绝不把技术错误抛给客户端。
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from app.adapters.base import AdapterFailure
from app.adapters.claude_adapter import make_claude_adapter
from app.adapters.gpt_adapter import make_gpt_adapter
from app.config import settings
from app.engine.old_photo_detector import analyze_oldness, old_photo_options
from app.engine.param_enhance import make_base_repair
from app.prompts.analyze_prompt import (
    PROMPT_VERSION,
    SCHEMA_VALIDATOR,
    fallback_analysis,
)
from app.storage import db
from app.storage.files import (
    decode_image_b64,
    input_path,
    output_dir,
    sanitize_id,
    to_url,
)

logger = logging.getLogger("laozhao.analyze")
router = APIRouter()

# adapter 单例。测试通过 monkeypatch 本模块的这两个名字来替换。
claude_adapter = make_claude_adapter()
backup_adapter = make_gpt_adapter()

_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "HEIC": "image/jpeg",  # 退化处理
}


class AnalyzeRequest(BaseModel):
    device_id: str
    image: str | None = None  # base64 (可带 data: 前缀)
    image_url: str | None = None  # 预留


def _save_input(raw: bytes, path: Path) -> None:
    """把上传的原图统一转存为 JPEG (尊重 EXIF 方向)。"""
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=95)


async def _analyze_with_fallback(image_b64: str, mime: str) -> dict:
    """主模型 -> 备用模型 -> 通用兜底。永不抛错。"""
    for adapter, label in ((claude_adapter, "claude"), (backup_adapter, "gpt")):
        if adapter is None:
            continue
        try:
            result = await asyncio.wait_for(
                adapter.analyze(image_b64, mime=mime),
                timeout=settings.claude_timeout + 2.0,
            )
            if SCHEMA_VALIDATOR(result):
                result.setdefault("scene", "")
                result.setdefault("subject", "")
                result.setdefault("problems", [])
                result["model"] = label
                result["fallback"] = False
                return result
            logger.warning("模型 %s 返回未通过 schema 校验, 尝试下一个", label)
        except asyncio.TimeoutError:
            logger.warning("模型 %s 调用超时", label)
        except AdapterFailure as exc:
            logger.warning("模型 %s 调用失败: %s", label, exc)
        except Exception:  # noqa: BLE001 —— 红线: 绝不让异常冒泡到客户端
            logger.exception("模型 %s 调用出现未预期异常", label)
    return fallback_analysis()


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    device_id = sanitize_id(req.device_id)
    db.get_or_create_device(device_id)
    job_id = db.new_id("j_")

    if not req.image:
        raise HTTPException(status_code=400, detail="没有收到照片，请重新选一张")

    # 解码 + 校验图片格式
    try:
        raw = decode_image_b64(req.image)
        probe = Image.open(io.BytesIO(raw))
        fmt = (probe.format or "JPEG").upper()
        probe.verify()  # 校验完整性
    except (ValueError, UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="图片格式不对，请换一张试试")

    mime = _MIME_BY_FORMAT.get(fmt, "image/jpeg")

    # 保存原图
    in_path = input_path(device_id, job_id)
    await asyncio.to_thread(_save_input, raw, in_path)
    db.create_job(
        job_id, device_id, type="analyze", status="running", input_path=str(in_path)
    )

    # 基础修复版 (始终尝试生成)
    base_path = output_dir(device_id, job_id) / "base.jpg"
    base_url = None
    try:
        await asyncio.to_thread(make_base_repair, in_path, base_path)
        base_url = to_url(base_path)
    except Exception:  # noqa: BLE001
        logger.exception("基础修复版生成失败 job=%s", job_id)

    # AI 看图 (用原始 bytes 的干净 base64)
    clean_b64 = base64.b64encode(raw).decode("ascii")
    analysis = await _analyze_with_fallback(clean_b64, mime)
    analysis["prompt_version"] = PROMPT_VERSION

    # 老照片判别 (任务 4.1): 命中 -> 换成预设老照片三选项 (PRD §7.1/§7.3)
    try:
        oldness = await asyncio.to_thread(
            analyze_oldness, in_path, analysis.get("scene", "")
        )
        if oldness["is_old"]:
            analysis["options"] = old_photo_options(oldness["is_bw"])
            analysis["is_old_photo"] = True
            analysis["old_signals"] = oldness["signals"]
            logger.info("判为老照片 job=%s signals=%s", job_id, oldness["signals"])
    except Exception:  # noqa: BLE001
        logger.exception("老照片判别失败 job=%s", job_id)

    db.update_job_status(
        job_id,
        status="success",
        metadata={
            "analysis": analysis,
            "base_path": str(base_path),
            "device_id": device_id,
        },
    )

    return {
        "job_id": job_id,
        "base_image_url": base_url,
        "analysis": {
            "scene": analysis.get("scene", ""),
            "subject": analysis.get("subject", ""),
            "problems": analysis.get("problems", []),
            "is_old_photo": analysis.get("is_old_photo", False),
            "options": [
                {"name": o["name"], "intent": o["intent"]}
                for o in analysis["options"]
            ],
        },
    }
