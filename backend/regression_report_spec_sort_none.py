#!/usr/bin/env python3
"""Regression check: report spec sorting must tolerate NULL metric values."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_spec_builder import build_report_spec


def main() -> None:
    dataset = {
        "id": 999001,
        "dataset_code": "consumer_autofill_test",
        "dataset_name": "消费者事业部测试数据集",
    }
    report_config = {
        "nameColumn": "节点名称",
        "parentColumn": "上级名称",
        "levelColumn": "层级",
        "trackColumn": "条线",
        "metrics": [
            {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
            {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
            {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
            {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
        ],
        "levels": [
            {"name": "事业部", "values": ["事业部"]},
            {"name": "业务部", "values": ["业务部"]},
            {"name": "渠道", "values": ["渠道"]},
        ],
        "officeRiskThreshold": 10,
        "officeBenchmarkThreshold": 15,
    }
    rows = [
        {
            "条线": "消费者",
            "层级": "事业部",
            "节点名称": "消费者事业部",
            "上级名称": "",
            "总任务金额": None,
            "年度开单金额": None,
            "达成率": None,
            "剩余任务金额": None,
        },
        {
            "条线": "消费者",
            "层级": "业务部",
            "节点名称": "线上业务部",
            "上级名称": "消费者事业部",
            "总任务金额": 1000000,
            "年度开单金额": None,
            "达成率": None,
            "剩余任务金额": None,
        },
        {
            "条线": "消费者",
            "层级": "业务部",
            "节点名称": "线下业务部",
            "上级名称": "消费者事业部",
            "总任务金额": 800000,
            "年度开单金额": None,
            "达成率": None,
            "剩余任务金额": None,
        },
        {
            "条线": "消费者",
            "层级": "渠道",
            "节点名称": "直营渠道",
            "上级名称": "线上业务部",
            "总任务金额": 400000,
            "年度开单金额": None,
            "达成率": None,
            "剩余任务金额": None,
        },
    ]
    spec = build_report_spec(
        question="消费者事业部业绩怎么样",
        dataset=dataset,
        rows=rows,
        columns=list(rows[0].keys()),
        report_config=report_config,
        sql="SELECT * FROM consumer_autofill_test;",
        review={"review_summary": "unit test"},
    )
    assert spec["version"] == "2.0"
    assert spec["accordions"], "expected drill accordions even when rates are NULL"
    assert spec["accordions"][0]["title"] in {"线上业务部", "线下业务部"}
    print("report spec NULL sort regression check passed")


if __name__ == "__main__":
    main()
