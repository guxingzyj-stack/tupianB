"""POST /api/enhance —— 把用户选的方向跑成实际修图结果 (PRD §6)。

普通照片: 参数化引擎 (parse_intent + apply_operations)。
老照片 (analyze 判定 is_old_photo): 走生成式图像编辑 (qwen-image-edit 等);
        失败则优雅降级到参数化 (PRD §6.5 红线: 图像编辑模型挂 -> 只给参数化结果)。
绝不覆盖原图。
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel

from app.adapters.base import AdapterFailure
from app.adapters.image_edit_adapter import make_image_edit_adapter
from app.engine.intent_mapper import parse_intent
from app.engine.old_photo_detector import is_restore_option, restore_prompt_for
from app.engine.param_enhance import apply_operations
from app.storage import db
from app.storage.files import output_dir, to_url

logger = logging.getLogger("laozhao.enhance")
router = APIRouter()

# 单例, 测试可 monkeypatch
image_edit_adapter = make_image_edit_adapter()


class EnhanceRequest(BaseModel):
    job_id: str
    option_index: int  # 0 / 1 / 2


def _save_image_bytes(raw: bytes, path: Path) -> None:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=92)


def _edit_size(raw: bytes) -> str | None:
    """从原图算出 size 字符串, 让图像模型保持原比例 (否则即梦会输出方图)。"""
    try:
        w, h = Image.open(io.BytesIO(raw)).size
        scale = min(1.0, 1536 / max(w, h))
        return f"{max(1, round(w * scale))}x{max(1, round(h * scale))}"
    except Exception:  # noqa: BLE001
        return None


@router.post("/enhance")
async def enhance(req: EnhanceRequest):
    job = db.get_job(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="找不到这次修图，请重新选照片")

    meta = job.get("metadata") or {}
    analysis = meta.get("analysis") or {}
    options = analysis.get("options") or []

    i = req.option_index
    if not isinstance(i, int) or i < 0 or i >= len(options):
        raise HTTPException(status_code=400, detail="这个选项不对，请重新选")

    intent = options[i].get("intent", "")
    name = options[i].get("name", "")
    in_path = job.get("input_path")
    if not in_path or not Path(in_path).exists():
        raise HTTPException(status_code=404, detail="原图丢失了，请重新选照片")

    device_id = job["device_id"]
    out_path = output_dir(device_id, req.job_id) / f"option_{i + 1}.jpg"
    is_old = bool(analysis.get("is_old_photo"))
    # 与不稳定的 cv2 老照片判别解耦: 用户选了"修复/上色"类选项就走生成式 (gpt-image-2)。
    use_restore = is_old or is_restore_option(name, intent)

    t0 = time.perf_counter()
    method = "param"

    # 老照片: 先试生成式修复。relay 偶发 429/网络抖动 -> 重试几次再降级 (429 失败很快,
    # 真正出图才慢, 所以多次重试通常仍在可接受时长内)。
    if use_restore:
        prompt = restore_prompt_for(name)
        original = await asyncio.to_thread(Path(in_path).read_bytes)
        size = _edit_size(original)
        for attempt in range(3):
            try:
                result = await asyncio.to_thread(
                    image_edit_adapter.edit, original, prompt, "image/jpeg", size
                )
                await asyncio.to_thread(_save_image_bytes, result, out_path)
                method = "generative"
                break
            except AdapterFailure as exc:
                logger.warning(
                    "生成式修复第 %d/3 次失败 job=%s: %s", attempt + 1, req.job_id, exc
                )
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
            except Exception:  # noqa: BLE001
                logger.exception("生成式修复异常 job=%s", req.job_id)
                break
        if method != "generative":
            logger.warning("生成式修复多次失败, 降级参数化 job=%s", req.job_id)

    # 普通照片, 或老照片生成式失败的降级
    if method != "generative":
        operations = parse_intent(intent)
        try:
            await asyncio.to_thread(apply_operations, in_path, operations, out_path)
        except Exception:  # noqa: BLE001
            logger.exception("参数化修图失败 job=%s option=%s", req.job_id, i)
            raise HTTPException(status_code=500, detail="这张图没修成，换个样子试试")

    processing_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "result_image_url": to_url(out_path),
        "processing_ms": processing_ms,
        "option_name": name,
        "method": method,
    }
