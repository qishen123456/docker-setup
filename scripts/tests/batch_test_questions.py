#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量测试智能问数系统。"""
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
os.chdir(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

QUESTIONS = [
    # 一、基础信息检索与单条件过滤
    "朱卫锋的总任务金额是多少？",
    "哪些节点的上级是“东部分公司”？",
    "帮我查一下“上海代表处”的达成率。",
    "属于“业务部”层级的节点有哪些？",
    "找出所有属于“区域条线”的数据。",
    "商用事业部的年度开单是多少？",
    "谁是“餐饮业务部”的业务代表？",
    "哪些代表处属于“南部分公司”？",
    "筛选出剩余任务金额大于0的节点。",
    "“甘青宁代表处”的各项指标数据是多少？",
    # 二、聚合与分组统计
    "区域条线的总任务金额是多少？",
    "行业条线下所有业务代表的年度开单总和是多少？",
    "统计一下每个分公司的平均达成率。",
    "业务部层级的总剩余任务是多少？",
    "代表处层级一共有多少个节点？",
    "按条线汇总他们的年度开单金额。",
    "计算一下公共办公业务部的总任务金额。",
    "每个层级的平均任务金额是多少？",
    "统计所有业务代表的平均剩余任务。",
    "东部分公司下属所有代表处的年度开单总额是多少？",
    # 三、排序与极值查询
    "哪个业务代表的达成率最高？",
    "年度开单金额最低的3个代表处是谁？",
    "任务金额排名前五的节点有哪些？",
    "区域条线中，哪家分公司的剩余任务最多？",
    "找出达成率最低的业务部。",
    "把所有代表处按照达成率从高到低排序。",
    "行业条线里开单金额最高的人是谁？",
    "剩余任务最少的前三个节点是哪些？",
    "哪个层级的平均达成率最高？",
    "找出总任务金额最大和最小的节点。",
    # 四、多条件复合查询
    "属于“东部分公司”且达成率低于60%的代表处有哪些？",
    "找出“行业条线”中，年度开单大于 5000000 且达成率大于80%的人。",
    "统计“南部分公司”下属代表处中，剩余任务不为0的节点数量。",
    "哪些业务代表的任务金额超过了 10000000，但开单金额为0？",
    "找出达成率在80%到100%之间的代表处。",
    "属于“区域条线”且上级不是“商用事业部”的节点有哪些？",
    "行业条线里，剩余任务大于 1000000 的业务代表有哪些？",
    "找出达成率高于平均水平的代表处。",
    "筛选出开单金额大于总任务金额的节点。",
    "找出西部分公司里达成率排前两名的代表处。",
    # 五、口语化、同义词与业务逻辑计算
    "大家今年一共完成了多少业绩？",
    "还有多少销售指标没有完成？",
    "哪些人已经提前完成了全年的任务？",
    "帮我算一下商用事业部整体的实际达成率。",
    "“东部”和“南部”两个分公司，哪个的任务完成得更好？",
    "哪些地方的开单进度落后了（比如达成率低于50%）？",
    "给我一份“行业条线”各成员的业绩排行榜。",
    "谁的任务缺口最大？",
    "代表处里有哪些已经超额完成了指标？",
    "算一下餐饮业务部下属员工的平均开单金额。",
]


def run_test():
    results = []
    for idx, question in enumerate(QUESTIONS, 1):
        print(f"[{idx}/50] {question}", flush=True)
        start = time.time()
        try:
            req = AskRequest(
                question=question,
                preferred_dataset_ids=[3],
                allowed_dataset_ids=[3],
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

            results.append({
                "no": idx,
                "question": question,
                "status": "error" if error else "success",
                "duration": duration,
                "error": error,
                "sql": sql_text,
                "row_count": row_count,
                "analysis": analysis,
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
                "route": {},
            })

    output_path = "/app/batch_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n测试结果已保存到 {output_path}")

    success = sum(1 for r in results if r["status"] == "success")
    error = sum(1 for r in results if r["status"] == "error")
    exception = sum(1 for r in results if r["status"] == "exception")
    print(f"成功: {success}, 错误: {error}, 异常: {exception}")


if __name__ == "__main__":
    run_test()
