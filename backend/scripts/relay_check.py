"""真实 relay 连通性 + 看图分析验证。

用法 (在 backend/ 下, 需先在 .env 配好 RELAY_*):
  python scripts/relay_check.py [图片路径] [模型名]

默认图 test_images/cheetah.jpg, 默认模型取 .env 的 RELAY_MODEL。
打印: 端点、模型、耗时、schema 是否通过、Claude 返回的原始 JSON。
"""

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.base import AdapterFailure  # noqa: E402
from app.adapters.claude_adapter import make_claude_adapter  # noqa: E402
from app.config import settings  # noqa: E402
from app.prompts.analyze_prompt import PROMPT_VERSION, SCHEMA_VALIDATOR  # noqa: E402

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


async def run(image_path: str, model: str | None) -> None:
    raw = Path(image_path).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = _MIME.get(Path(image_path).suffix.lower(), "image/jpeg")

    adapter = make_claude_adapter()
    if model:
        adapter.model = model

    print(f"endpoint = {settings.chat_completions_url}")
    print(f"model    = {adapter.model}   prompt = {PROMPT_VERSION}")
    print(f"image    = {image_path} ({len(raw)} bytes, {mime})")
    print("-" * 60)

    t0 = time.perf_counter()
    try:
        result = await adapter.analyze(b64, mime=mime)
    except AdapterFailure as exc:
        print(f"[FAIL] AdapterFailure: {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        return
    ms = int((time.perf_counter() - t0) * 1000)

    ok = SCHEMA_VALIDATOR(result)
    print(f"[OK] {ms}ms   schema_valid = {ok}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else "test_images/cheetah.jpg"
    mdl = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(run(img, mdl))
