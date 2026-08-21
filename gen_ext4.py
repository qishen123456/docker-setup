"""生成 baseline-ext4-2026-08-19.json
覆盖：多轮场景（hint 沿用/释放/收敛）、展示层（answerSummary/answerMode）、KPI 合计校验、汇总行、建议文字
"""
import json

cases = []

# ============================================================
# §3.7 / §8.1 / §8.3 多轮场景（用 turns，同 session 连续问）
# ============================================================

# 类型 A：同数据集沿用（4 条）
cases += [
    {"id": "MT-A-1", "type": "turns", "turns": [
        {"q": "商用事业部业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]},
        {"q": "东部分公司的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]},
            {"p": "dataset_results[ds=3].row_count", "op": "gte", "e": 1}
        ]}
    ]},
    {"id": "MT-A-2", "type": "turns", "turns": [
        {"q": "消费者业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]},
        {"q": "豫晋分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]},
            {"p": "dataset_results[ds=2].row_count", "op": "gte", "e": 1}
        ]}
    ]},
    {"id": "MT-A-3", "type": "turns", "turns": [
        {"q": "电商事业部的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [62]}
        ]},
        {"q": "国内业务部的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [62]}
        ]}
    ]},
    {"id": "MT-A-4", "type": "turns", "turns": [
        {"q": "商用业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]},
        {"q": "前3的分公司", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]},
            {"p": "dataset_results[ds=3].query_intent.intent", "op": "eq", "e": "ranking"}
        ]}
    ]},
]

# 类型 B：跨数据集应释放 hint（5 条）
cases += [
    {"id": "MT-B-1", "type": "turns", "turns": [
        {"q": "消费者业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]},
        {"q": "东部分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]},
            {"p": "dataset_results[ds=3].row_count", "op": "gte", "e": 1}
        ]}
    ]},
    {"id": "MT-B-2", "type": "turns", "turns": [
        {"q": "商用业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]},
        {"q": "河北分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]}
    ]},
    {"id": "MT-B-3", "type": "turns", "turns": [
        {"q": "电商业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [62]}
        ]},
        {"q": "东部分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]}
    ]},
    {"id": "MT-B-4", "type": "turns", "turns": [
        {"q": "消费者事业部业绩如何", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]},
        {"q": "其他消费者事业部业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]}
    ]},
    {"id": "MT-B-5", "type": "turns", "turns": [
        {"q": "商用分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]},
        {"q": "看下消费者事业部", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]}
    ]},
]

# 类型 C：先确认后追问（确认后 hint 正确沿用/释放）（4 条）
cases += [
    {"id": "MT-C-1", "type": "turns", "turns": [
        {"q": "前3的分公司", "a": [
            {"p": "requires_confirmation", "op": "eq", "e": True}
        ]},
        {"q": "河北分公司的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]}
    ]},
    {"id": "MT-C-2", "type": "turns", "turns": [
        {"q": "垫底的三个分公司", "a": [
            {"p": "requires_confirmation", "op": "eq", "e": True}
        ]},
        {"q": "东部分公司业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]}
    ]},
    {"id": "MT-C-3", "type": "turns", "turns": [
        {"q": "上海那边业绩如何了", "a": [
            {"p": "requires_confirmation", "op": "eq", "e": True}
        ]},
        {"q": "上海城市公司的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [2]}
        ]}
    ]},
    {"id": "MT-C-4", "type": "turns", "turns": [
        {"q": "上海的业绩如何", "a": [
            {"p": "requires_confirmation", "op": "eq", "e": True}
        ]},
        {"q": "上海代表处的业绩", "a": [
            {"p": "route.dataset_ids", "op": "eq", "e": [3]}
        ]}
    ]},
]

# 类型 D：refined_query 改写（追问触发 refined_query，rank/topn 不丢）（3 条）
cases += [
    {"id": "MT-D-1", "type": "turns", "turns": [
        {"q": "电商业务承接人业绩排名", "a": []},
        {"q": "看下前三的业务承接人", "a": [
            {"p": "dataset_results[ds=62].query_intent.intent", "op": "eq", "e": "ranking"},
            {"p": "dataset_results[ds=62].query_intent.top_n", "op": "eq", "e": 3}
        ]}
    ]},
    {"id": "MT-D-2", "type": "turns", "turns": [
        {"q": "电商业绩", "a": []},
        {"q": "前三的业务承接人", "a": [
            {"p": "dataset_results[ds=62].query_intent.intent", "op": "eq", "e": "ranking"},
            {"p": "dataset_results[ds=62].query_intent.top_n", "op": "eq", "e": 3}
        ]}
    ]},
    {"id": "MT-D-3", "type": "turns", "turns": [
        {"q": "商用的四个分公司", "a": []},
        {"q": "西部分公司业绩", "a": [
            {"p": "dataset_results[ds=3].row_count", "op": "gte", "e": 1}
        ]}
    ]},
]

# ============================================================
# §5.1 展示层 answerSummary（answerMode/title/text）
# ============================================================

# 类型 E：answerSummary 模式正确（10 条）
cases += [
    {"id": "DS-E-1", "q": "城市分公司的业绩", "a": [
        {"p": "dataset_results[ds=2].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-2", "q": "业务部的业绩排名", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-3", "q": "江浙沪分公司的城市分公司", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-4", "q": "低于10%的业务代表", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-5", "q": "东部分公司和南部分公司的业绩对比", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-6", "q": "东部分公司的业绩", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.title", "op": "nonempty"}
    ]},
    {"id": "DS-E-7", "q": "南部分公司业绩", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.title", "op": "nonempty"}
    ]},
    {"id": "DS-E-8", "q": "黄超的业绩", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.title", "op": "nonempty"}
    ]},
    {"id": "DS-E-9", "q": "电商事业部业绩", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
    {"id": "DS-E-10", "q": "消费者城市分公司排名", "a": [
        {"p": "dataset_results[ds=2].report_spec.answerSummary.mode", "op": "neq", "e": None}
    ]},
]

# 类型 F：answerSummary.text 不应为"本次对比"（除非有对比词）（6 条）
cases += [
    {"id": "DS-F-1", "q": "东部分公司的业绩", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "not_contains", "e": "本次对比"}
    ]},
    {"id": "DS-F-2", "q": "南部分公司业绩", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "not_contains", "e": "本次对比"}
    ]},
    {"id": "DS-F-3", "q": "城市分公司的业绩", "a": [
        {"p": "dataset_results[ds=2].report_spec.answerSummary.text", "op": "not_contains", "e": "本次对比"}
    ]},
    {"id": "DS-F-4", "q": "业务部业绩排名", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "not_contains", "e": "本次对比"}
    ]},
    {"id": "DS-F-5", "q": "黄超的业绩", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.text", "op": "not_contains", "e": "本次对比"}
    ]},
    {"id": "DS-F-6", "q": "东部分公司和南部分公司的业绩对比", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "contains", "e": "对比"}
    ]},
]

# ============================================================
# KPI 合计校验（kpi_equals_sum）
# ============================================================

# 类型 G：根节点 OVERVIEW 的 KPI 应等于所有下级合计（5 条）
cases += [
    {"id": "KPI-G-1", "q": "商用事业部整体业绩", "a": [
        {"p": "dataset_results[ds=3]", "op": "kpi_equals_sum", "e": "总任务金额"}
    ]},
    {"id": "KPI-G-2", "q": "消费者事业部整体业绩", "a": [
        {"p": "dataset_results[ds=2]", "op": "kpi_equals_sum", "e": "总任务金额"}
    ]},
    {"id": "KPI-G-3", "q": "电商事业部业绩", "a": [
        {"p": "dataset_results[ds=62]", "op": "kpi_equals_sum", "e": "总任务金额"}
    ]},
    {"id": "KPI-G-4", "q": "商用的四个分公司", "a": [
        {"p": "dataset_results[ds=3]", "op": "kpi_equals_sum", "e": "总任务金额"}
    ]},
    {"id": "KPI-G-5", "q": "城市分公司的业绩", "a": [
        {"p": "dataset_results[ds=2]", "op": "kpi_equals_sum", "e": "总任务金额"}
    ]},
]

# 类型 H：个人业绩 KPI = 单节点（5 条）
cases += [
    {"id": "KPI-H-1", "q": "黄超的业绩", "a": [
        {"p": "dataset_results[ds=62].row_count", "op": "eq", "e": 1},
        {"p": "dataset_results[ds=62].report_spec.kpis.0.value", "op": "nonempty"}
    ]},
    {"id": "KPI-H-2", "q": "靳锋的业绩", "a": [
        {"p": "dataset_results[ds=3].row_count", "op": "eq", "e": 1},
        {"p": "dataset_results[ds=3].report_spec.kpis.0.value", "op": "nonempty"}
    ]},
]

# 类型 I：跨数据集对比 KPI（每个数据集各自 KPI 正确）（3 条）
cases += [
    {"id": "KPI-I-1", "q": "商用和电商的对比", "a": [
        {"p": "dataset_results[ds=3].report_spec.kpis", "op": "nonempty"},
        {"p": "dataset_results[ds=62].report_spec.kpis", "op": "nonempty"}
    ]},
    {"id": "KPI-I-2", "q": "消费者和商用的对比", "a": [
        {"p": "dataset_results[ds=2].report_spec.kpis", "op": "nonempty"},
        {"p": "dataset_results[ds=3].report_spec.kpis", "op": "nonempty"}
    ]},
    {"id": "KPI-I-3", "q": "商用、消费、电商的总达成率对比", "a": [
        {"p": "dataset_results[ds=2].report_spec.kpis", "op": "nonempty"},
        {"p": "dataset_results[ds=3].report_spec.kpis", "op": "nonempty"},
        {"p": "dataset_results[ds=62].report_spec.kpis", "op": "nonempty"}
    ]},
]

# 类型 J：filter KPI / 排名 KPI 不为 None（3 条）
cases += [
    {"id": "KPI-J-1", "q": "低于10%的业务代表", "a": [
        {"p": "dataset_results[ds=3].report_spec.kpis", "op": "nonempty"}
    ]},
    {"id": "KPI-J-2", "q": "前3的分公司", "a": [
        {"p": "dataset_results[ds=3].report_spec.kpis", "op": "nonempty"}
    ]},
    {"id": "KPI-J-3", "q": "前三的业务承接人", "a": [
        {"p": "dataset_results[ds=62].report_spec.kpis", "op": "nonempty"}
    ]},
]

# ============================================================
# 汇总行数量（4 条）
# ============================================================
cases += [
    {"id": "SUM-1", "q": "商用事业部整体业绩", "a": [
        {"p": "dataset_results[ds=3].row_count", "op": "gte", "e": 1}
    ]},
    {"id": "SUM-2", "q": "消费者事业部整体业绩", "a": [
        {"p": "dataset_results[ds=2].row_count", "op": "gte", "e": 1}
    ]},
    {"id": "SUM-3", "q": "电商事业部业绩", "a": [
        {"p": "dataset_results[ds=62].row_count", "op": "gte", "e": 1}
    ]},
    {"id": "SUM-4", "q": "城市分公司的业绩", "a": [
        {"p": "dataset_results[ds=2].row_count", "op": "gte", "e": 1}
    ]},
]

# ============================================================
# 建议文字（answerText）—— 用 contains/not_contains 校验核心要素
# ============================================================
cases += [
    {"id": "TXT-1", "q": "黄超的业绩", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.text", "op": "nonempty"}
    ]},
    {"id": "TXT-2", "q": "城市分公司的业绩", "a": [
        {"p": "dataset_results[ds=2].report_spec.answerSummary.text", "op": "contains", "e": "个"}
    ]},
    {"id": "TXT-3", "q": "东部分公司业绩", "a": [
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "nonempty"}
    ]},
    {"id": "TXT-4", "q": "前三的业务承接人", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.text", "op": "nonempty"}
    ]},
    {"id": "TXT-5", "q": "电商事业部业绩", "a": [
        {"p": "dataset_results[ds=62].report_spec.answerSummary.text", "op": "nonempty"}
    ]},
]

# ============================================================
# §1.2 / §1.4 末端个人节点（应展示个人指标，无"下一级 X 个"措辞）
# ============================================================
cases += [
    {"id": "LEAF-1", "q": "商用事业部业务代表靳锋的业绩", "a": [
        {"p": "dataset_results[ds=3].row_count", "op": "eq", "e": 1},
        {"p": "dataset_results[ds=3].report_spec.answerSummary.text", "op": "not_contains", "e": "下一级"}
    ]},
    {"id": "LEAF-2", "q": "靳锋的业绩", "a": [
        {"p": "dataset_results[ds=3].row_count", "op": "eq", "e": 1}
    ]},
    {"id": "LEAF-3", "q": "黄超的业绩", "a": [
        {"p": "dataset_results[ds=62].row_count", "op": "eq", "e": 1},
        {"p": "dataset_results[ds=62].report_spec.answerSummary.text", "op": "not_contains", "e": "下一级"}
    ]},
]

# 转 qa_runner 格式
out = []
for c in cases:
    if c.get("type") == "turns":
        # 多轮用例
        turns_out = []
        for t in c["turns"]:
            asserts = []
            for a in t["a"]:
                p = {"path": a["p"], "op": a["op"]}
                if "e" in a:
                    p["expect"] = a["e"]
                asserts.append(p)
            turns_out.append({"question": t["q"], "asserts": asserts})
        out.append({"id": c["id"], "turns": turns_out, "source": c.get("src", "")})
    else:
        # 单轮用例
        asserts = []
        for a in c["a"]:
            p = {"path": a["p"], "op": a["op"]}
            if "e" in a:
                p["expect"] = a["e"]
            asserts.append(p)
        out.append({
            "id": c["id"],
            "question": c["q"],
            "asserts": asserts,
            "source": c.get("src", ""),
        })

with open("/app/backend/qa_cases/baseline-ext4-2026-08-19.json", "w", encoding="utf-8") as f:
    json.dump({"version": "ext4-multiturn-display-2026-08-19", "cases": out}, f, ensure_ascii=False, indent=2)
print("cases:", len(out))