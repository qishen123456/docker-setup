#!/usr/bin/env bash
set -euo pipefail

# =========================
# SmartAsk 更新脚本（支持自动环境检测）
# 用途：自动备份 → 拉取代码 → 重建容器 → 健康检查
#
# 环境检测：
#   Linux   → 自动使用外部代理模式（proxy）重建
#   Windows → 自动使用本地模式（local）重建
#
# 使用方式：
#   bash update.sh                    # 标准更新（自动检测环境）
#   bash update.sh --no-build         # 不重新构建镜像
#   bash update.sh --skip-backup      # 跳过备份（不推荐生产环境）
#   bash update.sh --run-tests        # 更新后运行测试
# =========================

NO_BUILD=0
NO_PULL=0
SKIP_BACKUP=0
RUN_TESTS=0
RUN_STREAM_TESTS=0
# 自动动态获取当前所在的分支，永不锁死特定分支
CURRENT_GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'docker-setup')"
BRANCH="${SMARTASK_GIT_BRANCH:-$CURRENT_GIT_BRANCH}"
REMOTE="${SMARTASK_GIT_REMOTE_NAME:-}"
SKIP_VERIFY=0

# =========================
# 自动环境检测（与 deploy.sh 保持一致）
# =========================
detect_environment() {
  local os_name os_type recommend_mode

  case "$(uname -s)" in
    Linux*)
      os_name="Linux"
      os_type="server"
      if [[ -f /proc/version ]] && grep -qi "microsoft\|wsl" /proc/version 2>/dev/null; then
        os_name="WSL (Windows Subsystem for Linux)"
        os_type="windows"
        recommend_mode="local"
      else
        recommend_mode="proxy"
      fi
      ;;
    Darwin*)
      os_name="macOS"
      os_type="development"
      recommend_mode="local"
      ;;
    MINGW*|CYGWIN*|MSYS*)
      os_name="Windows (Git Bash/MSYS2)"
      os_type="windows"
        recommend_mode="local"
      ;;
    *)
      os_name="$(uname -s) (未知系统)"
      os_type="unknown"
      recommend_mode="local"
      ;;
  esac

  echo "${os_name}|${os_type}|${recommend_mode}"
}

# 获取环境信息
IFS='|' read -r OS_NAME OS_TYPE RECOMMEND_MODE <<< "$(detect_environment)"

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
      BRANCH="${2:-docker-setup}"  # 默认使用 docker-setup 分支
      shift 2
      ;;
    --remote)
      REMOTE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk 更新脚本（支持自动环境检测 + 智能分支管理）

用法：
  bash update.sh                          # 标准更新（自动检测环境+使用main分支）
  bash update.sh --branch docker-setup    # 指定拉取 docker-setup 分支
  bash update.sh --run-tests              # 更新后运行测试
  bash update.sh --remote github          # 指定远程仓库名
  bash update.sh --no-pull                # 不拉取Git，仅重建容器
  bash update.sh --skip-backup            # 跳过备份（不推荐生产环境）
  bash update.sh --no-build               # 不重新构建镜像

参数：
  --branch NAME        指定更新分支（默认: main，与本地开发保持一致）。
                       示例: --branch main 或 --branch docker-setup
  --remote NAME        指定 Git 远端名，例如 github；未指定时使用当前分支 upstream。
  --no-build           不重新构建镜像，只重启容器。
  --no-pull            不拉取 Git，仅用当前代码重建。
  --skip-backup        跳过更新前备份，不建议生产环境使用。
  --run-tests          更新后运行接口测试。
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
RUNTIME_CONFIG_BACKUP_DIR=""
RUNTIME_CONFIG_FILES=(
  ".secret_master_key"
  "app_config.json"
  "datasources.json"
  "ai_settings.json"
  "feishu_sync.json"
  "sql_prompts.json"
  "employee_permissions.json"
  "data_permissions.json"
  "rbac_permissions.json"
  "organization_trees.json"
  "feature_flags.json"
  "ask_flow.json"
  "auth_tokens.json"
  "advanced_capabilities.json"
  "query_history.json"
  "smartask_report_history.json"
)

preserve_runtime_config_files() {
  local timestamp backup_dir copied=0 file
  if [[ ! -d config ]]; then
    return 0
  fi

  timestamp="$(date +%Y%m%d_%H%M%S)"
  backup_dir="$SCRIPT_DIR/backups/runtime_config_before_pull_${timestamp}"
  mkdir -p "$backup_dir"

  for file in "${RUNTIME_CONFIG_FILES[@]}"; do
    if [[ -f "config/$file" ]]; then
      cp -a "config/$file" "$backup_dir/$file" || true
      copied=1
    fi
  done

  if [[ "$copied" -eq 1 ]]; then
    RUNTIME_CONFIG_BACKUP_DIR="$backup_dir"
    warn "已暂存运行态配置，避免 git pull 覆盖: $backup_dir"
  else
    rmdir "$backup_dir" 2>/dev/null || true
  fi
}

restore_runtime_config_files() {
  local file
  if [[ -z "$RUNTIME_CONFIG_BACKUP_DIR" || ! -d "$RUNTIME_CONFIG_BACKUP_DIR" ]]; then
    return 0
  fi

  mkdir -p config
  for file in "${RUNTIME_CONFIG_FILES[@]}"; do
    if [[ -f "$RUNTIME_CONFIG_BACKUP_DIR/$file" ]]; then
      cp -a "$RUNTIME_CONFIG_BACKUP_DIR/$file" "config/$file" || true
    fi
  done
  warn "已恢复服务器运行态配置: config/*.json"
}

save_local_git_changes() {
  local status_text timestamp local_dir
  status_text="$(git status --porcelain --untracked-files=all)"
  if [[ -z "$status_text" ]]; then
    echo "  Git local changes: clean"
    return 0
  fi

  timestamp="$(date +%Y%m%d_%H%M%S)"
  local_dir="$SCRIPT_DIR/backups/local_git_changes_${timestamp}"
  mkdir -p "$local_dir"
  git status --short --untracked-files=all > "$local_dir/git_status.txt" || true
  git diff > "$local_dir/tracked_changes.patch" || true
  git diff --staged > "$local_dir/staged_changes.patch" || true
  git ls-files --others --exclude-standard > "$local_dir/untracked_files.txt" || true

  if [[ -s "$local_dir/untracked_files.txt" ]]; then
    while IFS= read -r file; do
      [[ -e "$file" ]] || continue
      mkdir -p "$local_dir/untracked/$(dirname "$file")"
      cp -a "$file" "$local_dir/untracked/$file" 2>/dev/null || true
    done < "$local_dir/untracked_files.txt"
  fi

  warn "检测到服务器存在本地改动或未跟踪文件，已保存到: $local_dir"
  warn "这些改动会先进入 git stash，避免 git pull 被本地文件阻断。"

  # 兼容旧版Git（CentOS 7等系统的Git 1.x/2.x）
  local git_stash_cmd
  if git stash --help 2>&1 | grep -q "push"; then
    git_stash_cmd="git stash push --include-untracked -m"
  else
    git_stash_cmd="git stash save --include-untracked"
  fi

  $git_stash_cmd "smartask-update-${timestamp}" || {
    warn "git stash 失败（可能是空stash或Git版本问题），尝试继续更新..."
    LOCAL_STASH_CREATED=0
  }
  if [[ "$LOCAL_STASH_CREATED" -eq 1 ]]; then
    LOCAL_STASH_NOTE="本地 tracked/untracked 改动已暂存到 git stash: smartask-update-${timestamp}；备份目录: $local_dir"
    echo "  Git local changes: stashed"
  fi
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

cleanup_compose_recreate_leftovers() {
  local ids
  ids="$(
    docker ps -a --format '{{.ID}} {{.Names}}' \
      | awk '$2 ~ /^[0-9a-f]+_smartask-(backend|frontend|postgres)$/ {print $1}' \
      || true
  )"
  if [[ -z "$ids" ]]; then
    return 0
  fi

  warn "检测到上次 Docker Compose 重建中断留下的临时容器，准备清理。"
  printf "%s\n" "$ids" | xargs docker rm -f >/dev/null 2>/dev/null || true
  warn "临时容器已清理，继续更新。"
}

dump_backend_diagnostics() {
  local url="$1"

  echo ""
  warn "后端健康检查失败，开始输出诊断信息"
  echo ""
  echo "---- docker compose ps ----"
  dc ps || true
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
  dc logs --tail=180 backend || true
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

has_encrypted_runtime_secret() {
  if [[ -f .env ]] && grep -q "enc:v1:" .env; then
    return 0
  fi
  if [[ -d config ]] && find config -type f -name '*.json' -exec grep -qs "enc:v1:" {} +; then
    return 0
  fi
  return 1
}

validate_secret_master_key() {
  local inline_key key_file
  if ! has_encrypted_runtime_secret; then
    return 0
  fi

  inline_key="$(read_env SMARTASK_SECRET_MASTER_KEY "")"
  if [[ -n "$inline_key" ]]; then
    warn "检测到 enc:v1 密文，并将使用 .env 中的 SMARTASK_SECRET_MASTER_KEY 解密。生产环境更建议使用 config/.secret_master_key 或 Docker Secret。"
    return 0
  fi

  key_file="$(read_env SMARTASK_SECRET_KEY_FILE "")"
  if [[ -n "$key_file" ]]; then
    if [[ -f "$key_file" ]]; then
      echo "  [OK] 检测到密文主密钥文件: $key_file"
      return 0
    fi
    if [[ "$key_file" == /* ]]; then
      warn "SMARTASK_SECRET_KEY_FILE=$key_file 是容器内绝对路径，宿主机无法直接校验；请确认 ${DOCKER_COMPOSE_CMD} 已挂载该 Secret。"
      return 0
    fi
    fail "检测到 enc:v1 密文，但 SMARTASK_SECRET_KEY_FILE 指向的文件不存在: $key_file"
  fi

  if [[ -f config/.secret_master_key ]]; then
    echo "  [OK] 检测到密文主密钥文件: config/.secret_master_key"
    return 0
  fi

  fail "检测到 enc:v1 密文，但缺少主密钥。请把 config/.secret_master_key 放回服务器，或设置 SMARTASK_SECRET_MASTER_KEY / SMARTASK_SECRET_KEY_FILE 后再更新。"
}

find_secret_check_python() {
  local candidate version
  for candidate in python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 7) else 1)
PY
    then
      echo "$candidate"
      return 0
    fi
    version="$("$candidate" <<'PY' 2>/dev/null || true
import sys
print(".".join(str(item) for item in sys.version_info[:3]))
PY
)"
    warn "宿主机 ${candidate} 版本 ${version:-unknown} 过低，无法导入新版加密模块做提前校验。" >&2
  done
  return 1
}

validate_runtime_secret_decryption() {
  local pybin
  if ! has_encrypted_runtime_secret; then
    return 0
  fi

  if ! pybin="$(find_secret_check_python)"; then
    warn "未找到 Python 3.7+，跳过宿主机 enc:v1 提前解密校验；将继续由 Docker 容器启动时校验。"
    return 0
  fi

  "$pybin" <<'PY' || fail "检测到 enc:v1 密文，但当前主密钥无法解密。请恢复原 config/.secret_master_key，或用当前主密钥重新加密 .env/config 中的密文。"
import json
import os
import sys
from pathlib import Path

ROOT = Path.cwd()


def parse_env(path: Path):
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


env_values = parse_env(ROOT / ".env")
for key in ("SMARTASK_SECRET_MASTER_KEY", "SMARTASK_SECRET_KEY_FILE"):
    if env_values.get(key):
        os.environ[key] = env_values[key]

sys.path.insert(0, str(ROOT / "backend"))
from secret_codec import decrypt_secret_value, is_encrypted_secret  # noqa: E402

targets = []
for key, value in env_values.items():
    if is_encrypted_secret(value):
        targets.append((f".env:{key}", value))


def collect_json_secrets(node, label: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            collect_json_secrets(value, f"{label}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            collect_json_secrets(value, f"{label}[{index}]")
    elif isinstance(node, str) and is_encrypted_secret(node):
        targets.append((label, node))


config_dir = ROOT / "config"
if config_dir.exists():
    for path in sorted(config_dir.glob("*.json")):
        try:
            collect_json_secrets(json.loads(path.read_text(encoding="utf-8")), f"config/{path.name}")
        except Exception:
            continue

failed = []
non_blocking_failed = []
for label, value in targets:
    try:
        decrypt_secret_value(value)
    except Exception as exc:
        item = f"{label}: {exc}"
        if label.startswith("config/ai_settings.json.") and ".api_key_b64" in label:
            non_blocking_failed.append(item)
        else:
            failed.append(item)

if failed:
    print("以下密文无法用当前主密钥解开：", file=sys.stderr)
    for item in failed[:20]:
        print(f"  - {item}", file=sys.stderr)
    if len(failed) > 20:
        print(f"  ... 还有 {len(failed) - 20} 项", file=sys.stderr)
    raise SystemExit(1)

if non_blocking_failed:
    print("以下 AI 模型密钥无法用当前主密钥解开，更新不会因此中断；如需使用对应模型，请在管理页面重新保存 API Key：", file=sys.stderr)
    for item in non_blocking_failed[:20]:
        print(f"  - {item}", file=sys.stderr)
    if len(non_blocking_failed) > 20:
        print(f"  ... 还有 {len(non_blocking_failed) - 20} 项", file=sys.stderr)

print(f"  [OK] enc:v1 密文解密校验通过，共 {len(targets)} 项")
PY
}

validate_postgres_password_hint() {
  local db_password postgres_password db_host
  db_host="$(read_env SMARTASK_DB_HOST "postgres")"
  db_password="$(read_env SMARTASK_DB_PASSWORD "")"
  postgres_password="$(read_env SMARTASK_POSTGRES_PASSWORD "")"

  if [[ "$db_host" == "postgres" && "$db_password" == enc:v1:* && -z "$postgres_password" ]]; then
    warn "SMARTASK_DB_PASSWORD 是 enc:v1 密文，但 compose 自带的 Postgres 不能解密。"
    warn "如果本次是首次建库、清空过数据库卷，或日志里出现 password authentication failed，请在 .env 增加 SMARTASK_POSTGRES_PASSWORD=数据库明文密码。"
  fi
}

command -v git >/dev/null 2>&1 || fail "未找到 git 命令"
command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
docker info >/dev/null 2>&1 || fail "Docker 未启动或当前用户无权限访问 Docker"

# =========================
# Docker Compose 命令兼容性检测
# 支持 docker-compose（v1）和 ${DOCKER_COMPOSE_CMD}（v2 plugin）
# =========================
detect_docker_compose_cmd() {
  # 优先使用 docker-compose（独立安装的 v1 版本）
  if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    info "检测到 docker-compose（v1 独立版本）"
  # 其次尝试 docker compose（Docker 内置的 v2 插件）
  elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    info "检测到 docker compose（v2 插件）"
  else
    fail "未找到 Docker Compose！请安装：\n  - CentOS/RHEL: yum install docker-compose-plugin\n  - Ubuntu/Debian: apt install docker-compose-plugin\n  - 或手动下载: https://docs.docker.com/compose/install/"
  fi
}

detect_docker_compose_cmd
[[ -f .env ]] || fail "缺少 .env，请先放好生产配置"
validate_secret_master_key
validate_runtime_secret_decryption
validate_postgres_password_hint

if [[ "$SKIP_BACKUP" -eq 0 ]]; then
  info "更新前备份"
  bash "$SCRIPT_DIR/backup.sh" || fail "备份失败，已停止更新以保护生产数据"
else
  warn "已跳过备份。生产环境不建议使用 --skip-backup"
fi

if [[ "$NO_PULL" -eq 0 ]]; then
  info "拉取最新代码"
  preserve_runtime_config_files
  if [[ -n "$REMOTE" ]]; then
    echo "  Git fetch: $REMOTE/$BRANCH"
    git fetch "$REMOTE" "$BRANCH" || {
      restore_runtime_config_files
      fail "从远端 $REMOTE 拉取分支 $BRANCH 失败"
    }
  else
    echo "  Git fetch: origin/$BRANCH"
    git fetch origin "$BRANCH"
  fi
  echo "  Git local changes check"
  save_local_git_changes
  echo "  Git checkout: $BRANCH"
  if ! git checkout "$BRANCH"; then
    restore_runtime_config_files
    fail "切换分支失败，已尽量恢复运行态配置"
  fi
  if [[ -n "$REMOTE" ]]; then
    echo "  Git remote: $REMOTE"
    echo "  Git branch: $BRANCH"
    git branch --set-upstream-to="$REMOTE/$BRANCH" "$BRANCH" 2>/dev/null || true
    echo "  Git merge: $REMOTE/$BRANCH"
    if ! git merge --ff-only "$REMOTE/$BRANCH"; then
      restore_runtime_config_files
      fail "拉取 $REMOTE/$BRANCH 失败，已尽量恢复运行态配置"
    fi
  elif ! git pull --ff-only; then
    restore_runtime_config_files
    fail "拉取最新代码失败，已尽量恢复运行态配置"
  fi
  restore_runtime_config_files
else
  warn "已跳过 Git 拉取"
fi

BACKEND_PORT="$(read_env SMARTASK_BACKEND_PORT 5002)"
FRONTEND_PORT="$(read_env SMARTASK_FRONTEND_PORT 8888)"
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

info "校验 ${DOCKER_COMPOSE_CMD}"

# 根据环境自动选择docker-compose配置文件（兼容 v1/v2）
COMPOSE_FILE_ARGS="-f docker-compose.yml"
case "${RECOMMEND_MODE}" in
  proxy)
    # Linux服务器：使用外部代理模式（禁用Docker内Nginx）
    COMPOSE_FILE_ARGS="-f docker-compose.yml -f docker-compose.proxy.yml"
    warn "检测到服务器环境，将使用外部代理模式（proxy）启动..."
    echo "  配置文件：docker-compose.yml docker-compose.proxy.yml"
    ;;
  local|*)
    echo "检测到${OS_NAME}环境，将使用本地模式启动..."
    echo "  配置文件：docker-compose.yml"
    ;;
esac

# 统一的 docker compose 执行函数（解决参数传递兼容性问题）
dc() {
  ${DOCKER_COMPOSE_CMD} ${COMPOSE_FILE_ARGS} "$@"
}

# 使用选定的配置文件进行校验和启动
dc config >/dev/null
cleanup_compose_recreate_leftovers

info "重建并启动容器"
if [[ "$NO_BUILD" -eq 1 ]]; then
  dc up -d
else
  dc up -d --build
fi
echo "  [OK] migrate 服务已自动执行数据库迁移（backend/migrations），迁移成功后启动 Flask 服务"

info "等待后端健康检查"
wait_for_backend_health "$BACKEND_PORT" 90 || fail "后端健康检查失败。请执行: bash doctor.sh"
dc ps

# 内置数据集模板同步已移除（2026-08-10 bootstrap 解耦 BugFix）：
# apply_payload_direct() 会 DELETE+全插 bs_* 子表，覆盖用户文件迁移导入的
# golden sql / 数据字典 / agent prompt。元数据改由 bundle 导入导出流程管理。
# 如需手动同步内置模板：dc exec -T backend python /app/backend/create_consumer_standard_dataset.py --direct

if [[ "$SKIP_VERIFY" -eq 0 ]]; then
  info "运行容器内自检"
  dc exec -T backend python /app/scripts/verify_deployment.py || fail "容器内自检失败。请执行: bash doctor.sh"
else
  warn "已跳过容器内自检: --skip-verify"
fi

echo ""
echo "[OK] 更新完成。页面如仍旧，请浏览器 Ctrl+F5。"
echo "用户访问地址: http://服务器IP:${FRONTEND_PORT}"
if [[ "$LOCAL_STASH_CREATED" -eq 1 ]]; then
  warn "$LOCAL_STASH_NOTE"
  warn "如需查看: git stash list；如需恢复单个文件，请先确认新版本配置后再执行: git checkout 'stash@{0}' -- 文件路径"
fi

if [[ "$RUN_TESTS" -eq 1 ]]; then
  info "运行集成测试"
  STREAM_ARGS=()
  if [[ "$RUN_STREAM_TESTS" -eq 1 ]]; then
    STREAM_ARGS+=(--with-stream)
  fi
  dc exec -T backend python -m pip install --quiet --disable-pip-version-check requests || true
  dc exec -T backend python /app/scripts/integration_test.py \
    --base-url "http://localhost:5002" \
    --frontend-url "http://frontend" \
    --no-wait "${STREAM_ARGS[@]}"
fi

# =========================
# 更新完成提示（包含环境信息）
# =========================
echo ""
echo "[OK] 更新完成。页面如仍旧，请浏览器 Ctrl+F5。"
echo ""
echo "📌 环境信息："
echo "  操作系统: ${OS_NAME}"
echo "  环境类型: ${OS_TYPE}"
echo "  使用模式: ${RECOMMEND_MODE}"

case "${RECOMMEND_MODE}" in
  proxy)
    echo ""
    echo "用户访问地址: ${FRONTEND_URL:-https://bifine.angelgroup.com.cn:10899/smart-ask}"
    echo "后端API地址: http://服务器IP:${BACKEND_PORT:-5002}/api/health"
    ;;
  local|*)
    echo ""
    echo "前端访问地址: http://localhost:${FRONTEND_PORT:-8888}"
    echo "后端API地址: http://localhost:${BACKEND_PORT:-5002}/api/health"
    ;;
esac

if [[ "$LOCAL_STASH_CREATED" -eq 1 ]]; then
  warn "$LOCAL_STASH_NOTE"
  warn "如需查看: git stash list；如需恢复单个文件，请先确认新版本配置后再执行: git checkout 'stash@{0}' -- 文件路径"
fi
