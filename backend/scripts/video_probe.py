"""探测 relay 图生视频接口的真实形状 (任务 5.2)。
试几种候选端点/字段, 打印每个的 HTTP + 响应片段, 据报错收敛。
用法: python scripts/video_probe.py [图片] [模型]
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402

PROMPT = "slow zoom in, no content change, stable composition"


def main() -> None:
    img = Path(sys.argv[1] if len(sys.argv) > 1 else "validation/scenes8/images/night.jpg")
    model = sys.argv[2] if len(sys.argv) > 2 else "kling-avatar-image2video"
    raw = img.read_bytes()
    b64 = base64.b64encode(raw).decode()
    data_uri = f"data:image/jpeg;base64,{b64}"
    root = settings.relay_base_url.rstrip("/")
    if root.endswith("/v1"):
        root_no_v1 = root[:-3].rstrip("/")
    else:
        root_no_v1 = root
        root = root + "/v1"
    key = settings.relay_api_key
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # (描述, 方法, url, json)
    candidates = [
        ("A v1/videos/generations data-uri",
         "POST", f"{root}/videos/generations",
         {"model": model, "prompt": PROMPT, "image": data_uri}),
        ("B v1/videos/generations image_url",
         "POST", f"{root}/videos/generations",
         {"model": model, "prompt": PROMPT, "image_url": data_uri}),
        ("C kling/v1/videos/image2video (native)",
         "POST", f"{root_no_v1}/kling/v1/videos/image2video",
         {"model_name": model, "prompt": PROMPT, "image": b64, "mode": "std", "duration": "5"}),
        ("D v1/video/generations",
         "POST", f"{root}/video/generations",
         {"model": model, "prompt": PROMPT, "image": data_uri}),
        ("E v1/images/edits style (multipart skip) - json videos",
         "POST", f"{root}/videos",
         {"model": model, "prompt": PROMPT, "image": data_uri}),
    ]

    for desc, method, url, payload in candidates:
        try:
            r = httpx.request(method, url, json=payload, headers=headers, timeout=40)
            print(f"[{desc}]\n  {method} {url}\n  HTTP {r.status_code}: {r.text[:300]}\n")
        except Exception as e:  # noqa: BLE001
            print(f"[{desc}]\n  {method} {url}\n  ERR {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
