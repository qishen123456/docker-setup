#!/usr/bin/env bash
set -euo pipefail

NO_BUILD=0
NO_PULL=0
SKIP_BACKUP=0
RUN_TESTS=0
RUN_STREAM_TESTS=0
BRANCH="docker-setup"
SKIP_VERIFY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --no-pull)
      NO_PULL=1
      shift
      ;;
    --skip-backup)
      SKIP_BACKUP=1
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
    --skip-verify)
      SKIP_VERIFY=1
      shift
      ;;
    --branch)
      BRANCH="${2:-docker-setup}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk Linux 更新脚本

用法：
  bash update.sh
  bash update.sh --run-tests
  bash update.sh --no-pull

参数：
  --branch NAME        指定更新分支，默认 docker-setup。
  --no-build          不重新构建镜像，只重启容器。
  --no-pull           不拉取 Git，仅用当前代码重建。
  --skip-backup       跳过更新前备份，不建议生产环境使用。
  --run-tests         更新后运行接口测试。
  --run-stream-tests  额外运行流式问数测试，需要真实 AI Key。
  --skip-verify       跳过容器内自检，仅做健康检查。
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

command -v git >/dev/null 2>&1 || fail "未找到 git 命令"
command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
docker info >/dev/null 2>&1 || fail "Docker 未启动或当前用户无权限访问 Docker"
docker compose version >/dev/null 2>&1 || fail "未找到 Docker Compose Plugin"
[[ -f .env ]] || fail "缺少 .env，请先放好生产配置"

if [[ "$SKIP_BACKUP" -eq 0 ]]; then
  info "更新前备份"
  bash "$SCRIPT_DIR/backup.sh" || fail "备份失败，已停止更新以保护生产数据"
else
  warn "已跳过备份。生产环境不建议使用 --skip-backup"
fi

if [[ "$NO_PULL" -eq 0 ]]; then
  info "拉取最新代码"
  git fetch --all
  git checkout "$BRANCH"
  git pull --ff-only
else
  warn "已跳过 Git 拉取"
fi

info "校验 docker compose"
docker compose config >/dev/null

info "重建并启动容器"
if [[ "$NO_BUILD" -eq 1 ]]; then
  docker compose up -d
else
  docker compose up -d --build
fi
echo "  [OK] 后端启动时会自动应用 backend/migrations，包括报告阈值与模板配置更新"

BACKEND_PORT="$(read_env SMARTASK_BACKEND_PORT 5002)"
FRONTEND_PORT="$(read_env SMARTASK_FRONTEND_PORT 8080)"

info "等待后端健康检查"
READY=0
for _ in $(seq 1 90); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

docker compose ps
[[ "$READY" -eq 1 ]] || fail "后端健康检查失败。请执行: bash doctor.sh"

if [[ "$SKIP_VERIFY" -eq 0 ]]; then
  info "运行容器内自检"
  docker compose exec -T backend python /app/scripts/verify_deployment.py || fail "容器内自检失败。请执行: bash doctor.sh"
else
  warn "已跳过容器内自检: --skip-verify"
fi

echo ""
echo "[OK] 更新完成。页面如仍旧，请浏览器 Ctrl+F5。"
echo "用户访问地址: http://服务器IP:${FRONTEND_PORT}"

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
