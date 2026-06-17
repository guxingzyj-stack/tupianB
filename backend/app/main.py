"""FastAPI 入口。

启动时:
  - 确保数据目录存在
  - 初始化 SQLite (CREATE TABLE IF NOT EXISTS)

中间件顺序 (请求进入方向): RateLimit -> Auth -> 业务。
Starlette 中后加的中间件在更外层, 所以先 add Auth, 再 add RateLimit。

静态文件: /files/* 映射到 FILE_BASE, 用于把修好的图/视频以 URL 形式返回给客户端。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.storage.db import init_db
from app.storage.files import ensure_dirs
from app.middleware.auth import AppTokenMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api import health, analyze, enhance, video, template, upload
from app.jobs.queue import queue
from app.jobs.handlers import video_handler, template_handler

# 在构造静态文件挂载之前就要保证目录存在。
ensure_dirs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    init_db()
    queue.register("video", video_handler)
    queue.register("template", template_handler)
    await queue.start()
    yield
    await queue.shutdown()


app = FastAPI(
    title="老照 · AI 照片补救",
    description="给老年人用的 AI 照片补救后端 (自用版 v0.1)",
    version=__version__,
    lifespan=lifespan,
)

# 先 Auth (内层), 再 RateLimit (外层) -> 实际请求顺序 RateLimit -> Auth
app.add_middleware(AppTokenMiddleware)
app.add_middleware(RateLimitMiddleware)
# CORS 放最外层: 预检 OPTIONS 不带 X-App-Token, 必须先于 auth 处理掉。
# 自用版放开所有来源 (无 cookie, 不用 credentials)。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用户图片/视频对外以 URL 提供 (24h 临时, 清理由后台 cron 负责)
app.mount("/files", StaticFiles(directory=settings.file_base, check_dir=False), name="files")

# 业务路由
app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(enhance.router, prefix="/api")
app.include_router(video.router, prefix="/api")
app.include_router(template.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.get("/")
async def root():
    return {"app": "老照 backend", "version": __version__, "docs": "/docs"}
