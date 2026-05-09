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

镜像源环境变量：
  SMARTASK_APT_MIRROR=https://mirrors.aliyun.com
  SMARTASK_DOCKER_REGISTRY_MIRRORS=https://docker.m.daocloud.io,https://docker.1ms.run
  SMARTASK_SKIP_APT_MIRROR=1
  SMARTASK_SKIP_DOCKER_MIRROR=1
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

is_root() {
  [[ "$(id -u)" -eq 0 ]]
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

restart_docker_daemon() {
  if command_exists systemctl; then
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl restart docker >/dev/null 2>&1 || {
      warn "Docker 镜像源已写入，但 Docker 重启失败，请稍后手动执行: systemctl restart docker"
      return 1
    }
    return 0
  fi

  if command_exists service; then
    service docker restart >/dev/null 2>&1 || {
      warn "Docker 镜像源已写入，但 Docker 重启失败，请稍后手动执行: service docker restart"
      return 1
    }
    return 0
  fi

  warn "未找到 systemctl/service，Docker 镜像源已写入，请手动重启 Docker"
  return 1
}

configure_docker_registry_mirror() {
  if [[ "${SMARTASK_SKIP_DOCKER_MIRROR:-0}" == "1" ]]; then
    warn "已跳过 Docker 镜像源配置: SMARTASK_SKIP_DOCKER_MIRROR=1"
    return
  fi

  if ! is_root; then
    warn "当前不是 root，跳过 Docker 镜像源配置。需要时请用 sudo/root 执行 deploy.sh"
    return
  fi

  local mirrors
  mirrors="$(read_env SMARTASK_DOCKER_REGISTRY_MIRRORS "${SMARTASK_DOCKER_REGISTRY_MIRRORS:-https://docker.m.daocloud.io,https://docker.1ms.run,https://hub-mirror.c.163.com,https://mirror.baidubce.com}")"

  mkdir -p /etc/docker

  local python_bin=""
  if command_exists python3; then
    python_bin="python3"
  elif command_exists python; then
    python_bin="python"
  fi

  if [[ -z "$python_bin" && -f /etc/docker/daemon.json ]]; then
    warn "未找到 python，且 daemon.json 已存在；为避免覆盖已有 Docker 配置，跳过自动合并。"
    return
  fi

  local backup=""
  if [[ -f /etc/docker/daemon.json ]]; then
    backup="/etc/docker/daemon.json.smartask.bak.$(date +%Y%m%d%H%M%S)"
    cp -a /etc/docker/daemon.json "$backup"
  fi

  if [[ -n "$python_bin" ]]; then
    SMARTASK_DOCKER_REGISTRY_MIRRORS="$mirrors" "$python_bin" <<'PY'
import json
import os
from pathlib import Path

path = Path("/etc/docker/daemon.json")
raw = path.read_text(encoding="utf-8").strip() if path.exists() else ""
data = {}
if raw:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

mirrors = [
    item.strip()
    for item in os.environ.get("SMARTASK_DOCKER_REGISTRY_MIRRORS", "").replace("\n", ",").split(",")
    if item.strip()
]
data["registry-mirrors"] = mirrors
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  else
    cat >/etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
  fi

  restart_docker_daemon || true
  if [[ -n "$backup" ]]; then
    ok "Docker 镜像源已更新，原配置备份: $backup"
  else
    ok "Docker 镜像源已更新"
  fi
}

write_ubuntu_apt_sources() {
  local codename="$1"
  local mirror="$2"
  local target="$3"

  if [[ "$target" == *.sources ]]; then
    cat >"$target" <<EOF
Types: deb
URIs: ${mirror}/ubuntu/
Suites: ${codename} ${codename}-updates ${codename}-backports ${codename}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
  else
    cat >"$target" <<EOF
deb ${mirror}/ubuntu/ ${codename} main restricted universe multiverse
deb ${mirror}/ubuntu/ ${codename}-updates main restricted universe multiverse
deb ${mirror}/ubuntu/ ${codename}-backports main restricted universe multiverse
deb ${mirror}/ubuntu/ ${codename}-security main restricted universe multiverse
EOF
  fi
}

write_debian_apt_sources() {
  local codename="$1"
  local mirror="$2"
  local target="$3"

  if [[ "$target" == *.sources ]]; then
    cat >"$target" <<EOF
Types: deb
URIs: ${mirror}/debian/
Suites: ${codename} ${codename}-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: ${mirror}/debian-security/
Suites: ${codename}-security
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
  else
    cat >"$target" <<EOF
deb ${mirror}/debian/ ${codename} main contrib non-free non-free-firmware
deb ${mirror}/debian/ ${codename}-updates main contrib non-free non-free-firmware
deb ${mirror}/debian-security/ ${codename}-security main contrib non-free non-free-firmware
EOF
  fi
}

configure_apt_mirror() {
  if [[ "${SMARTASK_SKIP_APT_MIRROR:-0}" == "1" ]]; then
    warn "已跳过 APT 镜像源配置: SMARTASK_SKIP_APT_MIRROR=1"
    return
  fi

  if ! command_exists apt-get; then
    warn "当前系统不是 apt 系，跳过 APT 镜像源配置"
    return
  fi

  if ! is_root; then
    warn "当前不是 root，跳过 APT 镜像源配置。需要时请用 sudo/root 执行 deploy.sh"
    return
  fi

  [[ -r /etc/os-release ]] || {
    warn "未找到 /etc/os-release，跳过 APT 镜像源配置"
    return
  }

  # shellcheck disable=SC1091
  source /etc/os-release
  local os_id="${ID:-}"
  local codename="${VERSION_CODENAME:-}"
  local mirror
  mirror="$(read_env SMARTASK_APT_MIRROR "${SMARTASK_APT_MIRROR:-https://mirrors.aliyun.com}")"

  if [[ -z "$codename" ]] && command_exists lsb_release; then
    codename="$(lsb_release -cs 2>/dev/null || true)"
  fi

  if [[ -z "$codename" ]]; then
    warn "未识别系统代号，跳过 APT 镜像源配置"
    return
  fi

  local target="/etc/apt/sources.list"
  if [[ "$os_id" == "ubuntu" && -f /etc/apt/sources.list.d/ubuntu.sources ]]; then
    target="/etc/apt/sources.list.d/ubuntu.sources"
  elif [[ "$os_id" == "debian" && -f /etc/apt/sources.list.d/debian.sources ]]; then
    target="/etc/apt/sources.list.d/debian.sources"
  fi

  local backup="${target}.smartask.bak.$(date +%Y%m%d%H%M%S)"
  [[ -f "$target" ]] && cp -a "$target" "$backup"

  case "$os_id" in
    ubuntu)
      write_ubuntu_apt_sources "$codename" "$mirror" "$target"
      ;;
    debian)
      write_debian_apt_sources "$codename" "$mirror" "$target"
      ;;
    *)
      warn "暂不自动改写 $os_id 的 APT 源，已跳过"
      return
      ;;
  esac

  apt-get update || warn "APT 源已写入，但 apt-get update 失败；如网络受限，可稍后手动重试。备份: $backup"
  ok "APT 镜像源已更新: $mirror，原配置备份: $backup"
}

info "1/7 检查 Docker"
command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
docker info >/dev/null 2>&1 || fail "Docker 未启动或当前用户无权限访问 Docker"
docker compose version >/dev/null 2>&1 || fail "未找到 Docker Compose Plugin"
ok "Docker 可用"

info "2/7 配置 Linux 镜像源"
configure_apt_mirror
configure_docker_registry_mirror
docker info >/dev/null 2>&1 || fail "Docker 镜像源配置后 Docker 不可用，请执行: bash doctor.sh"
ok "镜像源检查完成"

info "3/7 检查 .env"
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

info "4/7 校验 docker compose"
docker compose config >/dev/null
ok "docker-compose.yml 有效"

info "5/7 构建并启动容器"
if [[ "$NO_BUILD" -eq 1 ]]; then
  docker compose up -d
else
  docker compose up -d --build
fi

info "6/7 等待后端健康检查"
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

info "7/7 部署完成"
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
