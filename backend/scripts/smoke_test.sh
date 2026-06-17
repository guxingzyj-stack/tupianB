#!/usr/bin/env bash
# 端到端冒烟测试 (任务 2.6): 上传图 -> 三选项 -> 各选项修图 -> 下载结果。
# 依赖: bash + curl + jq + base64
# 用法:
#   APP_TOKEN=xxx ./scripts/smoke_test.sh [图片路径]
#   默认图片: test_images/cheetah.jpg
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
APP_TOKEN="${APP_TOKEN:-}"
DEVICE="${DEVICE:-smoke-device}"
IMG="${1:-test_images/cheetah.jpg}"
OUT_DIR="smoke_output"

HDR=(-H "Content-Type: application/json")
if [ -n "$APP_TOKEN" ]; then HDR+=(-H "X-App-Token: $APP_TOKEN"); fi

command -v jq   >/dev/null || { echo "需要 jq";   exit 1; }
command -v curl >/dev/null || { echo "需要 curl"; exit 1; }

mkdir -p "$OUT_DIR"

echo "==> 1. 检查后端 health"
HEALTH=$(curl -fsS "$BASE_URL/api/health")
echo "    $HEALTH"
echo "$HEALTH" | grep -q '"status":"ok"' || { echo "[FAIL] health 不正常"; exit 1; }

[ -f "$IMG" ] || { echo "[FAIL] 找不到测试图: $IMG (请放一张 test_images/cheetah.jpg)"; exit 1; }

echo "==> 2. POST /api/analyze ($IMG)"
IMG_B64=$(base64 "$IMG" | tr -d '\n')
REQ=$(jq -n --arg d "$DEVICE" --arg img "$IMG_B64" '{device_id:$d, image:$img}')
START=$(date +%s)
RESP=$(curl -fsS "${HDR[@]}" -d "$REQ" "$BASE_URL/api/analyze")
echo "$RESP" | jq '{job_id, base_image_url, names: [.analysis.options[].name]}'

JOB_ID=$(echo "$RESP" | jq -r '.job_id')
BASE_IMG_URL=$(echo "$RESP" | jq -r '.base_image_url')
[ "$JOB_ID" != "null" ] || { echo "[FAIL] 没拿到 job_id"; exit 1; }

# 校验三选项 name 都 <= 5 字 (jq length = Unicode 码点数, 中文每字算 1)
echo "$RESP" | jq -e '[.analysis.options[].name | length] | all(. <= 5)' >/dev/null \
  || { echo "[FAIL] 有选项 name 超过 5 字"; exit 1; }
echo "    [ok] 三选项 name 长度校验通过"

echo "==> 3. 下载基础修复版"
curl -fsS "$BASE_IMG_URL" -o "$OUT_DIR/base.jpg"
echo "    saved $OUT_DIR/base.jpg"

echo "==> 4-5. POST /api/enhance 三个选项"
for i in 0 1 2; do
  ER=$(curl -fsS "${HDR[@]}" -d "{\"job_id\":\"$JOB_ID\",\"option_index\":$i}" "$BASE_URL/api/enhance")
  URL=$(echo "$ER" | jq -r '.result_image_url')
  NAME=$(echo "$ER" | jq -r '.option_name')
  MS=$(echo "$ER" | jq -r '.processing_ms')
  curl -fsS "$URL" -o "$OUT_DIR/option_$((i + 1)).jpg"
  echo "    option $i [$NAME] ${MS}ms -> $OUT_DIR/option_$((i + 1)).jpg"
done

END=$(date +%s)
echo
echo "================ 冒烟测试通过 ================"
echo "总耗时:   $((END - START))s"
echo "输出目录: $OUT_DIR/"
echo "三选项:   $(echo "$RESP" | jq -r '[.analysis.options[].name] | join(" / ")')"
ls -l "$OUT_DIR"
