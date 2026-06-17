"""SQLite 数据层。

设计取舍 (见架构 §3.4):
  - 不用 ORM, 直接 sqlite3 标准库 (自用规模够用)。
  - 所有写操作走事务, 失败回滚 (get_db 上下文管理器负责)。
  - 主键用 uuid4 字符串, 不用自增。
  - created_at / updated_at 存 unix 时间戳 (整数)。
  - 建表用 CREATE TABLE IF NOT EXISTS, 不做迁移工具。
"""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from app.config import settings

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


# --------------------------------------------------------------------------- #
# 连接 / 初始化
# --------------------------------------------------------------------------- #
def _connect() -> sqlite3.Connection:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL: 读写并发更友好; 单实例自用足够。
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """事务上下文。正常退出自动 commit, 异常回滚。"""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """建表 (幂等)。应用启动时调用。"""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_db() as conn:
        conn.executescript(schema)


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def now_ts() -> int:
    return int(time.time())


def new_id(prefix: str = "j_") -> str:
    return prefix + uuid.uuid4().hex


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    if "metadata_json" in d:
        d["metadata"] = json.loads(d["metadata_json"]) if d["metadata_json"] else None
    if "config_json" in d:
        d["config"] = json.loads(d["config_json"]) if d["config_json"] else None
    return d


# --------------------------------------------------------------------------- #
# jobs 表
# --------------------------------------------------------------------------- #
def create_job(
    job_id: str,
    device_id: str,
    type: str,
    status: str = "pending",
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    ts = now_ts()
    meta = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None
    with get_db() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, device_id, type, status, input_path, output_path,
                metadata_json, created_at, updated_at, error_msg)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
            (job_id, device_id, type, status, input_path, output_path, meta, ts, ts),
        )


def update_job_status(
    job_id: str,
    status: Optional[str] = None,
    output_path: Optional[str] = None,
    metadata: Optional[dict] = None,
    error_msg: Optional[str] = None,
) -> None:
    sets = ["updated_at = ?"]
    vals: list[Any] = [now_ts()]
    if status is not None:
        sets.append("status = ?")
        vals.append(status)
    if output_path is not None:
        sets.append("output_path = ?")
        vals.append(output_path)
    if metadata is not None:
        sets.append("metadata_json = ?")
        vals.append(json.dumps(metadata, ensure_ascii=False))
    if error_msg is not None:
        sets.append("error_msg = ?")
        vals.append(error_msg)
    vals.append(job_id)
    with get_db() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)


def get_job(job_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row)


def list_jobs_by_device(device_id: str, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE device_id = ? ORDER BY created_at DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]  # type: ignore[misc]


def set_job_progress(job_id: str, progress: int) -> None:
    """更新任务进度 (0-100), 保留 metadata 其余字段。"""
    job = get_job(job_id)
    if job is None:
        return
    meta = job.get("metadata") or {}
    meta["progress"] = int(progress)
    update_job_status(job_id, metadata=meta)


def count_jobs_today(device_id: str, type: str) -> int:
    """某设备今天 (最近 24h) 某类型成功/进行中的任务数, 用于日上限。"""
    since = now_ts() - 24 * 3600
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS c FROM jobs
               WHERE device_id = ? AND type = ? AND created_at >= ?
                 AND status != 'failed'""",
            (device_id, type, since),
        ).fetchone()
    return int(row["c"]) if row else 0


# --------------------------------------------------------------------------- #
# devices 表
# --------------------------------------------------------------------------- #
def get_or_create_device(device_id: str, **defaults: Any) -> dict:
    with get_db() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO devices
               (device_id, nickname, daily_budget_cny, daily_video_limit,
                preferred_style, enable_video, enable_animate_old, config_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                device_id,
                defaults.get("nickname"),
                defaults.get("daily_budget_cny", 10.0),
                defaults.get("daily_video_limit", 10),
                defaults.get("preferred_style"),
                int(defaults.get("enable_video", 1)),
                int(defaults.get("enable_animate_old", 0)),
                None,
                now_ts(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
    return _row_to_dict(row)  # type: ignore[return-value]


def get_device(device_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
    return _row_to_dict(row)


_DEVICE_COLUMNS = {
    "nickname",
    "daily_budget_cny",
    "daily_video_limit",
    "preferred_style",
    "enable_video",
    "enable_animate_old",
}


def update_device_config(device_id: str, **fields: Any) -> None:
    """更新设备配置。config 走单独 JSON 列, 其余按白名单落普通列。"""
    sets: list[str] = []
    vals: list[Any] = []
    for key, value in fields.items():
        if key == "config":
            sets.append("config_json = ?")
            vals.append(json.dumps(value, ensure_ascii=False) if value is not None else None)
        elif key in _DEVICE_COLUMNS:
            sets.append(f"{key} = ?")
            vals.append(value)
        # 未知字段静默忽略, 避免 SQL 注入面
    if not sets:
        return
    vals.append(device_id)
    with get_db() as conn:
        conn.execute(f"UPDATE devices SET {', '.join(sets)} WHERE device_id = ?", vals)
