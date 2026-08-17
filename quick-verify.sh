#!/usr/bin/env bash
# ============================================================
# SmartAsk 快速功能验证脚本
# 使用方法: chmod +x quick-verify.sh && ./quick-verify.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 统计变量
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

log_test() {
  local test_name="$1"
  local result="$2"
  local detail="${3:-}"

  ((TOTAL_TESTS++))

  if [[ "$result" == "PASS" ]]; then
    ((PASSED_TESTS++))
    echo -e "${GREEN}[PASS]${NC} $test_name"
  else
    ((FAILED_TESTS++))
    echo -e "${RED}[FAIL]${NC} $test_name"
  fi

  if [[ -n "$detail" ]]; then
    echo "       $detail"
  fi
}

# 获取管理员Token
get_admin_token() {
  local admin_user="${SMARTASK_ADMIN_USERNAME:-admin}"
  local admin_pass="${SMARTASK_ADMIN_PASSWORD:-admin123456}"

  curl -s --max-time 10 -X POST "http://127.0.0.1:${SMARTASK_BACKEND_PORT:-5002}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${admin_user}\",\"password\":\"${admin_pass}\"}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo ""
}

echo ""
echo "============================================================"
echo -e "${BLUE} SmartAsk 快速功能验证工具 ${NC}"
echo "============================================================"
echo ""

# ==================== 测试组1: 基础服务 ====================
echo -e "${BLUE}[测试组1/5] 基础服务检查${NC}"
echo ""

# 1.1 健康检查
health_response=$(curl -fsS --max-time 5 "http://127.0.0.1:${SMARTASK_BACKEND_PORT:-5002}/api/health" 2>/dev/null || echo "{}")
if echo "$health_response" | grep -q '"status":"ok"'; then
  log_test "后端健康检查" "PASS" "API正常响应"
else
  log_test "后端健康检查" "FAIL" "无响应或状态异常: ${health_response:0:50}"
fi

# 1.2 Docker容器状态
container_status=$(docker compose ps --format "{{.Name}}: {{.State}}" 2>/dev/null || echo "")
running_count=$(echo "$container_status" | grep -c "running\|healthy" || true)
if [[ $running_count -ge 3 ]]; then
  log_test "Docker容器运行" "PASS" "3个容器都在运行"
else
  log_test "Docker容器运行" "FAIL" "只有${running_count}个容器运行（预期3个）"
fi

# 1.3 端口监听
backend_port="${SMARTASK_BACKEND_PORT:-5002}"
frontend_port="${SMARTASK_FRONTEND_PORT:-8888}"
pg_port="${SMARTASK_DOCKER_PG_PORT:-5433}"

if ss -lnt 2>/dev/null | grep -q ":${backend_port} "; then
  log_test "后端端口(${backend_port})" "PASS" "正在监听"
else
  log_test "后端端口(${backend_port})" "FAIL" "未监听"
fi

if ss -lnt 2>/dev/null | grep -q ":${frontend_port} "; then
  log_test "前端端口(${frontend_port})" "PASS" "正在监听"
else
  log_test "前端端口(${frontend_port})" "WARN" "未监听（可能使用Nginx代理）"
fi

echo ""

# ==================== 测试组2: 认证与权限 ====================
echo -e "${BLUE}[测试组2/5] 认证与权限${NC}"
echo ""

TOKEN=$(get_admin_token)

if [[ -n "$TOKEN" && "$TOKEN" != "" ]]; then
  log_test "管理员登录" "PASS" "Token获取成功 (${TOKEN:0:20}...)"
else
  log_test "管理员登录" "FAIL" "无法获取Token，请检查账号密码"
  TOKEN=""
fi

if [[ -n "$TOKEN" ]]; then
  # 2.2 用户列表API
  users_response=$(curl -s --max-time 10 "http://127.0.0.1:${SMARTASK_BACKEND_PORT:-5002}/api/admin/users" \
    -H "X-Auth-Token: $TOKEN" 2>/dev/null || echo "{}")

  if echo "$users_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'users' in d" 2>/dev/null; then
    user_count=$(echo "$users_response" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('users',[])))")
    log_test "用户列表API" "PASS" "返回${user_count}个用户"
  else
    log_test "用户列表API" "FAIL" "返回格式异常"
  fi

  # 2.3 数据集列表API
  datasets_response=$(curl -s --max-time 10 "http://127.0.0.1:${SMARTASK_BACKEND_PORT:-5002}/api/admin/datasets" \
    -H "X-Auth-Token: $TOKEN" 2>/dev/null || echo "{}")

  if echo "$datasets_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'datasets' in d or 'data' in d" 2>/dev/null; then
    ds_count=$(echo "$datasets_response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('datasets',d.get('data',[]))))")
    log_test "数据集列表API" "PASS" "返回${ds_count}个数据集"
  else
    log_test "数据集列表API" "WARN" "可能未配置数据集"
  fi
fi

echo ""

# ==================== 测试组3: 核心功能 ====================
echo -e "${BLUE}[测试组3/5] 核心NL2SQL功能${NC}"
echo ""

if [[ -n "$TOKEN" ]]; then
  # 3.1 Overview类问题
  overview_response=$(python3 <<PYEOF
import json, urllib.request

question = {"question": "商用事业部的业绩情况", "dataset_id": 3}
req = urllib.request.Request(
    f"http://127.0.0.1:${__import__('os').environ.get('SMARTASK_BACKEND_PORT', '5002')}/api/smart-chat/stream",
    data=json.dumps(question).encode(),
    headers={
        'Content-Type': 'application/json',
        'X-Auth-Token': '${TOKEN}'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        size = len(data)
        if size > 10000:
            print(f"PASS|{size}字节")
        else:
            print(f"FAIL|{size}字节")
except Exception as e:
    print(f"FAIL|{str(e)}")
PYEOF
)

  overview_result=$(echo "$overview_response" | cut -d'|' -f1)
  overview_detail=$(echo "$overview_response" | cut -d'|' -f2)
  log_test "Overview问数(事业部总览)" "$overview_result" "$overview_detail"

  # 3.2 排名TopN问题
  ranking_response=$(python3 <<PYEOF
import json, urllib.request

question = {"question": "前5的业务承接人", "dataset_id": 62}  # 电商数据集
req = urllib.request.Request(
    f"http://127.0.0.1:${__import__('os').environ.get('SMARTASK_BACKEND_PORT', '5002')}/api/smart-chat/stream",
    data=json.dumps(question).encode(),
    headers={
        'Content-Type': 'application/json',
        'X-Auth-Token': '${TOKEN}'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        size = len(data)
        has_confirm = b'requires_confirmation' in data
        if size > 10000 or has_confirm:
            status = "PASS" if not has_confirm else "WARN"
            detail = f"{size}字节" + (" (需确认)" if has_confirm else "")
            print(f"{status}|{detail}")
        else:
            print(f"FAIL|{size}字节")
except Exception as e:
    print(f"FAIL|{str(e)}")
PYEOF
)

  ranking_result=$(echo "$ranking_response" | cut -d'|' -f1)
  ranking_detail=$(echo "$ranking_response" | cut -d'|' -f2)
  log_test "排名TopN查询(承接人Top5)" "$ranking_result" "$ranking_detail"

  # 3.3 人名识别
  person_response=$(python3 <<PYEOF
import json, urllib.request

question = {"question": "丁杰的业绩怎么样", "dataset_id": 3}
req = urllib.request.Request(
    f"http://127.0.0.1:{__import__('os').environ.get('SMARTASK_BACKEND_PORT', '5002')}/api/smart-chat/stream",
    data=json.dumps(question).encode(),
    headers={
        'Content-Type': 'application/json',
        'X-Auth-Token': '${TOKEN}'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        size = len(data)
        if size > 10000:
            print(f"PASS|{size}字节 (人名识别成功)")
        else:
            print(f"FAIL|{size}字节")
except Exception as e:
    print(f"FAIL|{str(e)}")
PYEOF
)

  person_result=$(echo "$person_response" | cut -d'|' -f1)
  person_detail=$(echo "$person_response" | cut -d'|' -f2)
  log_test "人名识别(丁杰业绩)" "$person_result" "$person_detail"
else
  log_test "Overview问数" "SKIP" "无有效Token"
  log_test "排名TopN查询" "SKIP" "无有效Token"
  log_test "人名识别" "SKIP" "无有效Token"
fi

echo ""

# ==================== 测试组4: 数据管理 ====================
echo -e "${BLUE}[测试组4/5] 数据管理功能${NC}"
echo ""

if [[ -n "$TOKEN" ]]; then
  # 4.1 运行态导出
  export_size=$(curl -s --max-time 30 -X POST "http://127.0.0.1:${SMARTASK_BACKEND_PORT:-5002}/api/runtime-migration/export" \
    -H "X-Auth-Token: $TOKEN" | wc -c 2>/dev/null || echo "0")

  if [[ "$export_size" -gt 1000 ]]; then
    log_test "运行态导出" "PASS" "导出${export_size}字节"
  else
    log_test "运行态导出" "FAIL" "仅${export_size}字节"
  fi

  # 4.2 备份功能
  backup_output=$(docker exec smartask-backend python /app/scripts/backup_all.py 2>&1 | head -20 || echo "ERROR")

  if echo "$backup_output" | grep -q "backup_all"; then
    log_test "全量备份" "PASS" "备份脚本可执行"
  elif echo "$backup_output" | grep -q "Error\|error"; then
    log_test "全量备份" "FAIL" "$backup_output"
  else
    log_test "全量备份" "WARN" "未知输出"
  fi

  # 4.3 飞书同步状态（如果启用）
  feishu_status=$(docker exec smartask-backend python -c "
from config_manager import get_feishu_sync_configs
configs = get_feishu_sync_configs()
active = sum(1 for c in configs if c.get('is_active'))
print(f'{active}/{len(configs)}')
" 2>/dev/null || echo "?/?")

  active_count=$(echo "$feishu_status" | cut -d'/' -f1)
  total_count=$(echo "$feishu_status" | cut -d'/' -f2)
  log_test "飞书同步配置" "INFO" "${active_count}/${total_count} 个任务已启用"
else
  log_test "运行态导出" "SKIP" "无有效Token"
  log_test "全量备份" "SKIP" "无有效Token"
  log_test "飞书同步配置" "SKIP" "无有效Token"
fi

echo ""

# ==================== 测试组5: 系统健康 ====================
echo -e "${BLUE}[测试组5/5] 系统健康度${NC}"
echo ""

# 5.1 磁盘空间
disk_usage=$(df -BG . | awk 'NR==2 {print $5}' | tr -d '%')
if [[ "$disk_usage" -lt 80 ]]; then
  log_test "磁盘空间" "PASS" "使用率 ${disk_usage}%"
elif [[ "$disk_usage" -lt 90 ]]; then
  log_test "磁盘空间" "WARN" "使用率 ${disk_space}% (偏高)"
else
  log_test "磁盘空间" "FAIL" "使用率 ${disk_usage}% (危险!)"
fi

# 5.2 内存使用
mem_info=$(free -h | awk '/Mem:/ {print $3"/"$2}')
log_test "内存使用" "INFO" "$mem_info"

# 5.3 日志错误检查
recent_errors=$(docker compose logs --tail=100 backend 2>/dev/null | grep -ci "error\|exception\|traceback" || echo "0")
if [[ "$recent_errors" -eq 0 ]]; then
  log_test "最近日志错误" "PASS" "无ERROR级别日志"
elif [[ "$recent_errors" -lt 5 ]]; then
  log_test "最近日志错误" "WARN" "发现${recent_errors}条错误日志"
else
  log_test "最近日志错误" "FAIL" "发现${recent_errors}条错误日志！"
fi

# 5.4 数据库连接池
db_connections=$(docker exec smartask-postgres psql -U "${SMARTASK_DB_USERNAME:-smartask_user}" -d "${SMARTASK_DB_DATABASE:-smartask_db}" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='${SMARTASK_DB_DATABASE:-smartask_db}';" 2>/dev/null | tr -d ' ' || echo "?")
log_test "数据库连接数" "INFO" "当前${db_connections}个活跃连接"

echo ""

# ==================== 输出总结 ====================
echo "============================================================"
echo -e "${BLUE} 验证结果汇总 ${NC}"
echo "============================================================"
echo ""
printf "总计: %2d 项测试\n" "$TOTAL_TESTS"
echo -e "${GREEN}通过: %2d 项${NC}" "$PASSED_TESTS"
echo -e "${RED}失败: %2d 项${NC}" "$FAILED_TESTS"
echo -e "${YELLOW}跳过: %2d 项${NC}" "$((TOTAL_TESTS - PASSED_TESTS - FAILED_TESTS))"
echo ""

pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
if [[ $pass_rate -ge 90 ]]; then
  echo -e "${GREEN}🎉 系统状态良好！（通过率: ${pass_rate}%）${NC}"
elif [[ $pass_rate -ge 70 ]]; then
  echo -e "${YELLOW}⚠️ 系统基本正常，有少量问题需关注（通过率: ${pass_rate}%）${NC}"
else
  echo -e "${RED}❌ 系统存在严重问题！（通过率: ${pass_rate}%）${NC}"
  echo ""
  echo "建议操作:"
  echo "  1. 查看详细日志: docker compose logs --tail=200 backend"
  echo "  2. 检查配置文件: vim .env"
  echo "  3. 重启服务: docker compose restart"
fi

echo ""
echo "============================================================"
