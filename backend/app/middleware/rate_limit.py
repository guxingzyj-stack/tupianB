"""IP 维度频次限制中间件 (架构 §5.2 / 任务 2.5)。

- 默认 60 次/分钟/IP (RATE_LIMIT_PER_MIN)。
- 纯内存滑动窗口, 不引 Redis。临界区极小且不跨 await, 用 threading.Lock
  既线程安全又不与事件循环绑定 (TestClient 多次起循环也没问题)。
- 应用重启计数归零 (可接受)。
- 超限返回 429 + 人话提示。
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_EXCLUDED = {"/api/health"}


class SlidingWindowLimiter:
    """每个 key (IP) 一个时间戳队列, 维持最近 window 秒内的命中。"""

    def __init__(
        self,
        limit: int,
        window: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def allow(self, key: str) -> bool:
        now = self.clock()
        cutoff = now - self.window
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= self.limit:
                return False
            dq.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 模块级单例 (测试可 monkeypatch limiter.allow 或调小 limiter.limit)
limiter = SlidingWindowLimiter(limit=settings.rate_limit_per_min, window=60.0)


def _client_ip(request) -> str:
    # Zeabur / 反向代理会带 X-Forwarded-For, 取第一跳
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path in _EXCLUDED:
            return await call_next(request)
        if not await limiter.allow(_client_ip(request)):
            return JSONResponse({"error": "操作太频繁，稍等一下"}, status_code=429)
        return await call_next(request)
