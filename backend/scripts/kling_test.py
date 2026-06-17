"""Kling 图生视频真实提交+轮询 (探 task 形状)。
用法: python scripts/kling_test.py [图片] [model_name]
"""

import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> None:
    img = Path(sys.argv[1] if len(sys.argv) > 1 else "validation/scenes8/images/night.jpg")
    model_name = sys.argv[2] if len(sys.argv) > 2 else "kling-v1"
    b64 = base64.b64encode(img.read_bytes()).decode()

    root = settings.relay_base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    base = f"{root}/kling/v1/videos/image2video"
    headers = {"Authorization": f"Bearer {settings.relay_api_key}", "Content-Type": "application/json"}
    payload = {
        "model_name": model_name,
        "image": b64,
        "prompt": "slow zoom in, no content change, stable composition",
        "mode": "std",
        "duration": "5",
    }
    print(f"submit -> {base}  model_name={model_name}")
    r = httpx.post(base, json=payload, headers=headers, timeout=60)
    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    try:
        data = (r.json() or {}).get("data") or {}
    except Exception:
        return
    task_id = data.get("task_id")
    if not task_id:
        print("  无 task_id, 停。")
        return
    print(f"  task_id={task_id}")

    for i in range(45):
        time.sleep(10)
        g = httpx.get(f"{base}/{task_id}", headers=headers, timeout=30)
        d = (g.json() or {}).get("data") or {}
        st = d.get("task_status")
        print(f"  [{i}] {st} {d.get('task_status_msg', '')}")
        if st == "succeed":
            tr = d.get("task_result") or {}
            vids = tr.get("videos") or d.get("works") or []
            url = vids[0].get("url") if vids else None
            print(f"  video url: {url}")
            if url:
                out = Path("validation/edit_out")
                out.mkdir(parents=True, exist_ok=True)
                (out / "kling.mp4").write_bytes(httpx.get(url, timeout=180).content)
                print(f"  saved {out / 'kling.mp4'}")
            return
        if st in ("failed", "error"):
            print(f"  失败: {d}")
            return
    print("  轮询超时")


if __name__ == "__main__":
    main()
