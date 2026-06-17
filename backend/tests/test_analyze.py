"""/api/analyze 测试 (任务 2.3: happy path + fallback)。"""

import app.api.analyze as az
from app.adapters.base import AdapterFailure


class _FakeAdapter:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc

    async def analyze(self, image_b64, mime="image/jpeg"):
        if self.exc is not None:
            raise self.exc
        return self.result


_GOOD_RESULT = {
    "scene": "公园逆光",
    "subject": "小孩",
    "problems": ["脸偏暗"],
    "options": [
        {"name": "脸更亮", "intent": "主体更清楚、提亮"},
        {"name": "背景柔和", "intent": "柔和"},
        {"name": "色彩鲜艳", "intent": "色彩增强"},
    ],
}


def test_analyze_happy_path(client, monkeypatch, test_image_b64):
    monkeypatch.setattr(az, "claude_adapter", _FakeAdapter(result=_GOOD_RESULT))
    monkeypatch.setattr(az, "backup_adapter", None)

    resp = client.post(
        "/api/analyze", json={"device_id": "dev-happy", "image": test_image_b64}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["job_id"].startswith("j_")
    assert data["base_image_url"] and data["base_image_url"].endswith("base.jpg")
    opts = data["analysis"]["options"]
    assert len(opts) == 3
    assert [o["name"] for o in opts] == ["脸更亮", "背景柔和", "色彩鲜艳"]
    # 三选项 name 都 <= 5 字
    assert all(len(o["name"]) <= 5 for o in opts)


def test_analyze_fallback_on_failure(client, monkeypatch, test_image_b64):
    monkeypatch.setattr(
        az, "claude_adapter", _FakeAdapter(exc=AdapterFailure("relay 挂了"))
    )
    monkeypatch.setattr(az, "backup_adapter", None)

    resp = client.post(
        "/api/analyze", json={"device_id": "dev-fb", "image": test_image_b64}
    )
    assert resp.status_code == 200, resp.text
    names = [o["name"] for o in resp.json()["analysis"]["options"]]
    assert names == ["更明亮", "更鲜艳", "更柔和"]
    # 即便 AI 挂了, 基础修复版也要有
    assert resp.json()["base_image_url"]


def test_analyze_fallback_on_bad_schema(client, monkeypatch, test_image_b64):
    bad = {"options": [{"name": "暗部提亮高光压制超长名", "intent": "x"}]}
    monkeypatch.setattr(az, "claude_adapter", _FakeAdapter(result=bad))
    monkeypatch.setattr(az, "backup_adapter", None)

    resp = client.post(
        "/api/analyze", json={"device_id": "dev-bad", "image": test_image_b64}
    )
    assert resp.status_code == 200
    names = [o["name"] for o in resp.json()["analysis"]["options"]]
    assert names == ["更明亮", "更鲜艳", "更柔和"]


def test_analyze_backup_used(client, monkeypatch, test_image_b64):
    monkeypatch.setattr(
        az, "claude_adapter", _FakeAdapter(exc=AdapterFailure("主模型挂"))
    )
    monkeypatch.setattr(az, "backup_adapter", _FakeAdapter(result=_GOOD_RESULT))

    resp = client.post(
        "/api/analyze", json={"device_id": "dev-bk", "image": test_image_b64}
    )
    assert resp.status_code == 200
    names = [o["name"] for o in resp.json()["analysis"]["options"]]
    assert names == ["脸更亮", "背景柔和", "色彩鲜艳"]


def test_analyze_bad_image(client, monkeypatch):
    monkeypatch.setattr(az, "claude_adapter", _FakeAdapter(result=_GOOD_RESULT))
    resp = client.post(
        "/api/analyze", json={"device_id": "dev-x", "image": "这不是合法base64@@@"}
    )
    assert resp.status_code == 400
    assert "图片" in resp.json()["detail"]
