import json
cases = []
# ============================================================
# BL-X 系列：基于 confirmed_behaviors_baseline.md 深度扩展 (~100 用例)
# ============================================================

# === §1.1 单对象默认带一层下级 ===
cases += [
    {"id":"BL-1.1-X1","q":"西部分公司业绩","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X2","q":"南部分公司业绩","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X3","q":"北部分公司的业绩","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X4","q":"看下西部分公司的业绩","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X5","q":"西部分公司业绩?","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X6","q":"西部分公司咋样了","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X7","q":"北部那个分公司","d":[3],"rows_gte":1},
    {"id":"BL-1.1-X8","q":"商用的东部分公司","d":[3],"rows_gte":1},
]

# === §1.2 多对象对比不误走下钻 ===
cases += [
    {"id":"BL-1.2-X1","q":"西部分公司和东部分公司的业绩对比","d":[3],"intent":"comparison"},
    {"id":"BL-1.2-X2","q":"东部分公司和西部分公司的对比","d":[3],"intent":"comparison"},
    {"id":"BL-1.2-X3","q":"南北分公司业绩比较","d":[3],"intent":"comparison"},
    {"id":"BL-1.2-X4","q":"东部分公司vs西部分公司的业绩","d":[3],"intent":"comparison"},
    {"id":"BL-1.2-X5","q":"东部分公司跟西部分公司业绩差异","d":[3],"intent":"comparison"},
    {"id":"BL-1.2-X6","q":"商用东部分公司与南部分公司对比","d":[3],"intent":"comparison"},
]

# === §1.2.1 跨数据集对比（总数 / 总任务金额）===
cases += [
    {"id":"BL-1.2.1-X1","q":"商用和消费者的对比","len":[2,3],"intent":"comparison"},
    {"id":"BL-1.2.1-X2","q":"消费者和商用的对比","len":[2,3],"intent":"comparison"},
    {"id":"BL-1.2.1-X3","q":"商用事业部和消费者事业部的总任务金额对比","len":[2,3],"intent":"comparison"},
    {"id":"BL-1.2.1-X4","q":"电商和商用的对比","len":[3,62],"intent":"comparison"},
    {"id":"BL-1.2.1-X5","q":"消费者和电商的对比","len":[2,62],"intent":"comparison"},
    {"id":"BL-1.2.1-X6","q":"商用、消费、电商的总达成率对比","len":[2,3,62],"intent":"comparison"},
]

# === §1.2.2 跨数据集对比执行拆分 ===
cases += [
    {"id":"BL-1.2.2-X1","q":"商用和电商的对比","must_ds":[3,62]},
    {"id":"BL-1.2.2-X2","q":"电商和商用的业绩对比","must_ds":[62,3]},
    {"id":"BL-1.2.2-X3","q":"消费者跟电商的业绩对比","must_ds":[2,62]},
    {"id":"BL-1.2.2-X4","q":"商用、消费者、电商的总任务对比","must_ds":[2,3,62]},
]

# === §1.3 具体节点 + 目标子层级 drilldown ===
cases += [
    {"id":"BL-1.3-X1","q":"西部那个分公司的代表处","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X2","q":"商用东部分公司的城市分公司","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X3","q":"看看西部分公司的代表处","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X4","q":"南部分公司下面的代表处","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X5","q":"北部分公司的代表处","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X6","q":"商用东部分公司下面的代表处","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X7","q":"江浙沪分公司的城市分公司","d":[3],"intent":"drilldown"},
    {"id":"BL-1.3-X8","q":"山东分公司的业务代表","d":[3],"intent":"drilldown"},
]

# === §1.4 电商根节点默认展示直接下级 ===
cases += [
    {"id":"BL-1.4-X1","q":"电商事业部业绩","d":[62],"rows_gte":1},
    {"id":"BL-1.4-X2","q":"看电商事业部的业绩","d":[62],"rows_gte":1},
    {"id":"BL-1.4-X3","q":"电商事业部的表现如何","d":[62],"rows_gte":1},
    {"id":"BL-1.4-X4","q":"电商事业部业绩如何","d":[62],"rows_gte":1},
    {"id":"BL-1.4-X5","q":"电商事业部咋样","d":[62],"rows_gte":1},
    {"id":"BL-1.4-X6","q":"电商事业部的业绩情况","d":[62],"rows_gte":1},
]

# === §2.1 未明确数量时，不要默认 Top3 ===
cases += [
    {"id":"BL-2.1-X1","q":"商用分公司排名","d":[3]},
    {"id":"BL-2.1-X2","q":"商用业务部排名","d":[3]},
    {"id":"BL-2.1-X3","q":"消费者事业部排行","d":[2]},
    {"id":"BL-2.1-X4","q":"消费者城市分公司排名","d":[2]},
    {"id":"BL-2.1-X5","q":"电商业务部排名","d":[62]},
    {"id":"BL-2.1-X6","q":"商用的四个分公司","d":[3]},
]

# === §2.2 排名类问题优先保持排名语义 ===
cases += [
    {"id":"BL-2.2-X1","q":"业务部的业绩排名","d":[3],"intent":"ranking"},
    {"id":"BL-2.2-X2","q":"分公司的业绩排名","d":[3],"intent":"ranking"},
    {"id":"BL-2.2-X3","q":"事业部业绩排名","d":[3],"intent":"ranking"},
    {"id":"BL-2.2-X4","q":"消费者事业部业绩排名","d":[2],"intent":"ranking"},
    {"id":"BL-2.2-X5","q":"电商业务部业绩排名","d":[62],"intent":"ranking"},
]

# === §2.3 业务承接人排名 ===
cases += [
    {"id":"BL-2.3-X1","q":"看下前三的业务承接人","d":[62],"intent":"ranking","topn":3},
    {"id":"BL-2.3-X2","q":"电商业务承接人排名","d":[62],"intent":"ranking"},
    {"id":"BL-2.3-X3","q":"电商事业部业务承接人业绩排名","d":[62],"intent":"ranking"},
    {"id":"BL-2.3-X4","q":"前5的业务承接人","d":[62],"intent":"ranking","topn":5},
    {"id":"BL-2.3-X5","q":"电商事业部承接人排名前三","d":[62],"intent":"ranking","topn":3},
]

# === §2.4 层级 Overview 走 ranking/list ===
cases += [
    {"id":"BL-2.4-X1","q":"城市分公司的业绩情况","d":[2],"intent":"ranking"},
    {"id":"BL-2.4-X2","q":"业务部的业绩情况","d":[3],"intent":"ranking"},
    {"id":"BL-2.4-X3","q":"代表处的业绩如何","d":[3],"intent":"ranking"},
    {"id":"BL-2.4-X4","q":"业务部的业绩如何","d":[3],"intent":"ranking"},
    {"id":"BL-2.4-X5","q":"城市分公司的情况","d":[2],"intent":"ranking"},
]

# === §2.5 排名/TopN 不被下钻分支拦截 ===
cases += [
    {"id":"BL-2.5-X1","q":"看前三的城市分公司","d":[2],"intent":"ranking","topn":3},
    {"id":"BL-2.5-X2","q":"前5的业务代表","d":[3],"intent":"ranking","topn":5},
    {"id":"BL-2.5-X3","q":"看前两名的分公司","d":[3],"intent":"ranking","topn":2},
    {"id":"BL-2.5-X4","q":"Top3的城市分公司","d":[2],"intent":"ranking","topn":3},
    {"id":"BL-2.5-X5","q":"前三的业务部","d":[3],"intent":"ranking","topn":3},
    {"id":"BL-2.5-X6","q":"倒数后3的城市分公司","d":[2],"intent":"ranking","topn":3},
]

# === §2.6 口语化排名数量 ===
cases += [
    {"id":"BL-2.6-X1","q":"消费者事业部，业绩排名垫底的3家分公司","d":[2],"topn":3},
    {"id":"BL-2.6-X2","q":"消费者事业部垫底的5个城市分公司","d":[2],"topn":5},
    {"id":"BL-2.6-X3","q":"倒数前三的分公司","d_in":[2,3],"topn":3},
    {"id":"BL-2.6-X4","q":"垫底的三个分公司","d_in":[2,3],"topn":3},
    {"id":"BL-2.6-X5","q":"垫底的3个分公司","d_in":[2,3],"topn":3},
    {"id":"BL-2.6-X6","q":"垫底的5个业务代表","d_in":[2,3],"topn":5},
    {"id":"BL-2.6-X7","q":"垫底的那3个分公司","d_in":[2,3],"topn":3},
    {"id":"BL-2.6-X8","q":"最好的2个分公司","d_in":[2,3],"topn":2},
]

# === §2.7 最X 没有数量时默认取 1 ===
cases += [
    {"id":"BL-2.7-X1","q":"业绩最差的业务代表","d_in":[3],"topn":1},
    {"id":"BL-2.7-X2","q":"业绩最好的分公司","d_in":[3],"topn":1},
    {"id":"BL-2.7-X3","q":"垫底的分公司","d_in":[2,3],"topn":1},
    {"id":"BL-2.7-X4","q":"业绩最好的业务部","d_in":[3],"topn":1},
    {"id":"BL-2.7-X5","q":"业绩最高的业务部","d_in":[3],"topn":1},
    {"id":"BL-2.7-X6","q":"业绩最差的城市分公司","d_in":[2],"topn":1},
]

# === §2.8 节点索引优先 ===
cases += [
    {"id":"BL-2.8-X1","q":"云贵分公司的业绩","d":[2]},
    {"id":"BL-2.8-X2","q":"上海那边的业绩如何了","d_in":[2,3]},
    {"id":"BL-2.8-X3","q":"河北业绩怎么样","d":[2]},
    {"id":"BL-2.8-X4","q":"消费者事业部垫底的5个城市分公司","d":[2]},
    {"id":"BL-2.8-X5","q":"商用的东部分公司","d":[3]},
]

# === §3.1 通用业务词不确认 ===
cases += [
    {"id":"BL-3.1-X1","q":"业绩","no_confirm":True},
    {"id":"BL-3.1-X2","q":"表现","no_confirm":True},
    {"id":"BL-3.1-X3","q":"金额","no_confirm":True},
    {"id":"BL-3.1-X4","q":"业绩怎么样","no_confirm":True},
    {"id":"BL-3.1-X5","q":"整体业绩","d":[2,3,62],"no_confirm":True},
]

# === §3.4 裸节点优先走节点索引 ===
cases += [
    {"id":"BL-3.4-X1","q":"东部那个分公司怎么样","d":[3],"no_confirm":True},
    {"id":"BL-3.4-X2","q":"上海那边业绩如何了","d_in":[2,3]},
    {"id":"BL-3.4-X3","q":"河北业绩怎么样","d":[2],"no_confirm":True},
    {"id":"BL-3.4-X4","q":"看下上海代表处的业绩咋样了","d":[3],"no_confirm":True},
    {"id":"BL-3.4-X5","q":"继续看河南代表处的业绩如何了","d":[3]},
]

# === §3.5 多数据集重复展示真实节点（确认卡片含真实节点名）===
cases += [
    {"id":"BL-3.5-X1","q":"上海那边业绩如何了","must_confirm":True,"nodes_any":["城市公司","代表处"]},
    {"id":"BL-3.5-X2","q":"河北业绩怎么样","must_confirm":False},
    {"id":"BL-3.5-X3","q":"东部那个分公司怎么样","must_confirm":False},
    {"id":"BL-3.5-X4","q":"上海业绩怎么样","must_confirm":True,"nodes_any":["城市公司","代表处"]},
]

# === §3.6 唯一真实节点命中时直接直出 ===
cases += [
    {"id":"BL-3.6-X1","q":"看下上海代表处的业绩咋样了","d":[3],"no_confirm":True},
    {"id":"BL-3.6-X2","q":"东部那个分公司怎么样","d":[3],"no_confirm":True},
    {"id":"BL-3.6-X3","q":"继续看河南代表处的业绩如何了","d":[3],"no_confirm":True},
    {"id":"BL-3.6-X4","q":"看下北京代表处的业绩","d":[3],"no_confirm":True},
]

# === §6 最小回归补充（按基线文档 §6 列表原话抄 + 变体）===
cases += [
    {"id":"BL-6-MIN-X1","q":"东部分公司的业绩？","d":[3]},
    {"id":"BL-6-MIN-X2","q":"消费者城市分公司排名","d":[2]},
    {"id":"BL-6-MIN-X3","q":"低于10%的业务代表","d":[3],"intent":"filter"},
    {"id":"BL-6-MIN-X4","q":"看下上海代表处的业绩咋样了","d":[3]},
    {"id":"BL-6-MIN-X5","q":"东部分公司和南部分公司的业绩对比","d":[3],"intent":"comparison"},
    {"id":"BL-6-MIN-X6","q":"业务部业绩排名","d":[3],"intent":"ranking"},
    {"id":"BL-6-MIN-X7","q":"各分公司业绩排名","d_in":[2,3],"intent":"ranking"},
    {"id":"BL-6-MIN-X8","q":"城市分公司的业绩","d":[2],"intent":"ranking"},
    {"id":"BL-6-MIN-X9","q":"城市分公司的业绩咋样","d":[2],"intent":"ranking"},
    {"id":"BL-6-MIN-X10","q":"河北业绩怎么样","d":[2]},
    {"id":"BL-6-MIN-X11","q":"商用事业部业务代表靳锋的业绩","d":[3],"no_confirm":True},
]

# === §5.1 前端展示（answerSummary / answerMode）===
cases += [
    {"id":"BL-5.1-X1","q":"城市分公司的业绩","d":[2],"intent":"ranking"},
    {"id":"BL-5.1-X2","q":"江浙沪分公司的城市分公司","d":[3],"intent":"drilldown"},
    {"id":"BL-5.1-X3","q":"低于10%的业务代表","d":[3],"intent":"filter"},
    {"id":"BL-5.1-X4","q":"东部分公司和南部分公司的业绩对比","d":[3],"intent":"comparison"},
]

# 转 qa_runner 期望格式
out = []
for c in cases:
    a = []
    if "d" in c:
        a.append({"path":"route.dataset_ids","op":"eq","expect":c["d"]})
    if "d_in" in c:
        a.append({"path":"route.dataset_ids","op":"in","expect":c["d_in"]})
    if "len" in c:
        a.append({"path":"route.dataset_ids","op":"len_eq","expect":c["len"]})
    if "rows_gte" in c:
        a.append({"path":"dataset_results.0.row_count","op":"gte","expect":c["rows_gte"]})
    if "no_confirm" in c:
        a.append({"path":"requires_confirmation","op":"neq","expect":True})
    if "must_confirm" in c:
        a.append({"path":"requires_confirmation","op":"eq","expect":True})
    if "intent" in c:
        a.append({"path":"dataset_results.0.query_intent.intent","op":"eq","expect":c["intent"]})
    if "topn" in c:
        a.append({"path":"dataset_results.0.query_intent.top_n","op":"eq","expect":c["topn"]})
    if "must_ds" in c:
        a.append({"path":"__all_dataset_ids_in_results","op":"contains_all","expect":c["must_ds"]})
    if "nodes_any" in c:
        a.append({"path":"__confirmation_options_have_node","op":"contains_any","expect":c["nodes_any"]})
    out.append({"id":c["id"],"question":c["q"],"asserts":a})

with open("/app/backend/qa_cases/baseline-ext3-2026-08-19.json","w",encoding="utf-8") as f:
    json.dump({"version":"ext3-deep-2026-08-19","cases":out}, f, ensure_ascii=False, indent=2)
print("cases:", len(out))
