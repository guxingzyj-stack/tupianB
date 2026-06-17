"""X-App-Token 鉴权中间件 (架构 §5.2)。

- 所有 /api/* 需要 header X-App-Token, 值 = 环境变量 APP_TOKEN。
- /api/health 排除 (探活)。
- APP_TOKEN 留空 = 关闭鉴权 (仅本地开发); 线上务必设置。
不做 JWT、不做用户表 —— 自用版靠"不公开 URL" + 这道简单 token。
"""

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_EXCLUDED = {"/api/health"}


class AppTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in _EXCLUDED:
            expected = settings.app_token
            if expected:  # 配了 token 才校验
                if request.headers.get("X-App-Token") != expected:
                    return JSONResponse({"error": "应用 token 不对"}, status_code=401)
        return await call_next(request)
