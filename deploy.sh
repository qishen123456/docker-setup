#!/usr/bin/env bash
set -euo pipefail

NO_BUILD=0
RUN_TESTS=0
RUN_STREAM_TESTS=0
FORCE_IMPORT=0
FORCE_CONFIG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --run-tests)
      RUN_TESTS=1
      shift
      ;;
    --run-stream-tests)
      RUN_STREAM_TESTS=1
      RUN_TESTS=1
      shift
      ;;
    --force-import)
      FORCE_IMPORT=1
      shift
      ;;
    --force-config)
      FORCE_CONFIG=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk Linux 一键部署脚本

用法：
  bash deploy.sh
  bash deploy.sh --run-tests
  bash deploy.sh --no-build

参数：
  --no-build           不重新构建镜像，只启动容器。
  --run-tests          启动后运行接口测试。
  --run-stream-tests   额外运行流式问数测试，需要真实 AI Key。
  --force-import       强制重新导入元数据/业务数据，谨慎使用。
  --force-config       强制覆盖 config JSON，谨慎使用。
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

info() { echo ""; echo "==> $*"; }
ok() { echo "  [OK] $*"; }
warn() { echo "  [WARN] $*"; }
fail() { echo "  [ERR] $*" >&2; exit 1; }

read_env() {
  local key="$1"
  local default="${2:-}"
  if [[ ! -f .env ]]; then
    echo "$default"
    return
  fi
  local value
  value="$(grep -E "^${key}=" .env | tail -n1 | cut -d= -f2- || true)"
  echo "${value:-$default}"
}

require_env() {
  local key="$1"
  local value
  value="$(read_env "$key" "")"
  [[ -n "$value" ]] || fail ".env 缺少必填项: $key"
  if [[ "$value" =~ please|请填写|AI_API_KEY|SECRET_KEY ]]; then
    fail ".env 中 $key 仍是占位符，请先填写真实值"
  fi
}

info "1/6 检查 Docker"
command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
docker info >/dev/null 2>&1 || fail "Docker 未启动或当前用户无权限访问 Docker"
docker compose version >/dev/null 2>&1 || fail "未找到 Docker Compose Plugin"
ok "Docker 可用"

info "2/6 检查 .env"
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    warn "已从 .env.example 复制 .env。请填写真实配置后重新执行 bash deploy.sh"
    exit 1
  fi
  fail "缺少 .env，且未找到 .env.example"
fi
require_env "SMARTASK_SECRET_KEY"
require_env "SMARTASK_AI_API_KEY"
require_env "SMARTASK_ADMIN_PASSWORD"
ok ".env 已存在且关键项不是占位符"

mkdir -p config backups backend/logs backend/imports

FRONTEND_PORT="$(read_env SMARTASK_FRONTEND_PORT 8080)"
BACKEND_PORT="$(read_env SMARTASK_BACKEND_PORT 5002)"
PG_PORT="$(read_env SMARTASK_DOCKER_PG_PORT 5433)"

if ss -lnt 2>/dev/null | grep -q ":${FRONTEND_PORT} "; then
  warn "前端端口 $FRONTEND_PORT 已监听。如果不是旧 SmartAsk 容器，请调整 .env 端口。"
fi
if ss -lnt 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
  warn "后端端口 $BACKEND_PORT 已监听。如果不是旧 SmartAsk 容器，请调整 .env 端口。"
fi
if ss -lnt 2>/dev/null | grep -q ":${PG_PORT} "; then
  warn "PostgreSQL 映射端口 $PG_PORT 已监听。如果不是旧 SmartAsk 容器，请调整 .env 端口。"
fi

if [[ "$FORCE_IMPORT" -eq 1 ]]; then
  export SMARTASK_BOOTSTRAP_FORCE_IMPORT=1
  warn "--force-import 已开启，将强制重新导入元数据/业务数据"
fi
if [[ "$FORCE_CONFIG" -eq 1 ]]; then
  export SMARTASK_BOOTSTRAP_FORCE_CONFIG=1
  warn "--force-config 已开启，将覆盖 config JSON"
fi

info "3/6 校验 docker compose"
docker compose config >/dev/null
ok "docker-compose.yml 有效"

info "4/6 构建并启动容器"
if [[ "$NO_BUILD" -eq 1 ]]; then
  docker compose up -d
else
  docker compose up -d --build
fi

info "5/6 等待后端健康检查"
READY=0
for _ in $(seq 1 120); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

docker compose ps
[[ "$READY" -eq 1 ]] || fail "后端健康检查失败。请执行: bash doctor.sh"

info "6/6 部署完成"
ok "后端健康检查通过"
echo "  Frontend: http://服务器IP:${FRONTEND_PORT}"
echo "  Backend:  http://服务器IP:${BACKEND_PORT}/api/health"
echo "  Postgres: 服务器IP:${PG_PORT} (容器内 5432)"

if [[ "$RUN_TESTS" -eq 1 ]]; then
  info "运行集成测试"
  STREAM_ARGS=()
  if [[ "$RUN_STREAM_TESTS" -eq 1 ]]; then
    STREAM_ARGS+=(--with-stream)
  fi
  docker compose exec -T backend python -m pip install --quiet --disable-pip-version-check requests || true
  docker compose exec -T backend python /app/scripts/integration_test.py \
    --base-url "http://localhost:5002" \
    --frontend-url "http://frontend" \
    --no-wait "${STREAM_ARGS[@]}"
fi

echo ""
echo "常用命令："
echo "  日志：bash doctor.sh 或 docker compose logs -f backend"
echo "  更新：bash update.sh"
echo "  备份：bash backup.sh"
echo "  停止：docker compose stop"
