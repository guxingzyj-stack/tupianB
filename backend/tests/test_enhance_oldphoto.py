"""老照片生成式 enhance + 降级测试 (任务 4.2)。"""

import io

import numpy as np
from PIL import Image

import app.api.enhance as en
from app.adapters.base import AdapterFailure
from app.storage import db
from app.storage.files import input_path


def _jpg(w=80, h=80) -> bytes:
    arr = np.random.default_rng(3).integers(0, 256, (h, w, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, "JPEG")
    return buf.getvalue()


def _make_old_job(device: str) -> str:
    db.get_or_create_device(device)
    job_id = db.new_id("j_")
    p = input_path(device, job_id)
    p.write_bytes(_jpg())
    db.create_job(
        job_id, device, type="analyze", status="success", input_path=str(p),
        metadata={
            "analysis": {
                "is_old_photo": True,
                "options": [
                    {"name": "修旧如新", "intent": "去模糊+去划痕+褪色还原"},
                    {"name": "变成彩色", "intent": "黑白上色"},
                    {"name": "脸更清楚", "intent": "GFPGAN 人脸专修"},
                ],
            },
            "device_id": device,
        },
    )
    return job_id


class _FakeEdit:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = 0

    def edit(self, image_bytes, prompt, mime="image/jpeg", size=None):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.result


def test_oldphoto_uses_generative(client, monkeypatch):
    job_id = _make_old_job("dev-gen")
    fake = _FakeEdit(result=_jpg(120, 120))
    monkeypatch.setattr(en, "image_edit_adapter", fake)

    r = client.post("/api/enhance", json={"job_id": job_id, "option_index": 0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["method"] == "generative"
    assert fake.calls == 1
    assert body["result_image_url"].endswith("option_1.jpg")


def test_oldphoto_falls_back_to_param_when_relay_down(client, monkeypatch):
    job_id = _make_old_job("dev-fb")
    fake = _FakeEdit(exc=AdapterFailure("relay 429 上游负载饱和"))
    monkeypatch.setattr(en, "image_edit_adapter", fake)

    r = client.post("/api/enhance", json={"job_id": job_id, "option_index": 0})
    assert r.status_code == 200, r.text  # 不报错给用户
    body = r.json()
    assert body["method"] == "param"  # 优雅降级到参数化
    assert fake.calls == 1
    assert body["result_image_url"].endswith("option_1.jpg")
