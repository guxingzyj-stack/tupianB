"""参数化引擎 + /api/enhance 测试 (任务 2.4)。"""

import app.api.analyze as az
from app.engine.intent_mapper import Operation, parse_intent
from app.engine.param_enhance import apply_operations, image_stats


class _FakeAdapter:
    def __init__(self, result):
        self.result = result

    async def analyze(self, image_b64, mime="image/jpeg"):
        return self.result


_GOOD_RESULT = {
    "scene": "草原",
    "subject": "猎豹",
    "problems": ["主体偏暗"],
    "options": [
        {"name": "动物更清楚", "intent": "主体更清楚、提亮"},
        {"name": "天空更蓝", "intent": "天空更蓝、提亮"},
        {"name": "暖色草原", "intent": "暖色草原、纪录片感"},
    ],
}

# 任务 2.4 要求覆盖的关键词
_COVER_INTENTS = [
    "整体提亮、轻度增强",
    "饱和度提升、色彩增强",
    "降低对比、柔光化",
    "主体更清楚",
    "天空更蓝",
    "通透、清晰",
    "暖色草原",
    "纪录片感",
    "更亮",
    "更柔和",
]


def test_engine_all_intents_run(test_image_path, tmp_path):
    for idx, intent in enumerate(_COVER_INTENTS):
        ops = parse_intent(intent)
        assert ops, f"intent 没解析出操作: {intent}"
        out = tmp_path / f"o{idx}.jpg"
        apply_operations(test_image_path, ops, out)
        assert out.exists() and out.stat().st_size > 0


def test_brightness_increases_luma(test_image_path, tmp_path):
    out = tmp_path / "bright.jpg"
    apply_operations(test_image_path, [Operation("brightness", 0.25)], out)
    assert image_stats(out)["mean_luma"] > image_stats(test_image_path)["mean_luma"]


def test_saturation_increases_sat(test_image_path, tmp_path):
    out = tmp_path / "sat.jpg"
    apply_operations(test_image_path, [Operation("saturation", 0.4)], out)
    assert image_stats(out)["mean_sat"] > image_stats(test_image_path)["mean_sat"]


def test_three_intents_differ(test_image_path, tmp_path):
    """同一张图, 三个不同 intent 出来的结果应肉眼可分辨 (字节不同)。"""
    outs = []
    for i, intent in enumerate(["提亮", "更鲜艳", "更柔和"]):
        out = tmp_path / f"d{i}.jpg"
        apply_operations(test_image_path, parse_intent(intent), out)
        outs.append(out.read_bytes())
    assert len(set(outs)) == 3


def test_never_overwrites_original(test_image_path, tmp_path):
    before = test_image_path.read_bytes()
    out = tmp_path / "x.jpg"
    apply_operations(test_image_path, [Operation("brightness", 0.2)], out)
    assert test_image_path.read_bytes() == before  # 原图一字节没动


def test_enhance_endpoint(client, monkeypatch, test_image_b64):
    monkeypatch.setattr(az, "claude_adapter", _FakeAdapter(_GOOD_RESULT))
    monkeypatch.setattr(az, "backup_adapter", None)

    r = client.post(
        "/api/analyze", json={"device_id": "dev-enh", "image": test_image_b64}
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    for i in range(3):
        e = client.post("/api/enhance", json={"job_id": job_id, "option_index": i})
        assert e.status_code == 200, e.text
        body = e.json()
        assert body["result_image_url"].endswith(f"option_{i + 1}.jpg")
        assert body["processing_ms"] >= 0

    # 越界选项 -> 400
    assert (
        client.post(
            "/api/enhance", json={"job_id": job_id, "option_index": 9}
        ).status_code
        == 400
    )
    # 不存在的 job -> 404
    assert (
        client.post(
            "/api/enhance", json={"job_id": "j_nope", "option_index": 0}
        ).status_code
        == 404
    )
