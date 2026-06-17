"""简易异步任务队列 (任务 5.1)。

asyncio.Queue + N 个后台 worker, 不引 Celery/Redis。
worker 对单个任务的异常做兜底 (标 failed 后继续取下一个), 不会因任务报错而死。
任务状态/进度持久化到 SQLite jobs 表。进程退出时优雅 shutdown。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from app.config import settings
from app.storage import db

logger = logging.getLogger("laozhao.jobs")

# handler(job_id, payload, set_progress) -> result dict (含 output_path / result_url)
Handler = Callable[[str, dict, Callable[[int], None]], Awaitable[dict]]


class JobQueue:
    def __init__(self, worker_count: int = 2):
        self.worker_count = max(1, worker_count)
        self._q: asyncio.Queue = asyncio.Queue()
        self._handlers: dict[str, Handler] = {}
        self._workers: list[asyncio.Task] = []
        self._started = False

    def register(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    async def start(self) -> None:
        if self._started:
            return
        # 绑定到当前事件循环 (TestClient 每次可能新建循环)
        self._q = asyncio.Queue()
        self._started = True
        self._workers = [
            asyncio.create_task(self._worker(i)) for i in range(self.worker_count)
        ]
        logger.info("任务队列启动, worker=%d", self.worker_count)

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._started = False
        for w in self._workers:
            w.cancel()
        for w in self._workers:
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers = []

    def enqueue(self, job_type: str, device_id: str, payload: dict, id_prefix: str = "v_") -> str:
        job_id = db.new_id(id_prefix)
        db.create_job(
            job_id, device_id, type=job_type, status="pending",
            metadata={"payload": payload, "progress": 0},
        )
        self._q.put_nowait((job_id, job_type, payload))
        return job_id

    def get_status(self, job_id: str) -> Optional[dict]:
        job = db.get_job(job_id)
        if not job:
            return None
        meta = job.get("metadata") or {}
        status = job["status"]
        return {
            "status": status,
            "progress": 100 if status == "success" else int(meta.get("progress", 0)),
            "result_url": (meta.get("result") or {}).get("result_url")
            if status == "success"
            else None,
            "error": job.get("error_msg") if status == "failed" else None,
        }

    async def _worker(self, idx: int) -> None:
        while True:
            try:
                job_id, job_type, payload = await self._q.get()
            except asyncio.CancelledError:
                break
            try:
                db.update_job_status(job_id, status="running")
                handler = self._handlers.get(job_type)
                if handler is None:
                    raise RuntimeError(f"没有注册 {job_type} 的 handler")

                def set_progress(pct: int, _jid: str = job_id) -> None:
                    db.set_job_progress(_jid, pct)

                result = await handler(job_id, payload, set_progress)
                meta = (db.get_job(job_id) or {}).get("metadata") or {}
                meta["result"] = result
                meta["progress"] = 100
                db.update_job_status(
                    job_id, status="success",
                    output_path=result.get("output_path"), metadata=meta,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — 单任务失败不拖垮 worker
                logger.exception("任务失败 job=%s", job_id)
                db.update_job_status(job_id, status="failed", error_msg=str(exc)[:300])
            finally:
                self._q.task_done()


queue = JobQueue(worker_count=settings.worker_count)
