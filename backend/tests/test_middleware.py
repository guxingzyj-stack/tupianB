"""鉴权 + 频次限制中间件测试 (任务 2.5)。"""

import asyncio

import app.middleware.rate_limit as rl
from app.config import settings
from app.middleware.rate_limit import SlidingWindowLimiter


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_limiter_blocks_after_limit():
    clk = _Clock()
    lim = SlidingWindowLimiter(limit=3, window=60.0, clock=clk)

    async def run():
        assert await lim.allow("ip1")
        assert await lim.allow("ip1")
        assert await lim.allow("ip1")
        assert not await lim.allow("ip1")  # 第 4 次被挡
        assert await lim.allow("ip2")  # 另一 IP 不受影响
        clk.t = 61.0  # 窗口过去
        assert await lim.allow("ip1")  # 恢复

    asyncio.run(run())


def test_auth_401_without_token(client, monkeypatch):
    monkeypatch.setattr(settings, "app_token", "secret-token")
    resp = client.post("/api/enhance", json={"job_id": "x", "option_index": 0})
    assert resp.status_code == 401
    assert resp.json()["error"] == "应用 token 不对"

    # 带对的 token 就过了鉴权 (job 不存在 -> 404, 但已不是 401)
    resp2 = client.post(
        "/api/enhance",
        json={"job_id": "x", "option_index": 0},
        headers={"X-App-Token": "secret-token"},
    )
    assert resp2.status_code != 401


def test_health_excluded_from_auth(client, monkeypatch):
    monkeypatch.setattr(settings, "app_token", "secret-token")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_rate_limit_429(client, monkeypatch, test_image_b64):
    async def deny(key):
        return False

    monkeypatch.setattr(rl.limiter, "allow", deny)
    resp = client.post(
        "/api/analyze", json={"device_id": "d", "image": test_image_b64}
    )
    assert resp.status_code == 429
    assert resp.json()["error"] == "操作太频繁，稍等一下"
