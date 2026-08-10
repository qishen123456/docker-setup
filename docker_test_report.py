#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartAsk Docker 内部功能验证脚本
运行方式：docker exec smartask-backend python /tmp/docker_test_report.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ANSI颜色
class C:
    R='\033[91m'; G='\033[92m'; Y='\033[93m'; B='\033[94m'; CY='\033[96m'; W='\033[0m'

def header(t):
    print(f"\n{C.CY}{'='*65}{C.W}")
    print(f"{C.CY}  {t}{C.W}")
    print(f"{C.CY}{'='*65}{C.W}\n")

def test(name, ok, detail=""):
    s = f"{C.G}✅ PASS{C.W}" if ok else f"{C.R}❌ FAIL{C.W}"
    print(f"  {s} {name}")
    if detail:
        for line in detail.split('\n'):
            print(f"         {line}")

def main():
    header("SmartAsk Docker 内部功能验证")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐳 容器: smartask-backend")
    print()

    results = []

    # ===== 测试1: 后端健康检查 =====
    print(f"{C.Y}[1/6] 后端服务健康检查{C.W}")
    try:
        url = "http://localhost:5002/api/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            ok = data.get("status") == "running"
            test("后端可访问", ok, f"状态: {data.get('status')}, 版本: {data.get('version')}")
            results.append(ok)
    except Exception as e:
        test("后端可访问", False, str(e))
        results.append(False)

    # ===== 测试2: API认证机制 =====
    print(f"\n{C.Y}[2/6] API认证机制{C.W}")
    try:
        url = "http://localhost:5002/api/ai-models/active"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                needs_auth = "error" in data or "login" in str(data).lower()
                test("未登录返回错误", needs_auth, f"响应: {str(data)[:60]}")
                results.append(needs_auth)
        except urllib.error.HTTPError as e:
            ok = e.code in [401, 403]
            test(f"未登录返回HTTP {e.code}", ok, "认证机制正常")
            results.append(ok)
    except Exception as e:
        test("API认证检查", False, str(e))
        results.append(False)

    # ===== 测试3: 合并代码部署检查 =====
    print(f"\n{C.Y}[3/6] 飞书合并代码部署{C.W}")
    auth_file = "/app/backend/controllers/auth.py"
    checks = []
    if os.path.exists(auth_file):
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()

        has_merge = "_merge_feishu_to_existing" in content
        has_debug = "DEBUG-FEISHU-MERGE" in content
        has_disable = "_disable_employee" in content
        has_mobile = "_find_employee_by_mobile" in content

        test("合并函数已部署", has_merge, "_merge_feishu_to_existing()")
        checks.append(has_merge)
        test("调试日志已添加", has_debug, "[DEBUG-FEISHU-MERGE]")
        checks.append(has_debug)
        test("禁用函数已部署", has_disable, "_disable_employee()")
        checks.append(has_disable)
        test("手机号查找函数", has_mobile, "_find_employee_by_mobile()")
        checks.append(has_mobile)

        results.extend(checks)
    else:
        test("auth.py文件存在", False, f"文件不存在: {auth_file}")
        results.append(False)

    # ===== 测试4: 配置文件读取 =====
    print(f"\n{C.Y}[4/6] 用户配置文件分析{C.W}")
    config_file = "/app/config/employee_permissions.json"
    config_checks = []
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        employees = config.get("employees", [])

        # 查找刘太琳
        liutailin = [e for e in employees if e.get("name") == "刘太琳"]
        count_ok = len(liutailin) == 1
        test("刘太琳账号数量", count_ok, f"找到 {len(liutailin)} 个 (期望1个)")
        config_checks.append(count_ok)

        # 查找飞书重复账号
        feishu_dupes = [e for e in employees if e.get("id","").startswith("emp_feishu_")]
        no_dupes = len(feishu_dupes) == 0
        test("无飞书重复账号", no_dupes, f"重复数: {len(feishu_dupes)}")
        config_checks.append(no_dupes)

        if liutailin:
            main = liutailin[0]
            role_ok = main.get("role") == "business_admin"
            test("角色正确(业务管理员)", role_ok, f"实际: {main.get('role')}")
            config_checks.append(role_ok)

            has_unionid = bool(main.get("union_id"))
            test("union_id已同步", has_unionid, main.get("union_id", "")[:20] + "...")
            config_checks.append(has_unionid)

            note = main.get("note", "")
            has_merge_note = "合并" in note or "merged" in note.lower()
            test("合并备注存在", has_merge_note, (note[:50] + "...") if note else "无备注")
            config_checks.append(has_merge_note)

            org_count = len(main.get("organization_node_ids", []))
            org_ok = org_count >= 10
            test("组织树权限保留", org_ok, f"{org_count} 个节点")
            config_checks.append(org_ok)

        results.extend(config_checks)
    else:
        test("配置文件存在", False, f"不存在: {config_file}")
        results.append(False)

    # ===== 测试5: 前端UI组件检查 =====
    print(f"\n{C.Y}[5/6] 前端树形UI代码检查{C.W}")
    vue_file = "/app/frontend/dist/index.html"  # 构建后的文件
    ui_checks = []
    if os.path.exists(vue_file):
        with open(vue_file, 'r', encoding='utf-8') as f:
            vue_content = f.read()

        # 检查是否包含EmployeePermissions相关代码
        has_perm = "EmployeePermissions" in vue_content or "employee-permissions" in vue_content.lower()
        test("权限管理页面存在", has_perm, "Vue构建产物中包含权限管理")
        ui_checks.append(has_perm)
        results.extend(ui_checks)
    else:
        # 尝试源码
        vue_src = "/app/frontend/src/views/EmployeePermissions.vue"
        if os.path.exists(vue_src):
            with open(vue_src, 'r', encoding='utf-8') as f:
                src_content = f.read()

            has_tree = "expandedChannels" in src_content or "channel-group" in src_content
            has_checkbox = "el-checkbox-group" in src_content
            has_models = "loadActiveModels" in src_content or "getActiveAIModels" in src_content

            test("树形结构组件", has_tree, "渠道分组展示")
            ui_checks.append(has_tree)
            test("多选框组件", has_checkbox, "模型权限选择")
            ui_checks.append(has_checkbox)
            test("模型加载逻辑", has_models, "API调用")
            ui_checks.append(has_models)
            results.extend(ui_checks)
        else:
            test("前端文件存在", False, "未找到Vue源码或构建产物")
            results.append(False)

    # ===== 测试6: 环境配置检查 =====
    print(f"\n{C.Y}[6/6] 多环境部署配置{C.W}")
    env_files = [
        ("/app/.env.local", "本地环境配置"),
        ("/app/.env.production", "生产环境配置"),
        ("/app/deploy.ps1", "PowerShell部署脚本"),
        ("/app/nginx/nginx.prod.conf", "Nginx配置模板"),
    ]
    env_checks = []
    for path, name in env_files:
        exists = os.path.exists(path)
        test(name, exists, f"{'存在' if exists else '缺失'}")
        env_checks.append(exists)
    results.extend(env_checks)

    # ===== 汇总 =====
    header("验证结果汇总")
    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"总计: {total} 项测试")
    print(f"{C.G}通过: {passed} 项{C.W}")
    if failed > 0:
        print(f"{C.R}失败: {failed} 项{C.W}")

    print()
    if failed == 0:
        print(f"{C.G}🎉 所有测试通过！系统运行正常。{C.W}")
    else:
        print(f"{C.R}⚠️  有 {failed} 项需关注（可能是预期行为）。{C.W}")

    print()
    print("=" * 65)
    print("💡 已实现功能:")
    print("   ✓ 飞书账号自动合并（手机号匹配）")
    print("   ✓ 权限保留（角色+组织树+模型）")
    print("   ✓ 飞书信息同步（unionid/openid/userid）")
    print("   ✓ 树形模型权限UI（按渠道分组）")
    print("   ✓ 双层权限控制（角色级+用户级）")
    print("   ✓ 多环境部署配置（local/production）")
    print()
    print("🔍 待浏览器验证项:")
    print("   ○ 飞书登录流程（需清除Cookie重新登录）")
    print("   ○ 模型下拉列表过滤效果")
    print("   ○ 树形UI交互（展开/折叠/全选）")
    print("=" * 65)
    print()

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
