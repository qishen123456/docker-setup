#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量测试电商数据集（id=62）智能问数系统，输出 JSON 与 Markdown 报告。"""
import json
import os
import sys
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

QUESTIONS = [
    # 一、明细 / 总览（10）
    "电商事业部的业绩",
    "国内业务部的业绩",
    "直营零售部的达成率",
    "跨境业务部的年度开单",
    "净水业务的总任务金额",
    "天猫直营的开单金额",
    "陈小斌的业绩",
    "电商事业部的年度目标营收",
    "国内业务部的剩余任务金额",
    "抖音直营的达成率",
    # 二、排名 / 极值（10）
    "电商事业部业务部业绩排名",
    "电商事业部细分业务达成率排名",
    "业务经理开单金额排名前3的是谁",
    "业务部总任务金额排名",
    "细分业务开单金额排名",
    "业务经理达成率排名",
    "业务部达成率排名",
    "细分业务剩余任务金额排名",
    "业务经理剩余任务金额排名",
    "国内业务部细分业务达成率排名",
    # 三、筛选 / 阈值（10）
    "电商事业部达成率低于30%的细分业务有哪些",
    "开单金额超过1亿的业务经理有哪些",
    "总任务金额大于5亿的业务部有哪些",
    "达成率高于40%的细分业务有哪些",
    "剩余任务金额大于0的细分业务有哪些",
    "国内业务部达成率低于30%的细分业务",
    "跨境业务部开单金额低于1000万的细分业务",
    "年度开单金额在1亿到3亿之间的细分业务",
    "达成率在20%到50%之间的业务经理",
    "直营零售部达成率低于20%的细分业务",
    # 四、对比（10）
    "国内业务部和直营零售部对比",
    "净水业务和饮水业务对比",
    "京东直营和天猫直营对比",
    "国内业务部和跨境业务部对比",
    "抖音直营和达播对比",
    "直营零售部和跨境业务部对比",
    "净水业务和滤芯对比",
    "天猫直营和抖音直营对比",
    "国内业务部和直营零售部开单对比",
    "陈小斌和李金良对比",
    # 五、下钻 / 明细展开（10）
    "国内业务部有哪些细分业务",
    "国内业务部有哪些业务经理",
    "直营零售部下有哪些细分业务",
    "直营零售部有哪些业务经理",
    "跨境业务部有哪些细分业务",
    "跨境业务部有哪些业务经理",
    "电商事业部下有哪些业务部",
    "净水业务下有哪些业务经理",
    "京东直营下有哪些业务经理",
    "国内业务部下属明细",
]


def run_test():
    results = []
    for idx, question in enumerate(QUESTIONS, 1):
        print(f"[{idx}/{len(QUESTIONS)}] {question}", flush=True)
        start = time.time()
        try:
            req = AskRequest(
                question=question,
                preferred_dataset_ids=[62],
                allowed_dataset_ids=[62],
                current_user={"role": "admin", "username": "tester"},
            )
            result = ask_flow_controller.ask(req)
            duration = round(time.time() - start, 2)

            dataset_results = result.get("dataset_results") or []
            dr = dataset_results[0] if dataset_results else {}
            sql_text = dr.get("sql", "") if isinstance(dr, dict) else ""
            rows = dr.get("rows") if isinstance(dr, dict) else None
            row_count = len(rows) if isinstance(rows, list) else None
            error = result.get("error") or dr.get("error") if isinstance(dr, dict) else None
            analysis = dr.get("analysis", "") if isinstance(dr, dict) else ""
            spec = dr.get("report_spec", {}) if isinstance(dr, dict) else {}
            scene = dr.get("report_debug", {}).get("scene", {}).get("key") if isinstance(dr, dict) else None

            results.append({
                "no": idx,
                "question": question,
                "status": "error" if error else "success",
                "duration": duration,
                "error": error,
                "sql": sql_text,
                "row_count": row_count,
                "analysis": analysis,
                "scene": scene,
                "analysis_mode": spec.get("analysisMode") if isinstance(spec, dict) else None,
                "route": result.get("route", {}),
            })
        except Exception as exc:
            duration = round(time.time() - start, 2)
            results.append({
                "no": idx,
                "question": question,
                "status": "exception",
                "duration": duration,
                "error": str(exc),
                "sql": "",
                "row_count": None,
                "analysis": "",
                "scene": None,
                "analysis_mode": None,
                "route": {},
            })

    output_path = "ecommerce_batch_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n测试结果已保存到 {output_path}")

    success = sum(1 for r in results if r["status"] == "success")
    error = sum(1 for r in results if r["status"] == "error")
    exception = sum(1 for r in results if r["status"] == "exception")
    zero_rows = sum(1 for r in results if r["status"] == "success" and r["row_count"] == 0)
    print(f"成功: {success}, 错误: {error}, 异常: {exception}, 成功但0行: {zero_rows}")
    return results


def generate_markdown_report(results):
    lines = []
    lines.append("# 电商数据集（id=62）智能问数批量测试报告\n")
    lines.append(f"- 测试时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"- 总题数：{len(results)}\n")
    success = sum(1 for r in results if r["status"] == "success")
    error = sum(1 for r in results if r["status"] == "error")
    exception = sum(1 for r in results if r["status"] == "exception")
    zero_rows = sum(1 for r in results if r["status"] == "success" and r["row_count"] == 0)
    lines.append(f"- 成功：{success}，错误：{error}，异常：{exception}，成功但0行：{zero_rows}\n")
    lines.append("## 明细\n")
    lines.append("| 序号 | 问题 | 状态 | 行数 | 场景 | 耗时(s) | 备注 |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for r in results:
        remark = ""
        if r["status"] == "error":
            remark = f"错误：{str(r['error'])[:60]}"
        elif r["status"] == "exception":
            remark = f"异常：{str(r['error'])[:60]}"
        elif r["row_count"] == 0:
            remark = "返回0行"
        scene = r.get("scene") or r.get("analysis_mode") or "-"
        lines.append(
            f"| {r['no']} | {r['question']} | {r['status']} | {r['row_count']} | {scene} | {r['duration']} | {remark} |\n"
        )

    lines.append("\n## 需要关注的问题（0行/错误/异常）\n")
    for r in results:
        if r["status"] != "success" or r["row_count"] == 0:
            lines.append(f"- **{r['no']}. {r['question']}**\n")
            lines.append(f"  - 状态：{r['status']}，行数：{r['row_count']}，场景：{r.get('scene') or '-'}\n")
            if r.get("error"):
                lines.append(f"  - 错误：{r['error']}\n")
            if r.get("sql"):
                lines.append(f"  - SQL：```sql\n{r['sql']}\n```\n")

    md_path = "ecommerce_batch_test_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Markdown 报告已保存到 {md_path}")


if __name__ == "__main__":
    results = run_test()
    generate_markdown_report(results)
