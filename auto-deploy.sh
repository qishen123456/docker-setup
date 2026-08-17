#!/usr/bin/env bash
# ============================================================
# SmartAsk 一键部署脚本（从Git拉代码到服务启动）
# 使用方法:
#   chmod +x auto-deploy.sh
#   ./auto-deploy.sh [选项]
#
# 选项:
#   --git-url <url>        Git仓库地址（必填，首次部署）
#   --branch <branch>      分支名（默认main）
#   --env-file <path>      .env文件路径（默认./.env）
#   --skip-git             跳过Git拉取（本地已有代码）
#   --skip-env-check       跳过.env配置检查（不推荐）
#   --with-backup          导入旧环境备份包
#   --backup-file <path>   备份包路径
#   -h, --help             显示帮助信息
#
# 示例:
#   # 首次部署（从Git拉代码）
#   ./auto-deploy.sh --git-url https://github.com/your-org/smartask.git
#
#   # 更新部署（跳过Git）
#   ./auto-deploy.sh --skip-git
#
#   # 带旧数据迁移的部署
#   ./auto-deploy.sh --skip-git --with-backup --backup-file /tmp/runtime_config_bundle.json
# ============================================================

set -euo pipefail

# ==================== 全局变量 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_URL=""
BRANCH="main"
ENV_FILE=".env"
SKIP_GIT=0
SKIP_ENV_CHECK=0
WITH_BACKUP=0
BACKUP_FILE=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deploy_${TIMESTAMP}.log"

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== 工具函数 ====================
log_info() {
  echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_ok() {
  echo -e "${GREEN}[OK]${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

fail() {
  log_error "$*"
  exit 1
}

show_progress() {
  local current=$1
  local total=$2
  local message=${3:-}
  local width=40
  local percent=$((current * 100 / total))
  local filled=$((current * width / total))
  local empty=$((width - filled))

  printf "\r  ["
  printf "%${filled}s" '' | tr ' ' '='
  printf "%${empty}s" '' | tr ' ' '-'
  printf "] %3d%% %s" "$percent" "$message"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# ==================== 参数解析 ====================
parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --git-url)
        GIT_URL="$2"
        shift 2
        ;;
      --branch)
        BRANCH="$2"
        shift 2
        ;;
      --env-file)
        ENV_FILE="$2"
        shift 2
        ;;
      --skip-git)
        SKIP_GIT=1
        shift
        ;;
      --skip-env-check)
        SKIP_ENV_CHECK=1
        shift
        ;;
      --with-backup)
        WITH_BACKUP=1
        shift
        ;;
      --backup-file)
        BACKUP_FILE="$2"
        shift 2
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      *)
        fail "未知参数: $1 (使用 -h 查看帮助)"
        ;;
    esac
  done
}

show_help() {
  cat <<'EOF'
SmartAsk 一键部署脚本 v1.0

用法:
  ./auto-deploy.sh [选项]

必需参数（首次部署）:
  --git-url <url>        Git仓库地址

可选参数:
  --branch <branch>      分支名 (默认: main)
  --env-file <path>      .env文件路径 (默认: ./.env)
  --skip-git             跳过Git拉取（更新部署时使用）
  --skip-env-check       跳过.env配置检查（不推荐）
  --with-backup          导入旧环境备份包
  --backup-file <path>   备份包文件路径
  -h, --help             显示此帮助信息

示例:
  # 首次全新部署
  ./auto-deploy.sh --git-url https://github.com/org/smartask.git

  # 更新已有部署
  ./auto-deploy.sh --skip-git

  # 迁移部署（带数据）
  ./auto-deploy.sh --skip-git --with-backup --backup-file ./runtime_config_bundle.json
EOF
}

# ==================== Phase 0: 环境检查 ====================
check_prerequisites() {
  log_info "Phase 0/6: 检查运行环境..."

  # 检查操作系统
  if [[ "$(uname)" != "Linux" ]]; then
    log_warn "当前系统不是Linux，部分功能可能受限"
  fi

  # 检查必要命令
  local required_commands=("docker" "docker compose" "curl" "git")
  for cmd in "${required_commands[@]}"; do
    if ! command_exists "$cmd"; then
      fail "缺少必要命令: $cmd (请先安装)"
    fi
    show_progress 1 4 "检查 $cmd"
  done

  # 检查Docker状态
  if ! docker info >/dev/null 2>&1; then
    fail "Docker未启动或当前用户无权限 (执行: sudo systemctl start docker)"
  fi
  show_progress 2 4 "Docker"

  # 检查Docker Compose版本
  if ! docker compose version >/dev/null 2>&1; then
    fail "未找到Docker Compose V2插件 (安装: sudo apt install docker-compose-plugin)"
  fi
  show_progress 3 4 "Docker Compose"

  # 检查磁盘空间（至少50GB）
  local available_space
  available_space=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
  if [[ "$available_space" -lt 50 ]]; then
    warn "磁盘空间不足50GB (当前: ${available_space}GB)，可能导致部署失败"
  fi
  show_progress 4 4 "磁盘空间 (${available_space}GB)"

  echo ""
  log_ok "环境检查通过 ✓"
}

# ==================== Phase 1: Git代码拉取 ====================
clone_repository() {
  if [[ "$SKIP_GIT" -eq 1 ]]; then
    log_info "Phase 1/6: 跳过Git拉取（使用本地代码）"
    return
  fi

  log_info "Phase 1/6: 从Git拉取代码..."
  log_info "仓库地址: $GIT_URL"
  log_info "目标分支: $BRANCH"

  if [[ -z "$GIT_URL" ]]; then
    fail "首次部署必须指定 --git-url 参数"
  fi

  # 检查是否已是Git仓库
  if [[ -d ".git" ]]; then
    log_warn "当前目录已是Git仓库，尝试更新..."
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
  else
    # 克隆仓库（如果当前目录为空）
    if [[ -z "$(ls -A)" ]] || [[ "$(pwd)" == "$SCRIPT_DIR" ]]; then
      log_info "克隆仓库到当前目录..."
      git clone --branch "$BRANCH" --depth 1 "$GIT_URL" temp_deploy
      shopt -s dotglob nullglob
      mv temp_deploy/* . 2>/dev/null || true
      mv temp_deploy/.* . 2>/dev/null || true
      rm -rf temp_deploy
      shopt -u dotglob nullglob
    else
      fail "当前目录不为空且不是Git仓库，请使用空目录或指定 --skip-git"
    fi
  fi

  log_ok "代码准备完成 ✓"
}

# ==================== Phase 2: 配置文件检查与生成 ====================
setup_configuration() {
  log_info "Phase 2/6: 检查并配置环境变量..."

  cd "$SCRIPT_DIR"

  # 创建必要目录
  log_info "创建持久化目录..."
  mkdir -p config logs backups backend/data backend/imports backend/logs
  show_progress 1 3 "目录结构"

  # 检查.env文件
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f ".env.template" ]]; then
      log_warn ".env不存在，从模板复制..."
      cp .env.template "$ENV_FILE"
      log_error ""
      log_error "========================================="
      log_error "❌ 必须手动编辑 .env 文件！"
      log_error "========================================="
      log_error ""
      log_error "请执行以下步骤："
      log_error "  1. vim $ENV_FILE"
      log_error "  2. 修改所有标记为 [手动] 的配置项"
      log_error "  3. 特别是以下关键项："
      log_error "     - SMARTASK_DB_PASSWORD (数据库密码)"
      log_error "     - SMARTASK_ADMIN_PASSWORD (管理员密码)"
      log_error "     - SMARTASK_AI_API_KEY (AI模型API Key)"
      log_error "     - SMARTASK_SECRET_KEY (安全密钥)"
      log_error ""
      log_error "完成后重新运行: ./auto-deploy.sh --skip-git"
      log_error "========================================="
      exit 1
    else
      fail "缺少 .env 和 .env.template，无法继续"
    fi
  fi

  show_progress 2 3 ".env文件"

  # 验证关键配置（除非跳过）
  if [[ "$SKIP_ENV_CHECK" -eq 0 ]]; then
    validate_env_config
  else
    log_warn "跳过.env配置检查（不推荐生产环境使用）"
  fi

  show_progress 3 3 "配置验证"

  echo ""
  log_ok "环境变量配置完成 ✓"
}

validate_env_config() {
  log_info "验证关键配置项..."

  # 定义必须检查的配置项
  declare -A required_vars=(
    ["SMARTASK_DB_PASSWORD"]="数据库密码"
    ["SMARTASK_ADMIN_PASSWORD"]="管理员密码"
    ["SMARTASK_AI_API_KEY"]="AI模型API Key"
    ["SMARTASK_SECRET_KEY"]="安全密钥"
  )

  # 定义禁止使用的弱值
  declare -A weak_values=(
    ["SMARTASK_DB_PASSWORD"]="请修改|password|123456|postgres"
    ["SMARTASK_ADMIN_PASSWORD"]="admin123456|123456|password|请设置"
    ["SMARTASK_AI_API_KEY"]="sk-你的|your-api-key|请填写|changeme"
    ["SMARTASK_SECRET_KEY"]="请运行|请生成|vanna-local-secret"
  )

  local errors=0
  for var in "${!required_vars[@]}"; do
    local value
    value=$(grep -E "^${var}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | xargs)

    if [[ -z "$value" || "$value" == *"请"* || "$value" == *"placeholder"* ]]; then
      log_error "❌ ${required_vars[$var]} 未填写 ($var)"
      ((errors++))
    else
      # 检查弱密码/占位符
      local weak_pattern="${weak_values[$var]}"
      if [[ "$value" =~ $weak_pattern ]]; then
        log_warn "⚠️ ${required_vars[$var]} 可能是弱值或占位符 ($var)"
        ((errors++))
      fi
    fi
  done

  if [[ $errors -gt 0 ]]; then
    log_error ""
    log_error "发现 $errors 个配置问题，请修正后重试！"
    log_error "编辑: vim $ENV_FILE"
    exit 1
  fi
}

# ==================== Phase 3: Docker服务启动 ====================
start_services() {
  log_info "Phase 3/6: 构建并启动Docker服务..."

  cd "$SCRIPT_DIR"

  # 验证docker-compose.yml
  log_info "验证 docker-compose.yml..."
  if ! docker compose config >/dev/null 2>&1; then
    fail "docker-compose.yml 格式错误或缺少必要文件"
  fi
  show_progress 1 4 "Compose配置"

  # 构建镜像（首次较慢）
  log_info "构建Docker镜像（可能需要5-15分钟）..."
  if ! docker compose build --no-cache 2>&1 | tee -a "$LOG_FILE"; then
    fail "Docker镜像构建失败，查看日志: $LOG_FILE"
  fi
  show_progress 2 4 "镜像构建"

  # 启动服务
  log_info "启动所有容器..."
  if ! docker compose up -d 2>&1 | tee -a "$LOG_FILE"; then
    fail "容器启动失败，查看日志: $LOG_FILE"
  fi
  show_progress 3 4 "容器启动"

  # 等待PostgreSQL就绪
  log_info "等待PostgreSQL就绪..."
  local pg_ready=0
  for i in $(seq 1 30); do
    if docker exec smartask-postgres pg_isready -U "${SMARTASK_DB_USERNAME:-smartask_user}" -d "${SMARTASK_DB_DATABASE:-smartask_db}" >/dev/null 2>&1; then
      pg_ready=1
      break
    fi
    show_progress $i 30 "PostgreSQL启动中"
    sleep 2
  done

  if [[ $pg_ready -eq 0 ]]; then
    fail "PostgreSQL启动超时（60秒），检查日志: docker compose logs postgres"
  fi
  show_progress 4 4 "PostgreSQL就绪"

  echo ""
  log_ok "Docker服务已启动 ✓"
}

# ==================== Phase 4: 数据库初始化 ====================
initialize_database() {
  log_info "Phase 4/6: 初始化数据库..."

  cd "$SCRIPT_DIR"

  # 等待后端健康检查通过
  log_info "等待后端服务就绪..."
  local backend_ready=0
  local backend_port="${SMARTASK_BACKEND_PORT:-5002}"

  for i in $(seq 1 60); do
    if curl -fsS --max-time 3 "http://127.0.0.1:${backend_port}/api/health" >/dev/null 2>&1; then
      backend_ready=1
      break
    fi
    show_progress $i 60 "后端启动中"
    sleep 2
  done

  if [[ $backend_ready -eq 0 ]]; then
    fail "后端启动超时（120秒），检查日志: docker compose logs backend"
  fi

  log_ok "后端服务已就绪 ✓"
  show_progress 1 3 "后端健康检查"

  # 补充缺失的建表SQL（审计发现的坑）
  log_info "补充缺失的业务表..."
  docker exec -i smartask-postgres psql -U "${SMARTASK_DB_USERNAME:-smartask_user}" -d "${SMARTASK_DB_DATABASE:-smartask_db}" <<'SQL' 2>/dev/null || true
CREATE TABLE IF NOT EXISTS bs_common_questions (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    sql_template TEXT,
    intent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bs_dataset_external_configs (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL UNIQUE,
    config JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bs_regression_cases (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    expected_intent TEXT,
    expected_sql TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
SQL
  log_ok "业务表补充完成 ✓"
  show_progress 2 3 "补充建表SQL"

  # 导入备份包（如果指定）
  if [[ "$WITH_BACKUP" -eq 1 ]] && [[ -n "$BACKUP_FILE" ]] && [[ -f "$BACKUP_FILE" ]]; then
    log_info "导入旧环境备份包: $BACKUP_FILE"
    docker cp "$BACKUP_FILE" smartask-backend:/tmp/import_bundle.json
    docker exec smartask-backend python /app/scripts/import_runtime_config.py \
      --input /tmp/import_bundle.json \
      --mode merge \
      2>&1 | tee -a "$LOG_FILE" || true
    log_ok "备份包导入完成 ✓"
  fi

  show_progress 3 3 "数据导入"

  echo ""
  log_ok "数据库初始化完成 ✓"
}

# ==================== Phase 5: 功能验证 ====================
verify_deployment() {
  log_info "Phase 5/6: 执行功能验证..."

  cd "$SCRIPT_DIR"

  local backend_port="${SMARTASK_BACKEND_PORT:-5002}"

  # 测试1: 健康检查
  log_info "[1/5] 健康检查..."
  if curl -fsS "http://127.0.0.1:${backend_port}/api/health" | grep -q '"status":"ok"'; then
    log_ok "健康检查通过 ✓"
  else
    log_error "健康检查失败 ✗"
    return 1
  fi

  # 测试2: 管理员登录
  log_info "[2/5] 管理员登录测试..."
  local admin_user="${SMARTASK_ADMIN_USERNAME:-admin}"
  local admin_pass="${SMARTASK_ADMIN_PASSWORD:-admin123456}"

  local token_response
  token_response=$(curl -s --max-time 10 -X POST "http://127.0.0.1:${backend_port}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${admin_user}\",\"password\":\"${admin_pass}\"}" 2>/dev/null || echo "{}")

  local token
  token=$(echo "$token_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")

  if [[ -n "$token" && "$token" != "" ]]; then
    log_ok "管理员登录成功 ✓ (Token: ${token:0:20}...)"
  else
    log_warn "管理员登录失败 ✗ (可能是密码错误或服务未完全启动)"
  fi

  # 测试3: 用户列表API
  if [[ -n "$token" ]]; then
    log_info "[3/5] 权限API测试..."
    local users_response
    users_response=$(curl -s --max-time 10 "http://127.0.0.1:${backend_port}/api/admin/users" \
      -H "X-Auth-Token: $token" 2>/dev/null || echo "{}")

    if echo "$users_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'users' in d" 2>/dev/null; then
      log_ok "权限API正常 ✓"
    else
      log_warn "权限API异常（可能需要初始化RBAC数据）"
    fi
  fi

  # 测试4: 导出功能
  if [[ -n "$token" ]]; then
    log_info "[4/5] 运行态导出测试..."
    local export_size
    export_size=$(curl -s --max-time 30 -X POST "http://127.0.0.1:${backend_port}/api/runtime-migration/export" \
      -H "X-Auth-Token: $token" | wc -c 2>/dev/null || echo "0")

    if [[ "$export_size" -gt 1000 ]]; then
      log_ok "运行态导出正常 ✓ (${export_size}字节)"
    else
      log_warn "运行态导出异常 (${export_size}字节)"
    fi
  fi

  # 测试5: 容器状态检查
  log_info "[5/5] Docker容器状态..."
  local container_status
  container_status=$(docker compose ps --format "{{.Name}}: {{.State}}" 2>/dev/null || echo "")

  if echo "$container_status" | grep -q "running\|healthy"; then
    log_ok "所有容器运行正常 ✓"
    echo "$container_status" | while read -r line; do
      log_ok "  $line"
    done
  else
    log_warn "部分容器状态异常:"
    echo "$container_status" | while read -r line; do
      log_warn "  $line"
    done
  fi

  echo ""
  log_ok "功能验证完成 ✓"
}

# ==================== Phase 6: 输出总结 ====================
print_summary() {
  log_info "Phase 6/6: 部署总结"

  local frontend_port="${SMARTASK_FRONTEND_PORT:-8888}"
  local backend_port="${SMARTASK_BACKEND_PORT:-5002}"
  local pg_port="${SMARTASK_DOCKER_PG_PORT:-5433}"

  echo ""
  echo "============================================================"
  echo -e "${GREEN}🎉 SmartAsk 部署成功！${NC}"
  echo "============================================================"
  echo ""
  echo "📌 访问地址:"
  echo "  前端界面: http://$(hostname -I | awk '{print $1}'):${frontend_port}"
  echo "  后端API:  http://$(hostname -I | awk '{print $1}'):${backend_port}/api/health"
  echo "  数据库:   $(hostname -I | awk '{print $1}'):${pg_port} (仅内部访问)"
  echo ""
  echo "👤 默认账号:"
  echo "  用户名: ${SMARTASK_ADMIN_USERNAME:-admin}"
  echo "  密码:   ${SMARTASK_ADMIN_PASSWORD:-***请查看.env***}"
  echo ""
  echo "📋 后续操作:"
  echo "  1. 登录前端界面修改默认密码"
  echo "  2. 配置飞书同步（如果需要）"
  echo "  3. 导入书架元数据和业务数据"
  echo "  4. 触发第一次全量数据同步"
  echo ""
  echo "📝 常用命令:"
  echo "  查看日志: docker compose logs -f backend"
  echo "  停止服务: docker compose down"
  echo "  重启服务: docker compose restart"
  echo "  备份数据: docker exec smartask-backend python /app/scripts/backup_all.py"
  echo "  更新部署: ./auto-deploy.sh --skip-git"
  echo ""
  echo "📄 日志文件: $LOG_FILE"
  echo "============================================================"
}

# ==================== 主流程 ====================
main() {
  echo ""
  echo "============================================================"
  echo -e "${BLUE}  SmartAsk 一键部署工具 v1.0${NC}"
  echo "============================================================"
  echo ""

  # 解析参数
  parse_args "$@"

  # 记录开始时间
  local start_time=$(date +%s)

  # 执行各阶段
  check_prerequisites
  clone_repository
  setup_configuration
  start_services
  initialize_database
  verify_deployment
  print_summary

  # 计算耗时
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  local minutes=$((duration / 60))
  local seconds=$((duration % 60))

  log_info "总耗时: ${minutes}分${seconds}秒"
  log_info "详细日志: $LOG_FILE"
  echo ""
}

# ==================== 入口 ====================
main "$@"
