"""8 类场景 × 多模型 看图三选项 真实评测。

对每个场景下载/准备一张真实照片, 用锁定版 prompt (analyze_prompt.py) 分别调
每个模型 (经 relay), 记录: schema 是否通过、各项 §5.3 检查、耗时、token、
以及模型实际给老人的 scene/problems/三选项原文。

产出:
  validation/scenes8/images/*.jpg   各场景测试图
  scenes8_results.json              完整结果 (backend/ 下)
  控制台打印判分表 + 逐场景三选项

用法 (在 backend/ 下, 需先在 .env 配好 RELAY_*):
  python scripts/scenes8_eval.py
  python scripts/scenes8_eval.py --probe        # 只测 loremflickr 连通性
  python scripts/scenes8_eval.py --models claude-sonnet-4-6
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import shutil
import sys
import time
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.base import AdapterFailure, parse_json_loose  # noqa: E402
from app.config import settings  # noqa: E402
from app.prompts.analyze_prompt import (  # noqa: E402
    PROMPT_VERSION,
    SCHEMA_VALIDATOR,
    SYSTEM_PROMPT,
    USER_PROMPT,
    _TECH_WORDS,
)

DEFAULT_MODELS = ["claude-sonnet-4-6", "gpt-4.1"]

OUT_DIR = Path("validation/scenes8")
IMG_DIR = OUT_DIR / "images"
RESULTS_PATH = Path("scenes8_results.json")
MAX_EDGE = 1536  # 发送给模型前压到的长边

# 8 类场景。tags 走 loremflickr; old_photo 下载后做旧化处理 (age=True)。
SCENES = [
    {"key": "wildlife", "label": "野生动物", "tags": "leopard,wildlife,safari", "age": False},
    {"key": "landscape", "label": "风景", "tags": "landscape,mountain,lake", "age": False},
    {"key": "backlit_portrait", "label": "人像逆光", "tags": "portrait,sunset", "age": False},
    {"key": "group_photo", "label": "多人合影", "tags": "family,group,people", "age": False},
    {"key": "night", "label": "暗光夜景", "tags": "night,city,street", "age": False},
    {"key": "old_photo", "label": "老照片", "tags": "family,portrait,vintage", "age": True},
    {"key": "food", "label": "美食", "tags": "food,meal,dish", "age": False},
    {"key": "kids", "label": "孩子日常", "tags": "child,kid,playing", "age": False},
]

# 有本地真实图的场景, 优先用本地 (不依赖 loremflickr)。野生动物用猎豹图。
LOCAL_SOURCES = {
    "wildlife": Path("test_images/cheetah.jpg"),
}


# --------------------------------------------------------------------------- #
# 图片准备
# --------------------------------------------------------------------------- #
def loremflickr_url(tags: str, w: int = 1024, h: int = 768, lock: int = 1) -> str:
    return f"https://loremflickr.com/{w}/{h}/{tags}?lock={lock}"


def _valid_image(path: Path) -> bool:
    try:
        Image.open(path).verify()
        return path.stat().st_size > 2000
    except Exception:  # noqa: BLE001
        return False


def download_image(url: str, dst: Path, retries: int = 4) -> bool:
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(follow_redirects=True, timeout=25.0) as c:
                r = c.get(url)
            r.raise_for_status()
            data = r.content
            Image.open(io.BytesIO(data)).verify()  # 校验是有效图
            if len(data) < 2000:
                raise ValueError("图太小, 可能是占位图")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"    下载失败 ({attempt}/{retries}): {exc}")
            if attempt < retries:
                time.sleep(1.5 * attempt)  # 退避, 缓解 loremflickr 限流/500
    return False


def age_photo(src: Path, dst: Path) -> None:
    """把一张正常照片做成"老照片翻拍"观感: 去色 + 棕褐调 + 降对比 + 颗粒。"""
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    gray = ImageOps.grayscale(img)
    sepia = ImageOps.colorize(gray, black=(38, 26, 12), white=(252, 240, 206)).convert("RGB")
    sepia = ImageEnhance.Contrast(sepia).enhance(0.82)
    arr = np.asarray(sepia).astype(np.int16)
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 11, arr.shape).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype("uint8")
    out = Image.fromarray(arr, "RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, "JPEG", quality=88)


def downscale_to_b64(path: Path, max_edge: int = MAX_EDGE, quality: int = 88) -> tuple[str, int]:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = img.size
    scale = min(1.0, max_edge / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    raw = buf.getvalue()
    return base64.b64encode(raw).decode("ascii"), len(raw)


def _obtain_raw(sc: dict, dst: Path, lock: int) -> bool:
    """把一张原始图弄到 dst: 本地源优先, 否则 loremflickr (多标签->单标签兜底)。"""
    key = sc["key"]
    local = LOCAL_SOURCES.get(key)
    if local and local.exists() and _valid_image(local):
        shutil.copy(local, dst)
        print(f"    -> 用本地图 {local}")
        return True
    if download_image(loremflickr_url(sc["tags"], lock=lock), dst):
        return True
    # 单标签兜底 (多标签更容易 500)
    first_tag = sc["tags"].split(",")[0]
    print(f"    多标签失败, 试单标签 '{first_tag}' ...")
    return download_image(loremflickr_url(first_tag, lock=lock + 500), dst)


def prepare_images(lock_base: int = 21) -> dict[str, Path | None]:
    """下载/准备 8 张图。已存在的有效图直接复用 (缓存)。返回 {scene_key: path or None}。"""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path | None] = {}
    for i, sc in enumerate(SCENES):
        key = sc["key"]
        final = IMG_DIR / f"{key}.jpg"
        if _valid_image(final):
            print(f"  [{sc['label']}] 已缓存, 跳过下载")
            paths[key] = final
            continue
        print(f"  [{sc['label']}] 准备图 (tags={sc['tags']}) ...")
        if sc["age"]:
            raw = IMG_DIR / f"{key}_raw.jpg"
            if _obtain_raw(sc, raw, lock_base + i):
                age_photo(raw, final)
                print("    -> 已旧化处理")
                paths[key] = final
            else:
                paths[key] = None
        else:
            paths[key] = final if _obtain_raw(sc, final, lock_base + i) else None
    return paths


# --------------------------------------------------------------------------- #
# 模型调用 + 评分
# --------------------------------------------------------------------------- #
async def call_model(client: httpx.AsyncClient, model: str, b64: str, mime: str = "image/jpeg") -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    headers = {"Authorization": f"Bearer {settings.relay_api_key}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    resp = await client.post(settings.chat_completions_url, json=payload, headers=headers)
    ms = int((time.perf_counter() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    parsed = parse_json_loose(content)
    return {"parsed": parsed, "raw": content, "usage": usage, "latency_ms": ms}


def score(parsed: dict) -> dict:
    opts = parsed.get("options", []) if isinstance(parsed, dict) else []
    names = [o.get("name", "") for o in opts if isinstance(o, dict)]
    tech_hits = {n: [t for t in _TECH_WORDS if t in n] for n in names if any(t in n for t in _TECH_WORDS)}
    return {
        "schema_valid": SCHEMA_VALIDATOR(parsed),
        "n_options": len(opts),
        "names": names,
        "max_name_len": max((len(n) for n in names), default=0),
        "tech_word_hits": tech_hits,
        "distinct": len(set(names)) == len(names) and len(names) > 0,
    }


async def eval_all(
    models: list[str],
    paths: dict[str, Path | None],
    existing: dict[tuple[str, str], dict] | None = None,
) -> dict:
    existing = existing or {}
    results: dict = {
        "meta": {
            "prompt_version": PROMPT_VERSION,
            "endpoint": settings.chat_completions_url,
            "models": models,
            "max_edge": MAX_EDGE,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "scenes": [],
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        for sc in SCENES:
            key = sc["key"]
            path = paths.get(key)
            scene_rec: dict = {"key": key, "label": sc["label"], "image": str(path) if path else None, "models": {}}
            if path is None:
                scene_rec["skipped"] = "download_failed"
                print(f"[跳过] {sc['label']}: 图片下载失败")
                results["scenes"].append(scene_rec)
                continue
            b64 = None
            nbytes = 0
            for model in models:
                # 复用已有成功结果, 不重复调用 (省钱)
                if (key, model) in existing:
                    scene_rec["models"][model] = existing[(key, model)]
                    print(f"[复用] {sc['label']} × {model} (已有结果)")
                    continue
                if b64 is None:
                    b64, nbytes = downscale_to_b64(path)
                print(f"[调用] {sc['label']} × {model} (img {nbytes//1024}KB) ...", flush=True)
                rec: dict = {}
                try:
                    out = await call_model(client, model, b64)
                    parsed = out["parsed"]
                    sc_score = score(parsed)
                    rec = {
                        "ok": True,
                        "latency_ms": out["latency_ms"],
                        "usage": out["usage"],
                        "scene": parsed.get("scene"),
                        "subject": parsed.get("subject"),
                        "problems": parsed.get("problems"),
                        "options": parsed.get("options"),
                        **sc_score,
                    }
                    flag = "PASS" if sc_score["schema_valid"] else "FAIL"
                    print(
                        f"    -> {flag} {out['latency_ms']}ms "
                        f"tok={out['usage'].get('total_tokens')} "
                        f"names={sc_score['names']}"
                    )
                except (AdapterFailure, httpx.HTTPError) as exc:
                    rec = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    print(f"    -> ERROR {rec['error']}")
                except Exception as exc:  # noqa: BLE001
                    rec = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    print(f"    -> ERROR {rec['error']}")
                scene_rec["models"][model] = rec
            results["scenes"].append(scene_rec)
    return results


def print_summary(results: dict, models: list[str]) -> None:
    print("\n" + "=" * 64)
    print(f"判分汇总 (prompt {results['meta']['prompt_version']})")
    print("=" * 64)
    for model in models:
        passed = total = lat = tok = n_tok = 0
        for sc in results["scenes"]:
            rec = sc.get("models", {}).get(model)
            if not rec:
                continue
            total += 1
            if rec.get("ok") and rec.get("schema_valid"):
                passed += 1
            if rec.get("ok"):
                lat += rec.get("latency_ms", 0)
                tt = (rec.get("usage") or {}).get("total_tokens")
                if tt:
                    tok += tt
                    n_tok += 1
        avg_lat = f"{lat/total/1000:.1f}s" if total else "-"
        avg_tok = f"{tok/n_tok:.0f}" if n_tok else "-"
        print(f"  {model:24} 通过 {passed}/{total}   平均 {avg_lat}   平均token {avg_tok}")

    print("\n逐场景三选项 (老人实际看到的):")
    for sc in results["scenes"]:
        print(f"\n● {sc['label']}" + (f"  [{sc['skipped']}]" if sc.get("skipped") else ""))
        for model in models:
            rec = sc.get("models", {}).get(model)
            if not rec or not rec.get("ok"):
                if rec:
                    print(f"   {model:22} ERROR: {rec.get('error')}")
                continue
            names = " / ".join(rec.get("names", []))
            flag = "✓" if rec.get("schema_valid") else "✗"
            print(f"   {model:22} {flag} {names}   (scene: {rec.get('scene')})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--probe", action="store_true", help="只测 loremflickr 连通性")
    ap.add_argument("--resume", action="store_true", help="复用 scenes8_results.json 里已成功的结果, 只补缺失的")
    args = ap.parse_args()

    if args.probe:
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        ok = download_image(loremflickr_url("leopard,wildlife", lock=1), IMG_DIR / "_probe.jpg")
        print("loremflickr 连通:" + ("OK" if ok else "失败"))
        sys.exit(0 if ok else 1)

    print("== 准备 8 张测试图 ==")
    paths = prepare_images()
    n_ok = sum(1 for p in paths.values() if p)
    print(f"图片就绪: {n_ok}/8")
    if n_ok == 0:
        print("[中止] 一张图都没下到, 检查网络/loremflickr。")
        sys.exit(1)

    existing: dict[tuple[str, str], dict] = {}
    if args.resume and RESULTS_PATH.exists():
        prev = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        for sc in prev.get("scenes", []):
            for model, rec in sc.get("models", {}).items():
                if rec.get("ok"):
                    existing[(sc["key"], model)] = rec
        print(f"resume: 复用 {len(existing)} 条已有结果")

    print(f"\n== 评测 {args.models} ==")
    results = asyncio.run(eval_all(args.models, paths, existing))

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(results, args.models)
    print(f"\n完整结果已存: {RESULTS_PATH.resolve()}")


if __name__ == "__main__":
    main()
