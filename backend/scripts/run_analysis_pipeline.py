"""把一份 analysis JSON + 一张图, 跑完整后端逻辑 (校验 + 基础修复 + 三选项修图)。

用途:
  - 没有 relay 时, 用人工/本会话 Claude 产出的 analysis JSON 验证 prompt 与流水线。
  - 有 relay 后, 把真实 Claude 输出 dump 成 JSON, 用同一脚本 A/B 对比效果。

用法 (在 backend/ 下):
  python scripts/run_analysis_pipeline.py --image test_images/cheetah.jpg \
      --analysis validation/cheetah_analysis.json --out validation/out
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.intent_mapper import parse_intent  # noqa: E402
from app.engine.param_enhance import (  # noqa: E402
    apply_operations,
    image_stats,
    make_base_repair,
)
from app.prompts.analyze_prompt import (  # noqa: E402
    PROMPT_VERSION,
    SCHEMA_VALIDATOR,
    _TECH_WORDS,
)

_DASH = "-" * 60


def report_schema(analysis: dict) -> bool:
    print(_DASH)
    print(f"Schema 校验 (PRD §5.3) — prompt {PROMPT_VERSION}")
    opts = analysis.get("options", [])
    ok = SCHEMA_VALIDATOR(analysis)
    print(f"  options 个数: {len(opts)} (要求正好 3)")
    for o in opts:
        name = o.get("name", "")
        hits = [t for t in _TECH_WORDS if t in name]
        flags = []
        if len(name) > 5:
            flags.append("名字超 5 字")
        if hits:
            flags.append(f"含技术词 {hits}")
        status = "OK" if not flags else "✗ " + "; ".join(flags)
        print(f"    - {name!r:14} (len={len(name)})  {status}")
    names = [o.get("name") for o in opts]
    if len(set(names)) < len(names):
        print("    ✗ 名字有重复")
    print(f"  => SCHEMA_VALIDATOR = {ok}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--out", default="validation/out")
    args = ap.parse_args()

    image = Path(args.image)
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(_DASH)
    print("分析结果")
    print(f"  scene   : {analysis.get('scene')}")
    print(f"  subject : {analysis.get('subject')}")
    print(f"  problems: {analysis.get('problems')}")

    report_schema(analysis)

    src = image_stats(image)
    print(_DASH)
    print(f"原图: {image}  亮度={src['mean_luma']:.3f}  饱和={src['mean_sat']:.3f}")

    # 基础修复版
    t0 = time.perf_counter()
    make_base_repair(image, out / "base.jpg")
    bs = image_stats(out / "base.jpg")
    print(
        f"  base.jpg               {int((time.perf_counter()-t0)*1000):>4}ms  "
        f"亮度={bs['mean_luma']:.3f}  饱和={bs['mean_sat']:.3f}"
    )

    # 三选项
    print(_DASH)
    print("三选项修图")
    for i, opt in enumerate(analysis["options"]):
        intent = opt.get("intent", "")
        ops = parse_intent(intent)
        op_desc = ", ".join(f"{o.type}:{o.value}" for o in ops)
        dst = out / f"option_{i + 1}.jpg"
        t0 = time.perf_counter()
        apply_operations(image, ops, dst)
        ms = int((time.perf_counter() - t0) * 1000)
        st = image_stats(dst)
        print(f"  [{opt['name']}]  intent={intent!r}")
        print(f"      -> ops: {op_desc}")
        print(
            f"      -> {dst.name}  {ms:>4}ms  亮度={st['mean_luma']:.3f}  "
            f"饱和={st['mean_sat']:.3f}"
        )

    print(_DASH)
    print(f"完成. 输出目录: {out}/")


if __name__ == "__main__":
    main()
