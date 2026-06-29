#!/usr/bin/env python3
"""
SmartAsk ranking 问题复现脚本。
在 smartask-backend 容器内运行，模拟 ask -> confirm_by_boss 完整流程。

用法：
    docker exec smartask-backend python /app/backend/.agents/skills/smartask-ranking-debug/scripts/simulate_ask.py "看下前三的业务承接人" 62

参数：
    question          用户问题
    dataset_id        确认要选择的数据集 ID（默认 62，电商）
    option_id         确认选项 ID（默认 arbiter_dataset_62）
"""
import json
import sys

sys.path.insert(0, "/app/backend")

from four_agent_ask import four_agent_ask_service


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "看下前三的业务承接人"
    dataset_id = int(sys.argv[2]) if len(sys.argv) > 2 else 62
    option_id = sys.argv[3] if len(sys.argv) > 3 else f"arbiter_dataset_{dataset_id}"

    user = {
        "source": "admin",
        "role": "super_admin",
        "role_label": "超级管理员",
        "username": "admin",
        "name": "超级管理员",
    }
    service = four_agent_ask_service

    print(f"=== Step 1: ask(question={question!r}) ===")
    r1 = service.ask(question=question, current_user=user)
    print("requires_confirmation:", r1.get("requires_confirmation"))
    print("route_decision:", r1.get("route", {}).get("decision"))
    print("session_id:", r1.get("session_id"))
    print("confirmation_options:")
    for opt in r1.get("route", {}).get("confirmation_options", []):
        print(f"  - id={opt.get('id')!r} label={opt.get('label')!r} datasets={opt.get('dataset_ids')}")

    session_id = r1.get("session_id")
    if not session_id:
        print("ERROR: no session_id returned")
        return 1

    # 如果没触发确认，直接打印结果
    if not r1.get("requires_confirmation"):
        print_result("ask result", r1)
        return 0

    # 自动选择与 dataset_id 匹配的 option
    selected_option = next(
        (opt for opt in r1.get("route", {}).get("confirmation_options", [])
         if opt.get("id") == option_id),
        None,
    )
    if selected_option is None:
        selected_option = next(
            (opt for opt in r1.get("route", {}).get("confirmation_options", [])
             if dataset_id in [int(x) for x in (opt.get("dataset_ids") or [])]),
            None,
        )
    selected_label = (selected_option or {}).get("label") or f"dataset_{dataset_id}"
    selected_option_id = (selected_option or {}).get("id") or option_id

    print(f"\n=== Step 2: confirm_by_boss(option={selected_label!r}, datasets=[{dataset_id}]) ===")
    r2 = service.confirm_by_boss(
        session_id=session_id,
        selected_option=selected_label,
        selected_dataset_ids=[dataset_id],
        option_id=selected_option_id,
        current_user=user,
    )
    print_result("confirm result", r2)
    return 0


def print_result(label: str, data: dict):
    print(f"\n=== {label} ===")
    print("question:", data.get("question"))
    print("effective_question:", data.get("effective_question"))
    print("display_title:", data.get("display_title"))
    print("row_count:", data.get("row_count"))
    sql = data.get("sql") or ""
    print("sql tail:", sql[-250:])
    if data.get("dataset_results"):
        intent = data["dataset_results"][0].get("query_intent", {})
        print("query_intent:", json.dumps(intent, ensure_ascii=False))
        rows = data["dataset_results"][0].get("rows", [])
        print("rows count:", len(rows))
        for row in rows[:5]:
            print("  -", json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
