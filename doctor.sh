#!/usr/bin/env bash
set -uo pipefail

OUTPUT_DIR="diagnostics"
WITH_BUILD_LOG=0
TAIL_LINES=500

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="${2:-diagnostics}"
      shift 2
      ;;
    --with-build-log)
      WITH_BUILD_LOG=1
      shift
      ;;
    --tail)
      TAIL_LINES="${2:-500}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk Linux 诊断包生成器

用法：
  bash doctor.sh
  bash doctor.sh --with-build-log
  bash doctor.sh --output-dir diagnostics --tail 800

说明：
  默认只采集状态和日志，不重建、不删除数据。
  --with-build-log 会额外执行 docker compose build --progress=plain，用于复现构建失败日志。
EOF
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DIAG_ROOT="$SCRIPT_DIR/$OUTPUT_DIR"
DIAG_DIR="$DIAG_ROOT/smartask_linux_diagnose_$TIMESTAMP"
mkdir -p "$DIAG_DIR"

run_cmd() {
  local name="$1"
  shift
  {
    echo "\$ $*"
    "$@"
  } >"$DIAG_DIR/$name.txt" 2>&1 || true
}

run_shell() {
  local name="$1"
  shift
  {
    echo "\$ $*"
    bash -lc "$*"
  } >"$DIAG_DIR/$name.txt" 2>&1 || true
}

redact_file() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "missing $src" >"$dst"
    return
  fi
  sed -E \
    -e '/^[[:space:]]*#/! s/^([^=]*(KEY|SECRET|TOKEN|PASSWORD|APP_SECRET|API_KEY)[^=]*=).*/\1***REDACTED***/I' \
    -e 's/(password|passwd|pwd|secret|token|api[_-]?key)([":= ]+)[^",[:space:]]+/\1\2***REDACTED***/Ig' \
    "$src" >"$dst" 2>/dev/null || cp "$src" "$dst"
}

redact_in_place() {
  local file="$1"
  [[ -f "$file" ]] || return
  local tmp="$file.tmp"
  sed -E \
    -e '/^[[:space:]]*#/! s/^([^=]*(KEY|SECRET|TOKEN|PASSWORD|APP_SECRET|API_KEY)[^=]*=).*/\1***REDACTED***/I' \
    -e 's/(password|passwd|pwd|secret|token|api[_-]?key)([":= ]+)[^",[:space:]]+/\1\2***REDACTED***/Ig' \
    "$file" >"$tmp" 2>/dev/null && mv "$tmp" "$file"
}

echo "SmartAsk Linux 诊断包生成器"
echo "项目目录: $SCRIPT_DIR"
echo "输出目录: $DIAG_DIR"

{
  echo "generated_at=$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "project_root=$SCRIPT_DIR"
  echo "with_build_log=$WITH_BUILD_LOG"
  echo "tail_lines=$TAIL_LINES"
} >"$DIAG_DIR/summary.txt"

echo "==> 收集系统信息"
run_cmd "system_uname" uname -a
run_shell "system_os_release" "cat /etc/os-release || true"
run_cmd "system_date" date
run_cmd "disk_usage" df -h
run_cmd "memory" free -h
run_shell "ports" "FRONTEND_PORT=\$(grep -E '^SMARTASK_FRONTEND_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '\r'); FRONTEND_PORT=\${FRONTEND_PORT:-8080}; BACKEND_PORT=\$(grep -E '^SMARTASK_BACKEND_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '\r'); BACKEND_PORT=\${BACKEND_PORT:-5002}; PG_PORT=\$(grep -E '^SMARTASK_DOCKER_PG_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '\r'); PG_PORT=\${PG_PORT:-5433}; ss -lntp 2>/dev/null | grep -E \":\${FRONTEND_PORT}|:\${BACKEND_PORT}|:5432|:\${PG_PORT}\" || netstat -lntp 2>/dev/null | grep -E \":\${FRONTEND_PORT}|:\${BACKEND_PORT}|:5432|:\${PG_PORT}\" || true"

echo "==> 收集 Git 信息"
run_cmd "git_status" git status --short
run_cmd "git_branch" git branch -vv
run_cmd "git_head" git rev-parse HEAD
run_cmd "git_remote" git remote -v
run_cmd "git_recent_log" git log --oneline -n 12
run_cmd "root_files" find . -maxdepth 2 -type f

echo "==> 收集 Docker 信息"
run_cmd "docker_version" docker version
run_cmd "docker_info" docker info
run_cmd "docker_compose_version" docker compose version
run_cmd "compose_ps" docker compose ps -a
run_cmd "docker_images" docker images
run_cmd "docker_volumes" docker volume ls
run_cmd "docker_networks" docker network ls

echo "==> 收集 compose 配置"
run_cmd "compose_config" docker compose config
redact_in_place "$DIAG_DIR/compose_config.txt"

echo "==> 收集服务日志"
for svc in postgres backend frontend; do
  run_shell "logs_$svc" "docker compose logs --tail=$TAIL_LINES $svc"
  redact_in_place "$DIAG_DIR/logs_$svc.txt"
done

echo "==> 收集容器 inspect"
for container in smartask-postgres smartask-backend smartask-frontend; do
  run_shell "inspect_$container" "docker inspect $container"
  redact_in_place "$DIAG_DIR/inspect_$container.txt"
done

echo "==> 健康检查"
run_shell "health_backend_5002" "curl -fsS --max-time 8 http://127.0.0.1:5002/api/health"
run_shell "health_backend_env_port" "BACKEND_PORT=\$(grep -E '^SMARTASK_BACKEND_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '\r'); BACKEND_PORT=\${BACKEND_PORT:-5002}; curl -fsS --max-time 8 http://127.0.0.1:\$BACKEND_PORT/api/health"
run_shell "health_frontend_8080" "curl -I --max-time 8 http://127.0.0.1:8080"
run_shell "health_frontend_env_port" "FRONTEND_PORT=\$(grep -E '^SMARTASK_FRONTEND_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '\r'); FRONTEND_PORT=\${FRONTEND_PORT:-8080}; curl -I --max-time 8 http://127.0.0.1:\$FRONTEND_PORT"

echo "==> 生成脱敏配置摘要"
redact_file ".env" "$DIAG_DIR/env_redacted.txt"
if [[ -f ".env.example" ]]; then
  cp ".env.example" "$DIAG_DIR/env_example.txt" || true
fi

echo "==> 检查关键文件"
for file in docker-compose.yml frontend/Dockerfile backend/Dockerfile frontend/package.json backend/requirements.txt .dockerignore frontend/.dockerignore; do
  if [[ -f "$file" ]]; then
    mkdir -p "$DIAG_DIR/files/$(dirname "$file")"
    cp "$file" "$DIAG_DIR/files/$file" || true
  fi
done

if [[ "$WITH_BUILD_LOG" -eq 1 ]]; then
  echo "==> 采集 Docker 构建日志（可能耗时）"
  run_shell "compose_build_plain" "docker compose build --progress=plain"
  redact_in_place "$DIAG_DIR/compose_build_plain.txt"
fi

echo "==> 打包诊断结果"
mkdir -p "$DIAG_ROOT"
ARCHIVE_ZIP="$DIAG_DIR.zip"
ARCHIVE_TGZ="$DIAG_DIR.tar.gz"
if command -v zip >/dev/null 2>&1; then
  (cd "$DIAG_ROOT" && zip -qr "$(basename "$ARCHIVE_ZIP")" "$(basename "$DIAG_DIR")") || true
  ARCHIVE="$ARCHIVE_ZIP"
else
  tar -czf "$ARCHIVE_TGZ" -C "$DIAG_ROOT" "$(basename "$DIAG_DIR")" || true
  ARCHIVE="$ARCHIVE_TGZ"
fi

echo ""
echo "诊断包已生成：$ARCHIVE"
echo "请把这个文件发给开发者。诊断包已对 .env、compose 和日志中的常见 Key/Secret/Password 做脱敏处理。"
