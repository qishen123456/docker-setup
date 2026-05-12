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
  bash update.sh --pip-index-url https://mirrors.aliyun.com/pypi/simple/

参数：
  --branch NAME        指定更新分支，默认 docker-setup。
  --no-build          不重新构建镜像，只重启容器。
  --no-pull           不拉取 Git，仅用当前代码重建。
  --skip-backup       跳过更新前备份，不建议生产环境使用。
  --run-tests         更新后运行接口测试。
  --run-stream-tests  额外运行流式问数测试，需要真实 AI Key。
  --skip-verify       跳过容器内自检，仅做健康检查。
  --pip-index-url URL  指定 Docker 构建时的 pip 镜像源，默认读取 .env 或使用阿里云源。
  --pip-trusted-host HOST
                     指定 pip trusted-host，默认读取 .env 或 mirrors.aliyun.com。
EOF
      exit 0
      ;;
    --pip-index-url)
      export SMARTASK_PIP_INDEX_URL="${2:-}"
      shift 2
      ;;
    --pip-trusted-host)
      export SMARTASK_PIP_TRUSTED_HOST="${2:-}"
      shift 2
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

LOCAL_STASH_CREATED=0
LOCAL_STASH_NOTE=""

save_local_git_changes() {
  local status_text timestamp local_dir
  status_text="$(git status --porcelain --untracked-files=no)"
  if [[ -z "$status_text" ]]; then
    return 0
  fi

  timestamp="$(date +%Y%m%d_%H%M%S)"
  local_dir="$SCRIPT_DIR/backups/local_git_changes_${timestamp}"
  mkdir -p "$local_dir"
  git status --short --untracked-files=no > "$local_dir/git_status.txt" || true
  git diff > "$local_dir/tracked_changes.patch" || true
  git diff --staged > "$local_dir/staged_changes.patch" || true

  warn "检测到服务器 tracked 文件存在本地改动，已保存到: $local_dir"
  warn "这些改动会先进入 git stash，避免 git pull 覆盖失败。"
  git stash push -m "smartask-update-${timestamp}" >/dev/null
  LOCAL_STASH_CREATED=1
  LOCAL_STASH_NOTE="本地 tracked 改动已暂存到 git stash: smartask-update-${timestamp}；补丁备份目录: $local_dir"
}

render_progress_bar() {
  local current="$1"
  local total="$2"
  local message="${3:-}"
  local width=30
  local percent=$((current * 100 / total))
  local filled=$((current * width / total))
  local empty=$((width - filled))
  local bar_done bar_left

  bar_done="$(printf "%${filled}s" "" | tr ' ' '#')"
  bar_left="$(printf "%${empty}s" "" | tr ' ' '-')"
  printf "\r  [%s%s] %3d%% %ds/%ds %s" "$bar_done" "$bar_left" "$percent" "$((current * 2))" "$((total * 2))" "$message"
}

backend_container_health() {
  docker inspect smartask-backend \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
    2>/dev/null || true
}

dump_backend_diagnostics() {
  local url="$1"

  echo ""
  warn "后端健康检查失败，开始输出诊断信息"
  echo ""
  echo "---- docker compose ps ----"
  docker compose ps || true
  echo ""
  echo "---- backend container state ----"
  docker inspect smartask-backend \
    --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} exit={{.State.ExitCode}} error={{.State.Error}}' \
    2>/dev/null || true
  echo ""
  echo "---- curl health ----"
  curl -vS --max-time 8 "$url" || true
  echo ""
  echo "---- backend logs tail 180 ----"
  docker compose logs --tail=180 backend || true
  echo ""
}

wait_for_backend_health() {
  local port="$1"
  local attempts="${2:-90}"
  local url="http://127.0.0.1:${port}/api/health"
  local attempt status

  command -v curl >/dev/null 2>&1 || fail "未找到 curl，无法执行健康检查。请先安装 curl，或手动访问: $url"

  echo "  健康检查地址: $url"
  for attempt in $(seq 1 "$attempts"); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      echo ""
      echo "  [OK] 后端健康检查通过: $url"
      return 0
    fi

    status="$(backend_container_health)"
    render_progress_bar "$attempt" "$attempts" "backend=${status:-unknown}"

    if [[ "$status" == "healthy" ]]; then
      echo ""
      warn "宿主机 $url 暂未返回成功，但 backend 容器健康检查已 healthy，继续执行后续自检。"
      return 0
    fi

    sleep 2
  done

  echo ""
  dump_backend_diagnostics "$url"
  return 1
}

read_env() {
  local key="$1"
  local default="${2:-}"
  if [[ ! -f .env ]]; then
    echo "$default"
    return
  fi
  local value
  value="$(
    grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" .env \
      | tail -n1 \
      | sed -E "s/^[[:space:]]*(export[[:space:]]+)?${key}=//" \
      | tr -d '\r' \
      | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' \
      || true
  )"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
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
  save_local_git_changes
  git checkout "$BRANCH"
  git pull --ff-only
else
  warn "已跳过 Git 拉取"
fi

BACKEND_PORT="$(read_env SMARTASK_BACKEND_PORT 5002)"
FRONTEND_PORT="$(read_env SMARTASK_FRONTEND_PORT 8080)"
SMARTASK_PIP_INDEX_URL="${SMARTASK_PIP_INDEX_URL:-$(read_env SMARTASK_PIP_INDEX_URL https://mirrors.aliyun.com/pypi/simple/)}"
SMARTASK_PIP_TRUSTED_HOST="${SMARTASK_PIP_TRUSTED_HOST:-$(read_env SMARTASK_PIP_TRUSTED_HOST mirrors.aliyun.com)}"
SMARTASK_PIP_TIMEOUT="${SMARTASK_PIP_TIMEOUT:-$(read_env SMARTASK_PIP_TIMEOUT 120)}"
SMARTASK_PIP_RETRIES="${SMARTASK_PIP_RETRIES:-$(read_env SMARTASK_PIP_RETRIES 8)}"
export SMARTASK_PIP_INDEX_URL SMARTASK_PIP_TRUSTED_HOST SMARTASK_PIP_TIMEOUT SMARTASK_PIP_RETRIES

if [[ "$NO_BUILD" -eq 0 ]]; then
  info "Docker 构建下载源"
  echo "  pip index : ${SMARTASK_PIP_INDEX_URL:-官方默认源}"
  echo "  pip host  : ${SMARTASK_PIP_TRUSTED_HOST:-未设置}"
  echo "  pip retry : timeout=${SMARTASK_PIP_TIMEOUT}s retries=${SMARTASK_PIP_RETRIES}"
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

info "等待后端健康检查"
wait_for_backend_health "$BACKEND_PORT" 90 || fail "后端健康检查失败。请执行: bash doctor.sh"
docker compose ps

if [[ "$SKIP_VERIFY" -eq 0 ]]; then
  info "运行容器内自检"
  docker compose exec -T backend python /app/scripts/verify_deployment.py || fail "容器内自检失败。请执行: bash doctor.sh"
else
  warn "已跳过容器内自检: --skip-verify"
fi

echo ""
echo "[OK] 更新完成。页面如仍旧，请浏览器 Ctrl+F5。"
echo "用户访问地址: http://服务器IP:${FRONTEND_PORT}"
if [[ "$LOCAL_STASH_CREATED" -eq 1 ]]; then
  warn "$LOCAL_STASH_NOTE"
  warn "如需查看: git stash list；如需人工恢复某项改动，请先确认新版本配置后再 git stash show -p stash@{0}"
fi

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
