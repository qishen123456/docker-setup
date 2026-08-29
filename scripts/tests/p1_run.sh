#!/usr/bin/env bash
# P1 压测宿主侧包装：从仓库直跑（fixtures 是 git 唯一事实源，容器内代码打进镜像不可见，
# 所以第 0 步自动 docker cp runner + cases 进容器，跑完取回结果）。
#
# 用法：
#   scripts/tests/p1_run.sh <cases.json（仓库内路径）> <结果输出名.jsonl> [起始] [数量]
# 例：
#   scripts/tests/p1_run.sh backend/tests/fixtures/p1_baseline/p1_negative_cases.json negative_r1.jsonl
#
# 结果落回 <cases 所在目录>/<结果输出名>，同时容器内留副本 /app/config/。
set -euo pipefail

CASES_HOST="$1"
OUT_NAME="${2:-p1_result.jsonl}"
START="${3:-0}"
COUNT="${4:-9999}"
OUT_DIR="$(dirname "$CASES_HOST")"

export MSYS_NO_PATHCONV=1
docker cp scripts/tests/p1_http_runner.py smartask-backend:/app/backend/_p1_http_runner.py
docker cp scripts/tests/p1_gate_check.py smartask-backend:/app/backend/_p1_gate_check.py
docker cp "$CASES_HOST" "smartask-backend:/app/config/_p1_cases_tmp.json"
docker exec smartask-backend python /app/backend/_p1_http_runner.py \
    "/app/config/_p1_cases_tmp.json" "/app/config/_p1_out_tmp.jsonl" "$START" "$COUNT"
docker cp "smartask-backend:/app/config/_p1_out_tmp.jsonl" "$OUT_DIR/$OUT_NAME"
docker exec smartask-backend rm -f /app/config/_p1_cases_tmp.json /app/config/_p1_out_tmp.jsonl
echo "结果已落回 $OUT_DIR/$OUT_NAME"
