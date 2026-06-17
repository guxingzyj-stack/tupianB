"""数据层测试 (任务 2.2: 5 个核心操作)。"""

import sqlite3

from app.config import settings
from app.storage import db


def test_init_creates_tables():
    db.init_db()
    conn = sqlite3.connect(settings.db_path)
    try:
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "jobs" in names
    assert "devices" in names


def test_create_and_get_job():
    job_id = db.new_id("j_")
    db.create_job(
        job_id,
        device_id="dev-A",
        type="analyze",
        status="running",
        input_path="/tmp/x.jpg",
        metadata={"k": "值中文", "n": 3},
    )
    job = db.get_job(job_id)
    assert job is not None
    assert job["id"] == job_id
    assert job["device_id"] == "dev-A"
    assert job["type"] == "analyze"
    assert job["status"] == "running"
    assert job["input_path"] == "/tmp/x.jpg"
    # metadata JSON 往返
    assert job["metadata"]["k"] == "值中文"
    assert job["metadata"]["n"] == 3
    assert isinstance(job["created_at"], int)


def test_update_job_status():
    job_id = db.new_id("j_")
    db.create_job(job_id, device_id="dev-B", type="enhance", status="running")
    db.update_job_status(
        job_id,
        status="success",
        output_path="/tmp/out.jpg",
        metadata={"done": True},
    )
    job = db.get_job(job_id)
    assert job["status"] == "success"
    assert job["output_path"] == "/tmp/out.jpg"
    assert job["metadata"]["done"] is True

    db.update_job_status(job_id, status="failed", error_msg="boom")
    job = db.get_job(job_id)
    assert job["status"] == "failed"
    assert job["error_msg"] == "boom"


def test_list_jobs_by_device():
    dev = "dev-list"
    ids = []
    for _ in range(3):
        jid = db.new_id("j_")
        db.create_job(jid, device_id=dev, type="analyze", status="success")
        ids.append(jid)
    rows = db.list_jobs_by_device(dev)
    assert len(rows) == 3
    assert {r["id"] for r in rows} == set(ids)
    # 按 created_at 倒序 (不报错即可, 时间戳秒级可能相等)
    assert all(r["device_id"] == dev for r in rows)


def test_device_create_and_update():
    dev = "dev-cfg"
    d1 = db.get_or_create_device(dev)
    assert d1["device_id"] == dev
    assert d1["daily_budget_cny"] == 10.0
    assert d1["daily_video_limit"] == 10
    assert d1["enable_video"] == 1
    assert d1["enable_animate_old"] == 0

    # 幂等: 再次 create 不报错, 不重置
    d2 = db.get_or_create_device(dev, daily_budget_cny=999)
    assert d2["daily_budget_cny"] == 10.0  # 已存在, 不被默认覆盖

    db.update_device_config(
        dev, nickname="王奶奶", daily_budget_cny=20.0, enable_video=0,
        config={"theme": "big"},
    )
    d3 = db.get_device(dev)
    assert d3["nickname"] == "王奶奶"
    assert d3["daily_budget_cny"] == 20.0
    assert d3["enable_video"] == 0
    assert d3["config"]["theme"] == "big"
