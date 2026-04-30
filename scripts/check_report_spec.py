import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dataset_report_config import get_default_config
from report_spec_builder import build_report_spec


def main() -> None:
    config = get_default_config()
    rows = [
        {"条线": "区域条线", "层级": "分公司", "节点名称": "东部分公司", "上级名称": "商用事业部", "总任务金额": 3000, "年度开单金额": 900, "达成率": 30, "剩余任务金额": 2100},
        {"条线": "区域条线", "层级": "代表处", "节点名称": "安徽代表处", "上级名称": "东部分公司", "总任务金额": 1000, "年度开单金额": 800, "达成率": 80, "剩余任务金额": 200},
        {"条线": "区域条线", "层级": "代表处", "节点名称": "河南代表处", "上级名称": "东部分公司", "总任务金额": 2000, "年度开单金额": 100, "达成率": 5, "剩余任务金额": 1900},
        {"条线": "区域条线", "层级": "分公司", "节点名称": "南部分公司", "上级名称": "商用事业部", "总任务金额": 2500, "年度开单金额": 2100, "达成率": 84, "剩余任务金额": 400},
        {"条线": "区域条线", "层级": "代表处", "节点名称": "广东代表处", "上级名称": "南部分公司", "总任务金额": 1200, "年度开单金额": 1080, "达成率": 90, "剩余任务金额": 120},
        {"条线": "区域条线", "层级": "业务代表", "节点名称": "张三", "上级名称": "安徽代表处", "总任务金额": 500, "年度开单金额": 450, "达成率": 90, "剩余任务金额": 50},
        {"条线": "区域条线", "层级": "业务代表", "节点名称": "李四", "上级名称": "河南代表处", "总任务金额": 700, "年度开单金额": 35, "达成率": 5, "剩余任务金额": 665},
        {"条线": "区域条线", "层级": "业务代表", "节点名称": "王五", "上级名称": "广东代表处", "总任务金额": 600, "年度开单金额": 540, "达成率": 90, "剩余任务金额": 60},
    ]
    columns = list(rows[0].keys())
    spec = build_report_spec(
        question="东部分公司业绩怎么样？",
        dataset={"id": 1, "dataset_code": "angel_business_2026", "dataset_name": "商用事业部"},
        rows=rows,
        columns=columns,
        report_config=config,
        sql="select ...",
        review={"review_summary": "测试通过"},
    )

    assert spec["version"] == "2.0"
    assert spec["analysisMode"] == "drill_down"
    assert spec["scope"]["compareLevelLabel"] == "代表处"
    assert spec["scope"]["detailLevelLabel"] == "业务代表"
    assert spec["kpis"]
    assert spec["charts"] and spec["charts"][0]["rows"]
    assert "剩余任务金额" not in spec["charts"][0]["columns"]
    assert len(spec["accordions"]) == 2
    assert spec["accordions"][0]["parentName"] == "东部分公司"
    assert all(token in spec["accordions"][0]["narrative"] for token in ["开单", "任务", "达成率", "剩余缺口"])
    assert spec["provenance"] and spec["provenance"][0]["rowCount"] == len(rows)

    compare_spec = build_report_spec(
        question="东部分公司和南部分公司哪个完成得更好？",
        dataset={"id": 1, "dataset_code": "angel_business_2026", "dataset_name": "商用事业部"},
        rows=rows,
        columns=columns,
        report_config=config,
        sql="select ...",
        review={"review_summary": "测试通过"},
    )
    assert compare_spec["analysisMode"] == "comparative"
    assert compare_spec["scope"]["compareLevelLabel"] == "分公司"
    assert len(compare_spec["charts"][0]["rows"]) == 2
    print("ReportSpec regression passed")


if __name__ == "__main__":
    main()