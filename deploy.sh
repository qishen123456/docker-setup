#!/bin/bash
# =========================
# SmartAsk 部署切换脚本（支持自动环境检测）
# 用途：快速在本地开发 / 生产环境之间切换
#
# 使用方式：
#   ./deploy.sh              # 自动检测环境并提示推荐模式
#   ./deploy.sh local        # 切换到本地开发模式
#   ./deploy.sh production   # 切换到生产环境模式（Docker内部Nginx）
#   ./deploy.sh proxy        # 切换到外部代理模式（推荐！适用于已有外部Nginx/负载均衡）
#   ./deploy.sh status       # 查看当前模式和容器状态
#
# 环境检测逻辑：
#   Linux   → 服务器环境（推荐proxy模式）
#   Windows → 测试环境（推荐local模式）
#   macOS   → 开发环境（推荐local模式）
# =========================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# =========================
# 自动环境检测
# =========================
detect_environment() {
  local os_name os_type recommend_mode

  case "$(uname -s)" in
    Linux*)
      os_name="Linux"
      os_type="server"
      # 进一步判断是否为WSL（Windows Subsystem for Linux）
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

# 获取当前模式
get_current_mode() {
    if [ -f .env ]; then
        grep -q "^DEPLOY_MODE=production" .env && echo "production" || echo "local"
    else
        echo "未配置"
    fi
}

# 打印状态（增强版：包含环境检测信息）
print_status() {
    current=$(get_current_mode)
    echo -e "\n${CYAN}============================================${NC}"
    echo -e "${CYAN}  SmartAsk 部署状态面板${NC}"
    echo -e "${CYAN}============================================${NC}"

    # 环境信息
    echo -e "\n${YELLOW}📌 环境检测：${NC}"
    echo -e "  操作系统：${OS_NAME}"
    echo -e "  环境类型：${OS_TYPE}"
    if [[ "${RECOMMEND_MODE}" != "${current:-}" ]]; then
      echo -e "  推荐模式：${GREEN}${RECOMMEND_MODE}${NC} ${YELLOW}(当前: ${current:-未配置})${NC}"
    else
      echo -e "  推荐模式：${GREEN}${RECOMMEND_MODE}${NC} ✅"
    fi

    # 当前部署模式
    echo -e "\n${YELLOW}📋 当前部署模式：${NC}"
    case "${current}" in
      local)
        echo -e "  模式：${GREEN}本地开发模式${NC}"
        echo -e "  后端端口：5002（直接访问）"
        echo -e "  前端端口：8888（直接访问）"
        echo -e "  Nginx：未启用"
        ;;
      production)
        echo -e "  模式：${GREEN}生产环境模式（Docker内Nginx）${NC}"
        echo -e "  访问方式：通过 Docker 内 Nginx 单端口代理"
        ;;
      proxy)
        echo -e "  模式：${GREEN}外部代理模式（推荐用于服务器）${NC}"
        echo -e "  访问地址：$(grep '^PUBLIC_PROTOCOL=' .env 2>/dev/null | cut -d= -f2)://$(grep '^PUBLIC_DOMAIN=' .env 2>/dev/null | cut -d= -f2):$(grep '^PUBLIC_PORT=' .env 2>/dev/null | cut -d= -f2)$(grep '^BASE_PATH=' .env 2>/dev/null | cut -d= -f2)"
        echo -e "  后端API：对外暴露 :5002（供外部Nginx转发）"
        echo -e "  前端页面：对外暴露 :8888（供外部Nginx转发）"
        ;;
      *)
        echo -e "  模式：${RED}未配置${NC}"
        ;;
    esac

    # 详细环境变量
    if [ -f .env ]; then
        echo -e "\n${YELLOW}⚙️  配置详情：${NC}"
        echo -e "  DEPLOY_MODE=${current:-未设置}"
        echo -e "  BACKEND_URL=$(grep '^BACKEND_URL=' .env | cut -d= -f2)"
        echo -e "  FRONTEND_URL=$(grep '^FRONTEND_URL=' .env | cut -d= -f2)"
        if grep -q '^PUBLIC_DOMAIN=' .env; then
          echo -e "  PUBLIC_DOMAIN=$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)"
        fi
    fi

    # Docker容器状态
    echo -e "\n${YELLOW}🐳 Docker 容器状态：${NC}"
    if command -v docker-compose &> /dev/null; then
        docker-compose ps 2>/dev/null || echo "  Docker Compose 未运行或未安装"
    else
        echo "  未找到 docker-compose 命令"
    fi

    echo ""
}

# 切换到本地模式
switch_to_local() {
    echo -e "\n${GREEN}>>> 切换到本地开发模式...${NC}\n"

    # 备份当前 .env
    if [ -f .env ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "  ${YELLOW}已备份当前 .env 文件${NC}"
    fi

    # 复制本地配置
    cp .env.local .env

    # 确保端口暴露（取消注释 docker-compose.yml 中的 ports）
    sed -i 's/^\(\s*\)#\(\s*ports:\)/\1\2/' docker-compose.yml 2>/dev/null || true

    echo -e "  ${GREEN}✓ 已应用本地配置${NC}"
    echo -e "  ${GREEN}✓ 后端端口：5002（直接访问）${NC}"
    echo -e "  ${GREEN}✓ 前端端口：8888（直接访问）${NC}"
    echo -e "  ${GREEN}✓ Nginx：未启用${NC}"

    echo -e "\n${BLUE}启动命令：docker-compose up -d --build${NC}\n"
}

# 切换到生产模式（Docker内部Nginx）
switch_to_production() {
    echo -e "\n${GREEN}>>> 切换到生产环境模式（Docker内部Nginx）...${NC}\n"

    # 检查是否已配置域名
    if ! grep -q "^PUBLIC_DOMAIN=" .env.production || grep -q "^PUBLIC_DOMAIN=your-domain.com$" .env.production; then
        echo -e "${RED}错误：请先修改 .env.production 中的 PUBLIC_DOMAIN！${NC}"
        exit 1
    fi

    # 备份当前 .env
    if [ -f .env ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "  ${YELLOW}已备份当前 .env 文件${NC}"
    fi

    # 复制生产配置
    cp .env.production .env

    echo -e "  ${GREEN}✓ 已应用生产配置${NC}"
    echo -e "  ${GREEN}✅ 公网域名：$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)${NC}"
    echo -e "  ${GREEN}✅ 后端 API：通过 Docker内Nginx 代理${NC}"
    echo -e "  ${GREEN}✅ 前端页面：通过 Docker内Nginx 代理${NC}"
    echo -e "  ${GREEN}✅ Nginx：Docker容器内启动${NC}"

    echo -e "\n${BLUE}启动命令：${NC}"
    echo -e "  docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build"
    echo ""
}

# 切换到外部代理模式（推荐！适用于已有外部Nginx/负载均衡）
switch_to_proxy() {
    echo -e "\n${GREEN}>>> 切换到外部代理模式...${NC}\n"
    echo -e "  ${BLUE}适用场景：已有外部Nginx/负载均衡处理HTTPS和路径前缀${NC}\n"

    # 检查是否已配置域名
    if ! grep -q "^PUBLIC_DOMAIN=" .env.production || grep -q "^PUBLIC_DOMAIN=your-domain.com$" .env.production; then
        echo -e "${RED}错误：请先修改 .env.production 中的 PUBLIC_DOMAIN！${NC}"
        exit 1
    fi

    # 备份当前 .env
    if [ -f .env ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "  ${YELLOW}已备份当前 .env 文件${NC}"
    fi

    # 复制生产配置
    cp .env.production .env

    domain=$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)
    port=$(grep '^PUBLIC_PORT=' .env | cut -d= -f2)
    base_path=$(grep '^BASE_PATH=' .env | cut -d= -f2)

    echo -e "  ${GREEN}✓ 已应用生产配置${NC}"
    echo -e "  ${GREEN}✅ 公网地址：$(grep '^PUBLIC_PROTOCOL=' .env | cut -d= -f2)://${domain}:${port}${base_path}${NC}"
    echo -e "  ${GREEN}✅ 后端 API：对外暴露 :5002（供外部Nginx转发）${NC}"
    echo -e "  ${GREEN}✅ 前端页面：对外暴露 :8888（供外部Nginx转发）${NC}"
    echo -e "  ${GREEN}✅ Docker内Nginx：已禁用（使用外部代理）${NC}"

    echo -e "\n${YELLOW}⚠️  重要提示：${NC}"
    echo -e "  请确保外部Nginx已正确配置 /smart-ask/ 和 /smart-ask/api/ 的转发"
    echo -e "  详细配置见 DEPLOY_TO_SERVER.md"
    echo ""

    echo -e "${BLUE}启动命令：${NC}"
    echo -e "  docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build"
    echo ""
}

# 主逻辑（支持无参数时自动提示）
case "${1:-auto}" in
    local|dev)
        switch_to_local
        ;;
    production|prod)
        switch_to_production
        ;;
    proxy|external)
        switch_to_proxy
        ;;
    status|st|s)
        print_status
        ;;
    auto|"")
        # 无参数时显示环境检测信息并推荐模式
        print_status

        echo -e "${CYAN}💡 快速操作：${NC}"
        echo -e ""

        case "${OS_TYPE}" in
          server)
            echo -e "  检测到 ${GREEN}服务器环境${NC}，推荐使用外部代理模式："
            echo -e "    ${CYAN}./deploy.sh proxy${NC}"
            echo -e ""
            echo -e "  或使用一键更新脚本："
            echo -e "    ${CYAN}bash update.sh${NC} （自动备份+重启）"
            echo -e ""
            ;;
          windows)
            echo -e "  检测到 ${GREEN}Windows测试环境${NC}，推荐使用本地开发模式："
            echo -e "    ${CYAN}./deploy.sh local${NC}"
            echo -e ""
            echo -e "  启动服务："
            echo -e "    ${CYAN}docker-compose up -d --build${NC}"
            echo -e ""
            ;;
          development)
            echo -e "  检测到 ${GREEN}macOS开发环境${NC}，推荐使用本地开发模式："
            echo -e "    ${CYAN}./deploy.sh local${NC}"
            echo -e ""
            ;;
          *)
            echo -e "  请手动选择部署模式："
            echo -e "    ${CYAN}./deploy.sh local${NC}       # 本地开发"
            echo -e "    ${CYAN}./deploy.sh production${NC}  # 生产环境（Docker内Nginx）"
            echo -e "    ${CYAN}./deploy.sh proxy${NC}       # 外部代理模式（服务器）"
            echo -e ""
            ;;
        esac

        echo -e "${YELLOW}其他命令：${NC}"
        echo -e "  ./deploy.sh status     # 查看详细状态"
        echo -e "  ./deploy.sh --help     # 显示帮助信息"
        echo -e ""
        ;;
    -h|--help)
        cat <<'HELPEOF'
${CYAN}
╔══════════════════════════════════════════════════════════════╗
║           SmartAsk 部署切换脚本 - 使用帮助                   ║
╚══════════════════════════════════════════════════════════════╝
${NC}

${YELLOW}基本用法：${NC}
  ./deploy.sh [命令]

${YELLOW}可用命令：${NC}
  ${GREEN}local${NC}         切换到本地开发模式（Windows/macOS推荐）
                    - 后端:5002 + 前端:8888 直连访问
                    - 不启用Nginx

  ${GREEN}production${NC}    切换到生产环境模式（Docker内部Nginx）
                    - 仅Nginx对外暴露单端口
                    - 适用于无外部负载均衡的场景

  ${GREEN}proxy${NC}         切换到外部代理模式（Linux服务器推荐 ⭐）
                    - backend/frontend端口对外暴露
                    - 由外部Nginx/负载均衡处理HTTPS和路径前缀
                    - 适用于你的场景：https://bifine.angelgroup.com.cn:10899/smart-ask

  ${GREEN}status${NC}        查看当前模式和容器状态（增强版状态面板）

  ${GREEN}(无参数)${NC}      自动检测环境并推荐最佳模式

${YELLOW}示例：${NC}
  # Windows测试环境
  ./deploy.sh local && docker-compose up -d --build

  # Linux服务器部署
  ./deploy.sh proxy
  docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build

  # 查看状态
  ./deploy.sh status

${YELLOW}环境检测逻辑：${NC}
  • Linux   → 识别为服务器 → 推荐 proxy 模式
  • Windows → 识别为测试环境 → 推荐 local 模式
  • macOS   → 识别为开发环境 → 推荐 local 模式
  • WSL     → 识别为Windows子系统 → 推荐 local 模式

${YELLOW}相关文件：${NC}
  • .env.local              本地开发环境变量
  • .env.production         生产环境变量（已配置公网地址）
  • docker-compose.proxy.yml 外部代理模式配置
  • DEPLOY_TO_SERVER.md     服务器部署详细指南
  • NGINX_DEPLOYMENT.md     Nginx配置完整指南

HELPEOF
        ;;
    *)
        echo -e "\n${RED}未知命令: $1${NC}\n"
        echo -e "用法：$0 {local|production|proxy|status|--help}${NC}\n"
        echo -e "  ${BLUE}local${NC}       - 本地开发模式（端口直连）"
        echo -e "  ${BLUE}production${NC}  - 生产环境模式（Docker内Nginx）"
        echo -e "  ${BLUE}proxy${NC}      - 外部代理模式（服务器推荐 ⭐）"
        echo -e "  ${BLUE}status${NC}      - 查看当前模式和容器状态"
        echo -e "  ${BLUE}(无参数)${NC}    - 自动检测环境并推荐"
        echo ""
        exit 1
        ;;
esac
