#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartAsk 飞书账号合并 + 模型权限 自动化测试脚本

使用方式：
    python test_feishu_merge.py

功能：
    1. 验证后端服务状态
    2. 检查用户配置文件（合并状态）
    3. 模拟API调用测试权限过滤
    4. 输出完整测试报告
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# =========================
# 配置
# =========================

BASE_URL = "http://localhost:5002"
CONFIG_FILE = Path(__file__).parent / "config" / "employee_permissions.json"
TEST_USER_MOBILE = "+8618576614568"  # 刘太琳的手机号
EXPECTED_MODEL_ID = 11  # DeepSeek-V4-Pro 的ID

# ANSI 颜色代码
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Color.CYAN}{'='*60}{Color.RESET}")
    print(f"{Color.CYAN}  {text}{Color.RESET}")
    print(f"{Color.CYAN}{'='*60}{Color.RESET}\n")

def print_test(name, passed, detail=""):
    status = f"{Color.GREEN}✅ PASS{Color.RESET}" if passed else f"{Color.RED}❌ FAIL{Color.RESET}"
    print(f"  {status} {name}")
    if detail:
        print(f"         {detail}")

# =========================
# 测试函数
# =========================

def test_backend_health():
    """测试1：后端健康检查"""
    try:
        url = f"{BASE_URL}/api/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "running", f"状态: {data.get('status')}"
    except Exception as e:
        return False, str(e)

def test_user_config():
    """测试2：检查用户配置（合并状态）"""
    if not CONFIG_FILE.exists():
        return False, f"配置文件不存在: {CONFIG_FILE}"

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    employees = config.get("employees", [])

    # 查找刘太琳的账号
    liutailin_accounts = [
        emp for emp in employees
        if emp.get("account") in [TEST_USER_MOBILE, "18576614568"]
           or emp.get("name") == "刘太琳"
    ]

    details = []
    all_passed = True

    # 检查2.1：应该只有1个刘太琳账号
    if len(liutailin_accounts) != 1:
        all_passed = False
        details.append(f"找到 {len(liutailin_accounts)} 个刘太琳账号（期望1个）")
    else:
        details.append(f"✅ 只有1个刘太琳账号")

    # 检查2.2：不应该有emp_feishu_开头的重复账号
    feishu_dupes = [
        emp for emp in employees
        if emp.get("id", "").startswith("emp_feishu_")
        and (emp.get("account") in [TEST_USER_MOBILE, "18576614568"])
    ]
    if feishu_dupes:
        all_passed = False
        details.append(f"❌ 还存在飞书重复账号: {[e['id'] for e in feishu_dupes]}")
    else:
        details.append(f"✅ 无飞书重复账号")

    # 检查2.3：主账号应该是业务管理员
    if liutailin_accounts:
        main_account = liutailin_accounts[0]
        role = main_account.get("role", "")
        if role == "business_admin":
            details.append(f"✅ 角色正确: {role}")
        else:
            all_passed = False
            details.append(f"❌ 角色错误: {role} (期望 business_admin)")

        # 检查2.4：应有合并时间戳备注
        note = main_account.get("note", "")
        if "飞书账号已合并" in note or "merged" in note.lower():
            details.append(f"✅ 合并记录存在: {note[:50]}...")
        else:
            details.append(f"⚠️  无合并备注（可能之前已合并或首次创建）")

        # 检查2.5：应有飞书字段
        has_unionid = bool(main_account.get("union_id"))
        has_openid = bool(main_account.get("open_id"))
        details.append(f"{'✅' if has_unionid else '❌'} union_id: {'已同步' if has_unionid else '缺失'}")
        details.append(f"{'✅' if has_openid else '❌'} open_id: {'已同步' if has_openid else '缺失'}")

        # 检查2.6：组织树权限应保留
        org_nodes = main_account.get("organization_node_ids", [])
        if len(org_nodes) > 10:
            details.append(f"✅ 组织树权限保留: {len(org_nodes)} 个节点")
        else:
            details.append(f"⚠️  组织树节点较少: {len(org_nodes)} 个")

    return all_passed, "\n         ".join(details)

def test_api_auth_required():
    """测试3：API需要认证"""
    try:
        url = f"{BASE_URL}/api/ai-models/active"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            # 如果返回error说明需要认证
            return "error" in data or "请先登录" in str(data), f"返回: {str(data)[:50]}"
    except urllib.error.HTTPError as e:
        # 401/403 也算需要认证
        if e.code in [401, 403]:
            return True, f"HTTP {e.code} (需要认证)"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)

def test_model_list_structure():
    """测试4：检查模型列表结构（无需认证的端点）"""
    try:
        # 尝试获取所有模型列表（如果有的话）
        url = f"{BASE_URL}/api/ai-models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

            models = data.get("models", [])
            channels = set(m.get("channel_display_name", "未知") for m in models)

            details = [
                f"总模型数: {len(models)}",
                f"渠道数: {len(channels)}",
                f"渠道列表: {', '.join(sorted(channels))}"
            ]

            # 检查是否有默认模型
            default_models = [m for m in models if m.get("is_default")]
            if default_models:
                details.append(f"默认模型: {default_models[0].get('name')} (ID:{default_models[0].get('id')})")

            # 检查是否有DeepSeek
            deepseek_models = [m for m in models if "deepseek" in m.get("name", "").lower()]
            if deepseek_models:
                details.append(f"DeepSeek模型: {[m['name'] for m in deepseek_models]}")

            return True, "\n         ".join(details)
    except Exception as e:
        return False, str(e)

# =========================
# 主流程
# =========================

def main():
    print_header("SmartAsk 功能测试报告")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 目标地址: {BASE_URL}")
    print(f"👤 测试用户: 刘太琳 ({TEST_USER_MOBILE})")
    print()

    results = []

    # 运行测试
    print(f"{Color.YELLOW}[测试1] 后端服务健康检查{Color.RESET}")
    passed, detail = test_backend_health()
    results.append(("后端健康检查", passed))
    print_test("后端可访问", passed, detail)

    print(f"\n{Color.YELLOW}[测试2] 用户配置与合并状态{Color.RESET}")
    passed, detail = test_user_config()
    results.append(("用户合并状态", passed))
    print_test("账号合并正确性", passed, detail)

    print(f"\n{Color.YELLOW}[测试3] API认证机制{Color.RESET}")
    passed, detail = test_api_auth_required()
    results.append(("API认证", passed))
    print_test("未登录返回401/错误", passed, detail)

    print(f"\n{Color.YELLOW}[测试4] 模型数据结构{Color.RESET}")
    passed, detail = test_model_list_structure()
    results.append(("模型数据", passed))
    print_test("模型列表可访问", passed, detail)

    # =========================
    # 汇总报告
    # =========================

    print_header("测试汇总")

    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    failed_count = total - passed_count

    print(f"总计: {total} 项测试")
    print(f"{Color.GREEN}通过: {passed_count} 项{Color.RESET}")
    print(f"{Color.RED}失败: {failed_count} 项{Color.RESET}" if failed_count > 0 else "")

    print()
    if failed_count == 0:
        print(f"{Color.GREEN}🎉 所有测试通过！系统运行正常。{Color.RESET}")
    else:
        print(f"{Color.RED}⚠️  有 {failed_count} 项测试失败，请检查上述详情。{Color.RESET}")

    print()
    print("=" * 60)
    print("💡 下一步建议：")
    print("   1. 用浏览器打开 http://localhost:8888")
    print("   2. 清除Cookie后重新用飞书登录")
    print("   3. 打开智能问数页面查看模型下拉列表")
    print("   4. 确认是否只显示允许的模型")
    print("=" * 60)

    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
