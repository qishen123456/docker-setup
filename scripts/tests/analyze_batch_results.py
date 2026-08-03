#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析批量测试结果并生成 Markdown 报告。"""
import json
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze(results, dataset_name):
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    errors = sum(1 for r in results if r["status"] == "error")
    exceptions = sum(1 for r in results if r["status"] == "exception")
    zero_rows = sum(1 for r in results if r.get("row_count") == 0)
    null_rows = sum(1 for r in results if r.get("row_count") is None)
    empty_sql = sum(1 for r in results if not r.get("sql"))

    lines = [
        f"# {dataset_name} 批量测试结果",
        "",
        f"- 总题数：{total}",
        f"- 链路成功（无 error/exception）：{success}",
        f"- 链路错误：{errors}",
        f"- 链路异常：{exceptions}",
        f"- 返回 0 行：{zero_rows}",
        f"- 返回行数为空：{null_rows}",
        f"- SQL 为空：{empty_sql}",
        "",
        "## 逐题明细",
        "",
        "| 题号 | 问题 | 状态 | 行数 | SQL 模式 |",
        "|------|------|------|------|----------|",
    ]
    for r in results:
        no = r["no"]
        question = r["question"].replace("|", "\\|")
        status = r["status"]
        row_count = r.get("row_count") if r.get("row_count") is not None else "N/A"
        sql = r.get("sql", "")
        # 提取 SQL 前几个关键字作为模式
        sql_mode = ""
        if sql:
            upper_sql = sql.upper()
            if "SELECT" in upper_sql:
                sql_mode = "SELECT"
            if "GROUP BY" in upper_sql:
                sql_mode += "+GROUP BY"
            if "ORDER BY" in upper_sql:
                sql_mode += "+ORDER BY"
            if "ROW_NUMBER" in upper_sql:
                sql_mode += "+RANK"
            if "WHERE" in upper_sql:
                sql_mode += "+WHERE"
            sql_mode = sql_mode.strip("+")
        else:
            sql_mode = "EMPTY"
        lines.append(f"| {no} | {question} | {status} | {row_count} | {sql_mode} |")

    lines.append("")
    lines.append("> 注：本报告仅统计链路执行状态与返回行数，业务正确性需结合 SQL 与预期人工复核。")
    return "\n".join(lines)


def main():
    reports = []
    if os.path.exists("batch_test_results.json"):
        reports.append(("batch_test_results.json", "商用数据集"))
    if os.path.exists("consumer_batch_test_results.json"):
        reports.append(("consumer_batch_test_results.json", "消费者数据集"))

    for path, name in reports:
        results = load(path)
        md = analyze(results, name)
        out_path = path.replace(".json", "_report.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"已生成 {out_path}")


if __name__ == "__main__":
    main()
