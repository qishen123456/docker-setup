# -*- coding: utf-8 -*-
"""生成输入理解层评估基线 understanding_eval.json（前置 0）。

素材来源：
  失误题  <- backend/_typo100_test.py 的 TYPO_ENTITIES + AMB(15 歧义)
  清晰题  <- config/confirmed_behaviors_baseline.md 第6节(16条) + _typo100_test.py 的 CLEAR(15条)
  0 行场景 <- 手工 mock 夹具（A/B/C 三分支各一）

2026-08-28 修订：
  - 刘志伟 dataset_id 3→62（书架实测：刘志伟别名只在 ds=62 节点索引下，typo100 原表标错）
  - 变体==实体名本身的（刘志伟）不进失误题——那是正确写法，应属清晰题

重复生成：python backend/tests/fixtures/_gen_eval.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(BACKEND, ".."))
OUT = os.path.join(HERE, "understanding_eval.json")

# ---- 失误题素材（与 _typo100_test.py 对齐，dataset_id 已按书架实测纠偏）----
DS2, DS3, DS62 = 2, 3, 62
TYPO_ENTITIES = [
    ("山东分公司", DS2, ["山冬分公司", "山东分司", "山東分公司", "山东分公"]),
    ("云贵渝分公司", DS2, ["云贵俞分公司", "云贵雨分公司", "云贵渝分司"]),
    ("江浙沪分公司", DS2, ["江浙沪分司", "江浙户分公司", "江淅沪分公司"]),
    ("豫晋分公司", DS2, ["豫普分公司", "预晋分公司", "豫晋分司"]),
    ("消费者事业部", DS2, ["消费者事业不", "消费这事业部", "消費者事业部"]),
    ("东部分公司", DS3, ["东部分公事", "东部分司", "冬部分公司", "东部风公司"]),
    ("南部分公司", DS3, ["南部分司", "难部分公司", "南部分公"]),
    ("商用事业部", DS3, ["商泳事业部", "商用事业不", "伤用事业部", "商用事業部"]),
    ("迟昊", DS3, ["迟浩", "池昊", "迟吴"]),
    ("丁杰", DS3, ["丁洁", "丁傑", "订杰"]),
    ("刘志伟", DS62, ["刘志威", "刘至伟"]),  # ds 实测=62；变体"刘志伟"=正确写法，不进失误题
    ("靳锋", DS3, ["靳峰", "劲锋", "靳风"]),
    ("京东直营", DS62, ["京东直赢", "京冬直营", "京东直银"]),
    ("天猫直营", DS62, ["天猫直赢", "甜猫直营", "天喵直营"]),
]
TYPO_TPL = ["{}的业绩", "{}业绩怎么样", "看下{}", "{}达成率多少", "{}完成情况"]
AMB = [
    "最不好的，还有第二不好的分公司", "最好的和最差的分公司", "前三名和倒数前三名",
    "最高和最低的分别是", "最好不分公司", "第二差的代表处", "排名靠后的前三名",
    "倒数第一的分公司最好的城市", "好不好都看一下", "中等的分公司",
    "不是最好的分公司", "最差也是最好的分公司", "好的坏的都要",
    "完成最好不分公司情况怎么样了", "最差的前两名分公司",
]
CLEAR_TYPO100 = [
    ("山东分公司的业绩", DS2), ("东部分公司业绩", DS3), ("消费者事业部整体业绩", DS2),
    ("各分公司业绩排名", DS2), ("京东直营和天猫直营对比", DS62), ("迟昊的业绩", DS3),
    ("云贵渝分公司各城市分公司的业绩", DS2), ("达成率大于50%的分公司", DS2),
    ("前三的分公司", DS2), ("商用事业部业绩分析", DS3), ("南部分公司这个月开单", DS3),
    ("京津分公司达成率", DS2), ("西北分公司业绩怎么样", DS2), ("河南代表处的业绩", DS3),
    ("消费者事业部排名", DS2), ("刘志伟的业绩", DS62),
]
# baseline.md 第6节"建议的最小回归问题清单"（13 问数题）
CLEAR_BASELINE6 = [
    ("东部分公司的业绩怎么样了", DS3), ("东部分公司的业绩？", DS3),
    ("东部分公司和南部分公司的业绩对比", DS3), ("业务部业绩排名", DS3),
    ("各分公司业绩排名", DS3), ("消费者城市分公司排名", DS2),
    ("城市分公司的业绩", DS2), ("城市分公司的业绩咋样", DS2),
    ("江浙沪分公司的城市分公司", DS2), ("看下前三的城市分公司", DS2),
    ("低于10%的业务代表", DS2), ("上海那边业绩如何了", DS2),
    ("看下上海代表处的业绩咋样了", DS2), ("东部那个分公司怎么样", DS3),
    ("河北业绩怎么样", DS2), ("看下前三的业务承接人", DS62),
]


def gen_typo():
    cases = []
    tpl_i = 0
    for name, ds, variants in TYPO_ENTITIES:
        for v in variants:
            if v == name:
                continue  # 正确写法不是失误题
            q = TYPO_TPL[tpl_i % len(TYPO_TPL)].format(v)
            tpl_i += 1
            cases.append({
                "question": q, "dataset_id": ds,
                "expected_action": ["rewrite", "soft_hint", "clarify"],
                "expect_correction": name,
                "category": "typo_entity", "source": "typo100",
            })
    for q in AMB:
        cases.append({
            "question": q, "dataset_id": None,
            "expected_action": ["clarify", "soft_hint", "pass"],
            "expect_correction": None,
            "category": "direction_ambiguity", "source": "typo100_amb",
        })
    return cases


def gen_clear():
    cases, seen = [], set()
    for q, ds in CLEAR_TYPO100 + CLEAR_BASELINE6:
        if q in seen:
            continue
        seen.add(q)
        cases.append({
            "question": q, "dataset_id": ds,
            "expected_action": ["pass"],
            "expect_correction": None,
            "category": "clear", "source": "baseline6/typo100_clear",
        })
    return cases


def gen_zero_rows():
    return [
        {
            "question": "火星分公司的业绩",
            "dataset_id": DS3,
            "expected_action": ["branch_A"],
            "expected_branch": "A",
            "branch_desc": "对象不存在（书架+拼音索引均无近邻）",
            "expect_correction": None,
            "category": "zero_rows", "source": "mock",
        },
        {
            "question": "东部分公司的业绩",
            "dataset_id": DS2,
            "expected_action": ["branch_B"],
            "expected_branch": "B",
            "branch_desc": "路由错数据集（东部在 ds=3，却用 ds=2 查）",
            "expect_correction": "切换到 商用事业部开单金额(ds=3)",
            "category": "zero_rows", "source": "mock",
        },
        {
            "question": "达成率大于200%的分公司",
            "dataset_id": DS2,
            "expected_action": ["branch_C"],
            "expected_branch": "C",
            "branch_desc": "真没数据（对象/数据集正确，口径内无数据）",
            "expect_correction": None,
            "category": "zero_rows", "source": "mock",
        },
    ]


def main():
    typo, clear, zero = gen_typo(), gen_clear(), gen_zero_rows()
    doc = {
        "version": "1.1",
        "generated_at": "2026-08-28",
        "description": "输入理解层评估基线（P0 阻断级前置）。失误题=理解层应识别并纠正/提示；清晰题=应 pass 零打扰；0 行=三分支各走对路。v1.1：刘志伟 ds 纠偏 3→62，变体==实体名不进失误题。",
        "sets": {
            "typo": {
                "name": "失误题（同音/漏字/多字/口误全谱系）",
                "pass_criteria": "召回率 >=80%（分母只含 expect_correction 非空的实体错字题；歧义题单列）",
                "count": len(typo),
                "cases": typo,
            },
            "clear": {
                "name": "清晰题（正常问法）",
                "pass_criteria": "误拦率 0",
                "count": len(clear),
                "cases": clear,
            },
            "zero_rows": {
                "name": "0 行场景（A对象不存在/B路由错数据集/C真没数据）",
                "pass_criteria": "三分支各走对路",
                "count": len(zero),
                "cases": zero,
            },
        },
    }
    os.makedirs(HERE, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"OK 失误题={len(typo)} 清晰题={len(clear)} 0行={len(zero)} 合计={len(typo)+len(clear)+len(zero)}")
    print(f"输出: {OUT}")


if __name__ == "__main__":
    main()
