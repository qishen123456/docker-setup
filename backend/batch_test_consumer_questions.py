#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量测试消费者数据集智能问数系统。"""
import json
import os
import sys
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

QUESTIONS = [
    # 一、基础检索与单条件过滤
    '云贵渝分公司的"总实际_万"是多少？',
    '哪些城市分公司隶属于"赣闽分公司"？',
    '查一下"万州城市分公司"的"新零售实际_万"。',
    '找出"线下实际_万"大于 100 万的分公司。',
    '筛选出所有"城市分公司"层级的节点。',
    '"燃气定制-地产任务_万"大于 0 的节点有哪些？',
    '帮我看一下"上海城市分公司"的各项指标。',
    '哪些分公司的总达成率已经达到 100%？',
    '找出上级名称是"消费者事业部"的所有节点。',
    '"豫晋分公司"的"线下任务_万"是多少？',
    # 二、多渠道对比与横向计算
    '哪些城市分公司的"新零售实际_万"超过了"线下实际_万"？',
    '找出"燃气定制-地产实际_万"大于"新零售实际_万"的分公司。',
    '有哪些节点的"总实际_万"不等于线下、新零售和燃气实际的总和？',
    '哪些分公司的"新零售任务_万"占"总任务_万"的比例超过了 50%？',
    '统计线下任务比新零售任务重的城市分公司名单。',
    # 三、分组统计与聚合
    '消费者事业部整体的"线下实际_万"总和是多少？',
    '统计每个分公司下属城市分公司的"新零售实际_万"总和。',
    '城市分公司层级的"燃气定制-地产实际_万"平均值是多少？',
    '帮我汇总一下各分公司的"总任务_万"和"总实际_万"。',
    '线下渠道和新零售渠道，哪个渠道的总实际销售额更高？',
    '按照上级名称分组，计算各区域的平均总达成率。',
    '统计各分公司拥有的城市分公司数量。',
    '算出所有分公司的"燃气定制-地产任务_万"总额。',
    '新零售实际销售额排名前三的分公司是哪些？',
    '哪些分公司的城市分公司平均总实际额低于 50 万？',
    # 四、复杂逻辑与极值
    '燃气定制-地产实际完成额最高的是哪个分公司？',
    '哪个城市分公司的"总实际_万"最低？',
    '找出新零售实际销售额排名前五的城市分公司。',
    '总达成率排在后三名的分公司有哪些？',
    '线下实际完成最好的前三个城市分公司是谁？',
    '找出"线下实际"为0但"新零售实际"大于0的节点。',
    '哪个分公司下属的城市分公司总实际额差距最大？',
    '找出达成率低于平均总达成率的分公司。',
    # 五、业务口语化与同义词转换
    '今年新零售业务谁做得最好？',
    '还有哪些地方燃气定制业务没有开张？',
    '线下拖了后腿（达成率低于 50%）的城市有哪些？',
    '帮我排一下各省分公司的整体业绩。',
    '哪些城市新零售完成了指标，但线下没完成？',
    '燃气定制业务主要集中在哪些分公司？',
    '算一下各区域线上（新零售）和线下渠道的业绩贡献比例。',
]


def run_test():
    results = []
    for idx, question in enumerate(QUESTIONS, 1):
        print(f"[{idx}/{len(QUESTIONS)}] {question}", flush=True)
        start = time.time()
        try:
            req = AskRequest(
                question=question,
                preferred_dataset_ids=[13],
                allowed_dataset_ids=[13],
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

    with open("consumer_batch_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    success = sum(1 for r in results if r["status"] == "success")
    error = sum(1 for r in results if r["status"] == "error")
    exception = sum(1 for r in results if r["status"] == "exception")
    print(f"\n测试完成：成功 {success}，错误 {error}，异常 {exception}，总计 {len(results)}")


if __name__ == "__main__":
    run_test()
