"""探测 relay 的 /v1/images/edits 调用格式 (任务 4.2 前置)。
用 qwen-image-edit 真修一张图, 打印响应结构, 存下结果。
用法: python scripts/image_edit_probe.py [图片] [模型]
"""

import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402

PROMPT = (
    "修复这张老照片：去除划痕和折痕，修正褪色和偏黄，提升清晰度，"
    "让人物面部自然清晰。保持原貌，不要改变人物身份，不要新增内容。"
)


def main() -> None:
    img_path = Path(sys.argv[1] if len(sys.argv) > 1 else "validation/scenes8/images/old_photo.jpg")
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen-image-edit-2509"
    if not img_path.exists():
        print(f"[缺] 找不到图: {img_path}")
        sys.exit(1)

    endpoint = settings.relay_base_url.rstrip("/") + "/images/edits"
    print(f"endpoint = {endpoint}\nmodel    = {model}\nimage    = {img_path}")

    files = {"image": (img_path.name, img_path.read_bytes(), "image/jpeg")}
    data = {"model": model, "prompt": PROMPT, "n": "1"}
    headers = {"Authorization": f"Bearer {settings.relay_api_key}"}

    t0 = time.perf_counter()
    try:
        resp = httpx.post(endpoint, files=files, data=data, headers=headers, timeout=180)
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {type(e).__name__}: {e}")
        sys.exit(1)
    ms = int((time.perf_counter() - t0) * 1000)
    print(f"HTTP {resp.status_code}  {ms}ms")

    if resp.status_code != 200:
        print("body:", resp.text[:600])
        sys.exit(1)

    body = resp.json()
    print("顶层 keys:", list(body.keys()) if isinstance(body, dict) else type(body))
    items = body.get("data", []) if isinstance(body, dict) else []
    if items:
        print("data[0] keys:", list(items[0].keys()))
        out = Path("validation/edit_out"); out.mkdir(parents=True, exist_ok=True)
        first = items[0]
        if first.get("b64_json"):
            (out / "restored.jpg").write_bytes(base64.b64decode(first["b64_json"]))
            print("saved (b64) ->", out / "restored.jpg")
        elif first.get("url"):
            print("result url:", first["url"])
            try:
                img = httpx.get(first["url"], timeout=60).content
                (out / "restored.jpg").write_bytes(img)
                print("saved (url) ->", out / "restored.jpg")
            except Exception as e:  # noqa: BLE001
                print("下载结果图失败:", e)
    else:
        print("body 预览:", str(body)[:600])


if __name__ == "__main__":
    main()
