#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

FAIL=0

section() {
  echo ""
  echo "==> $*"
}

mark_fail() {
  echo "  [FAIL] $*" >&2
  FAIL=1
}

mark_ok() {
  echo "  [OK] $*"
}

section "检查 Git 新源码是否被遗漏"
UNTRACKED_IMPORTANT="$(git ls-files --others --exclude-standard \
  frontend/src \
  backend/*.py \
  backend/controllers \
  scripts \
  docs \
  '*.sh' \
  2>/dev/null || true)"
if [[ -n "$UNTRACKED_IMPORTANT" ]]; then
  echo "$UNTRACKED_IMPORTANT"
  mark_fail "存在未跟踪的重要源码/脚本/文档，请确认是否需要 git add"
else
  mark_ok "没有未跟踪的重要源码"
fi

section "检查 .gitignore 是否误伤前端/后端源码"
IGNORED_SOURCE=""
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  if git check-ignore -q "$file"; then
    IGNORED_SOURCE+="$file"$'\n'
  fi
done < <(
  {
    find frontend/src -type f \( -name '*.vue' -o -name '*.js' -o -name '*.ts' -o -name '*.css' \) 2>/dev/null
    find backend -maxdepth 1 -type f -name '*.py' 2>/dev/null
    find backend/controllers -type f -name '*.py' 2>/dev/null
    find scripts -type f -name '*.py' 2>/dev/null
  } | sort
)
if [[ -n "$IGNORED_SOURCE" ]]; then
  echo "$IGNORED_SOURCE"
  mark_fail "发现源码被 .gitignore 忽略"
else
  mark_ok "没有发现源码被 .gitignore 误伤"
fi

section "检查 Linux shell 脚本 LF 行尾"
CRLF_FILES=""
for file in *.sh; do
  [[ -f "$file" ]] || continue
  if grep -q $'\r' "$file"; then
    CRLF_FILES+="$file"$'\n'
  fi
done
if [[ -n "$CRLF_FILES" ]]; then
  echo "$CRLF_FILES"
  mark_fail "发现 .sh 文件包含 CRLF 行尾"
else
  mark_ok ".sh 文件均为 LF 行尾"
fi

section "检查 docker compose 配置"
if docker compose config >/tmp/smartask_compose_check.txt 2>&1; then
  mark_ok "docker compose config 通过"
else
  cat /tmp/smartask_compose_check.txt
  mark_fail "docker compose config 失败"
fi

section "前端构建检查"
if (cd frontend && npm run build); then
  mark_ok "frontend npm run build 通过"
else
  mark_fail "frontend npm run build 失败"
fi

section "后端关键文件语法检查"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  PYTHON_BIN=""
fi

if [[ -n "$PYTHON_BIN" ]]; then
  if "$PYTHON_BIN" -B - <<'PY'
import ast
from pathlib import Path

files = []
for root in (Path("backend"), Path("scripts")):
    if root.exists():
        files.extend(sorted(root.rglob("*.py")))

for file in files:
    ast.parse(Path(file).read_text(encoding="utf-8-sig"), filename=str(file))
print(f"PY_AST_OK {len(files)} files")
PY
  then
    mark_ok "后端与脚本 AST 通过"
  else
    mark_fail "后端与脚本 AST 失败"
  fi
else
  mark_fail "未找到 python/python3，无法检查后端语法"
fi

section "报告场景与模板契约烟雾测试"
if [[ -n "$PYTHON_BIN" ]]; then
  if "$PYTHON_BIN" -B - <<'PY'
import sys

sys.path.insert(0, "backend")

from report_contract_health import validate_report_contract
from report_scene_registry import detect_report_scene

scene = detect_report_scene("东部和西部业绩对比", None, 2)
assert scene["key"] == "comparative", scene
assert scene["layout"] == "comparison", scene

config = {
    "nameColumn": "节点名称",
    "parentColumn": "上级名称",
    "levelColumn": "层级",
    "trackColumn": "条线",
    "metrics": [
        {"key": "task", "label": "任务", "column": "任务金额", "format": "amount"},
        {"key": "actual", "label": "开单", "column": "开单金额", "format": "amount"},
        {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
    ],
    "analysisDimensions": [{"key": "level", "column": "层级"}],
    "signalRules": [{"key": "rate", "dangerBelow": 0.1, "goodAbove": 0.2}],
    "sqlOutputContract": {
        "requiredColumns": ["节点名称", "层级", "任务金额", "开单金额", "达成率"]
    },
}
columns = ["节点名称", "上级名称", "层级", "条线", "任务金额", "开单金额", "达成率"]
contract = validate_report_contract(config, columns, scene)
assert contract["used"] is True, contract
assert contract["score"] >= 85, contract
print(f"REPORT_CONTRACT_OK scene={scene['key']} score={contract['score']}")
PY
  then
    mark_ok "报告场景与模板契约通过"
  else
    mark_fail "报告场景与模板契约失败"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "发布检查通过。"
else
  echo "发布检查失败，请先处理上述问题。" >&2
  exit 1
fi
