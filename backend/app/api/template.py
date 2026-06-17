"""模板系统 (任务 5.4)。

GET  /api/templates       列出分类与模板 (从 JSON 配置读)
POST /api/template/apply  应用模板 (入队, 异步合成)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.jobs.queue import queue
from app.storage.files import sanitize_id

router = APIRouter()

_CONFIG = Path(__file__).resolve().parent.parent / "templates" / "templates.json"


@lru_cache(maxsize=1)
def _load_templates() -> dict:
    return json.loads(_CONFIG.read_text(encoding="utf-8"))


def _find_template(template_id: str) -> dict | None:
    for cat in _load_templates().get("categories", []):
        for t in cat.get("templates", []):
            if t.get("id") == template_id:
                return t
    return None


@router.get("/templates")
async def list_templates():
    return _load_templates()


class TemplateApplyRequest(BaseModel):
    device_id: str
    template_id: str
    image_url: str
    text_index: int = 0


@router.post("/template/apply")
async def apply_template(req: TemplateApplyRequest):
    tpl = _find_template(req.template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="没找到这个模板")
    texts = tpl.get("texts", [])
    text = texts[req.text_index] if 0 <= req.text_index < len(texts) else (texts[0] if texts else "")
    device_id = sanitize_id(req.device_id)
    job_id = queue.enqueue(
        "template",
        device_id,
        {
            "device_id": device_id,
            "template_id": req.template_id,
            "image_url": req.image_url,
            "text": text,
            "image_intent": tpl.get("image_intent", ""),
            "video_motion": tpl.get("video_motion", "slow_zoom"),
            "music": tpl.get("music", ""),
        },
        id_prefix="t_",
    )
    return {"job_id": job_id, "status": "pending"}
