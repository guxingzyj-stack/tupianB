"""异步队列 (5.1) + 视频/任务接口 (5.2) + 模板接口 (5.4) 管道测试。
视频实际出片被 relay 挡, 这里用 mock handler 验证编排管道。"""

import asyncio

from app.jobs.queue import JobQueue, queue as app_queue
from app.storage import db


# --------------------------- 5.1 队列本身 --------------------------- #
def test_queue_runs_job_to_success():
    async def run():
        q = JobQueue(worker_count=2)

        async def handler(job_id, payload, set_progress):
            set_progress(50)
            return {"output_path": f"/x/{job_id}.mp4", "result_url": "http://x/v.mp4"}

        q.register("video", handler)
        await q.start()
        jid = q.enqueue("video", "dev-q", {"a": 1})
        st = None
        for _ in range(200):
            st = q.get_status(jid)
            if st["status"] in ("success", "failed"):
                break
            await asyncio.sleep(0.02)
        await q.shutdown()
        return st

    st = asyncio.run(run())
    assert st["status"] == "success"
    assert st["result_url"] == "http://x/v.mp4"
    assert st["progress"] == 100


def test_queue_marks_failed_on_handler_error():
    async def run():
        q = JobQueue(worker_count=1)

        async def handler(job_id, payload, set_progress):
            raise RuntimeError("boom")

        q.register("video", handler)
        await q.start()
        jid = q.enqueue("video", "dev-qf", {})
        st = None
        for _ in range(200):
            st = q.get_status(jid)
            if st["status"] in ("success", "failed"):
                break
            await asyncio.sleep(0.02)
        await q.shutdown()
        return st

    st = asyncio.run(run())
    assert st["status"] == "failed"
    assert st["error"]


# --------------------------- 5.2 视频/任务接口 --------------------------- #
def test_video_api_flow(client):
    async def fake(job_id, payload, set_progress):
        set_progress(80)
        return {"output_path": f"/v/{job_id}.mp4", "result_url": f"http://test/{job_id}.mp4"}

    app_queue.register("video", fake)  # 覆盖真 handler

    r = client.post(
        "/api/video",
        json={"device_id": "dev-vid", "image_url": "http://x/o.jpg", "motion": "subtle_human"},
    )
    assert r.status_code == 200, r.text
    jid = r.json()["job_id"]
    assert jid.startswith("v_")
    assert r.json()["status"] == "pending"

    final = None
    for _ in range(80):
        s = client.get(f"/api/jobs/{jid}")
        assert s.status_code == 200
        final = s.json()
        if final["status"] in ("success", "failed"):
            break
    assert final["status"] == "success", final
    assert final["result_url"].endswith(".mp4")


def test_video_daily_limit(client):
    async def fake(job_id, payload, set_progress):
        return {"result_url": "http://x/v.mp4"}

    app_queue.register("video", fake)
    db.get_or_create_device("dev-lim")
    db.update_device_config("dev-lim", daily_video_limit=1)

    r1 = client.post("/api/video", json={"device_id": "dev-lim", "image_url": "u"})
    assert r1.status_code == 200
    r2 = client.post("/api/video", json={"device_id": "dev-lim", "image_url": "u"})
    assert r2.status_code == 429


def test_jobs_404(client):
    assert client.get("/api/jobs/v_nope").status_code == 404


# --------------------------- 5.4 模板接口 --------------------------- #
def test_templates_list(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) == 4
    assert all(len(c["templates"]) >= 3 for c in cats)


def test_template_apply_enqueues(client):
    r = client.post(
        "/api/template/apply",
        json={"device_id": "dev-t", "template_id": "midautumn", "image_url": "http://x/o.jpg", "text_index": 1},
    )
    assert r.status_code == 200
    assert r.json()["job_id"].startswith("t_")


def test_template_apply_unknown(client):
    r = client.post(
        "/api/template/apply",
        json={"device_id": "dev-t", "template_id": "nope", "image_url": "u"},
    )
    assert r.status_code == 404
