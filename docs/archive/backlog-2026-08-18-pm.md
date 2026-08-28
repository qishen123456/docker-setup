# SmartAsk 待修清单与排期（2026-08-18 下午场）

> 整理时间：2026-08-18 下午
> 整理人：架构师（backlog）
> 范围：今日实测复现的 N1-N8 新回归 + R-bottom5 新回归 + 用户上午拍板未修的 3 个共 12 个 P0/P1 项
> 不含：已通过 08-13~17 修复闭环的 15 项（见 `fix-report-2026-08-18.md`）+ 已复测 PASS 的 4 项 + 非代码数据事实 3 项
> 引用约束：本清单所有"现象/根因"只列已经过静态根因核实（高置信）或今日用户/团队领导实测坐实的事实；不复述未经核实的内容

---

## 一、概述

| 项 | 内容 |
|---|---|
| 待修问题总数 | 12 个（N1-N8 共 8 个 + R-bottom5 新回归 1 个 + 用户拍板未修 3 个） |
| P0 数 | **5 个**（N3/N4/N7/N8/商用的四个分公司——核心 KPI 失真或主路径空） |
| P1 数 | **6 个**（N1/N2/N5/N6/业绩最好的分公司/大于5000万的呢——影响明确但非阻断） |
| P2 数（遗留观察） | 1 个（N1 一新触发点衍生：think 标签/单数"最多"/代表处指代歧义） |
| 同源合并后实际修复点 | 8 个分组（G1~G8），其中 G1/G3/G6 各自"一处修 N 个受益" |
| 强依赖 | G1（flattened_tree 投影）→ G6（ranking top1 增强依赖 G1 的口径修正）；其它组相互独立可并行 |
| 已修复护城河 | 8-13~17 修复的 15 项 + 8-13 的 bug#12 修复为 G2 提供基础（追问结构化字段透传已在），N6/N3 是 bug#12 不彻底残余 |
| 风险特征 | 高风险集中在 G1（影响 ds=3 全量 SQL）；G3/G5 低风险纯解析层 |
| 整体工期估计 | 1 天核心修复 + 0.5 天全量 ds=3 回归（G1 后必须做的兜底验证） |

**核心矛盾**：`flattened_tree` CTE（`backend/dataset_copilot/syyb_rule_generator.py:101-137`）对 ds=3 的层级投影与 KPI 选取口径不一致——同源引发 N7 / 商用的四个分公司 / N8 三个看似不同的问题，根因均落在该 CTE 的 `CASE WHEN` 投影。这是今日工作量最大、影响面最广的一处。

---

## 二、问题清单

### 总表

| # | 现象 | 严重度 | 根因落点 | 修复分组 | 关联用例 |
|---|---|---|---|---|---|
| N1 | "去年的业绩"→ 把"去年"当节点名 `IN ('去年')`→0 行 | P1 | 实体提取未排除"去年"等时间词（four_agent_ask.py:1681 blocked 列表） | G3 | 新增 N-last-year |
| N2 | "各代表处的业绩"→ 把"各代表处"当节点名（被 _looks_like_structural_subject_phrase 漏） | P1 | blocked 与 structural_tokens 列表对层级泛称覆盖不全（four_agent_ask.py:1681/1694） | G5 | 新增 N-all-offices |
| N3 | "业绩咋样了/排名/条线的业绩"→ 确认后零行桩 SQL（intent 缺失 / 误走聚合） | P0 | 追问 intent 继承仍残留 bug#12 修复不彻底：confirm 后 refined_query 污染 + intent 链路不全 | G2 | 新增 N-vague + 增强 R-bottom5 链 |
| N4 | "2025年的业绩"→ 静默查 2026 无提示 | P1 | SQL `WHERE 当前年 = '2026'` 硬编码（L98/L5700/L5737），无"当前年='2025'"路径或缺数据提示 | G3 | 新增 N-2025 |
| N5 | "西藏分公司的业绩"→ 不存在节点静默返回 82 行 | P1 | 无节点校验：entity_names 走 `节点名称 IN (...)` 命中 0 行→自动降级全表 200 行（L4708/4716） | G4 | 新增 N-unknown-node |
| N6 | "谁业绩最好"→ 确认后 ranking 意图丢失 | P1 | confirm 后 refined_query 把"业绩最好"剥成纯问句；同时 ranking detection 缺少口语化变体（"谁最"/"哪个最"） | G7 | 增强 R-best-confirm（已存在 baseline §2.7） |
| N7 | "电商的业绩"→ KPI 张冠李戴（8.8亿 vs 14.96亿） | P0 | `flattened_tree` 投影时 `业务代表` 与 `负责人` 字段串行重复 SUM，导致 `电商事业部`根行被累加错误（syyb_rule_generator.py:106-107） | G1 | 新增 N-ecom-kpi |
| N8 | "四大分公司区域业绩整体盘点"→ 101 行瀑布（4 分公司+25 代表处+72 业务代表） | P0 | `flattened_tree` 投影 `层级=CASE` 在"业务部"漏写 `分公司 LIKE '%业务部'`，业务部行被错分到"代表处"导致递归下钻放大多层 | G1 | 新增 N-four-regions |
| 商用的四个分公司 | "商用的四个分公司" → 层级颠倒 + KPI 张冠李戴 | P0 | 同 N7/N8：`flattened_tree` 把"商用"过滤成节点名走 CTE 后跟"四个分公司"叠加 → 返回代表处/业务部/业务代表层 | G1 | 增强 N-qysg4 |
| 业绩最好的分公司 | "业绩最好的分公司" → KPI 单薄（只榜首/末位）+ 下级无 | P1 | `_build_layered_management_report` ranking 分支（L841-979）top_n=1 走 L905 极值口径，缺 SUM 汇总 + 缺下级两段式 SQL | G6 | R-best-confirm + 新增 N-best-with-children |
| 大于5000万的呢 | "大于5000万的呢" → 追问层级错乱（bug#12 修复不彻底） | P1 | bug#12 修了主要场景但遗漏"filter_metric_column 默认值 + 多重追问变体 + threshold 单位歧义" | G2 | 增强 baseline §5 |
| R-bottom5 | "垫底的5个城市分公司" → top_n=5/direction=asc 对，但 row_count=0 | P1 | consumer ranking SQL 生成 top_n=5 解析正确，但 ask_engine_entity.py 实体提取误把"5个城市分公司"作为整体 entity 入库，过 null 校验后 SQL `WHERE` 走错主体 | G8 | R-bottom5 baseline §2.6（已存在） |

### 逐条详表

#### N1 — 「去年的业绩」0 行

| 项 | 内容 |
|---|---|
| 现象 | 用户问"去年的业绩"，SQL 生成 `WHERE 节点名称 IN ('去年') AND 上级名称 IN ('去年')`，返回 0 行 |
| 根因 | `_question_subject_names`（`four_agent_ask.py:1893`）→ `_looks_like_org_subject_question`（`ask_engine_entity.py:71`）未拦截"去年"等时间词。`four_agent_ask.py:1681` blocked 列表虽含"今年/本年"但漏"去年/前年/明年/去年年底"等 |
| 代码片段 | `four_agent_ask.py:1679-1684` `blocked = [..., "今年", "本年", ...]` 缺"去年/前年" |
| 复现步骤 | 输入"去年的业绩" → ds=3 → entity_names=['去年'] → `WHERE 节点名称 IN ('去年')` → 0 行 |
| 严重度 | P1（语义层面错误，不阻断主流程） |
| 修复点 | `four_agent_ask.py:1679-1684` blocked 列表补"去年/前年/明年/明后年/年初/年底/上个月/上季度"等时间词；同步在 `ask_engine_entity.py:71` `_looks_like_org_subject_question` 加时间词守卫 |
| 风险 | 低（纯解析层拦截） |
| 关联用例 | **新增** `cases/baseline.json` `N-last-year`：预期"去年"不出现在 entity_names，dataset 走 ds=3 通用业绩查询 |

#### N2 — 「各代表处的业绩」节点名错位

| 项 | 内容 |
|---|---|
| 现象 | "各代表处的业绩"→ entity_names=['各代表处']，SQL `WHERE 节点名称 IN ('各代表处')` 0 行 |
| 根因 | `four_agent_ask.py:1982` org_pattern 中"各/全部/所有 + 层级词"被识别成实体名；`four_agent_ask.py:1694` structural_tokens 含"全部/所有/哪些/哪个/几个"但**缺"各"** |
| 代码片段 | `four_agent_ask.py:1694` `structural_tokens = [..., "全部", "所有", "哪些", "哪个", "几个"]` 缺"各" |
| 复现步骤 | 输入"各代表处的业绩" → entity_names=['各代表处'] → 0 行 |
| 严重度 | P1 |
| 修复点 | `four_agent_ask.py:1694` structural_tokens 补"各"；同步 `_looks_like_org_subject_question` 早返回 |
| 风险 | 低 |
| 关联用例 | **新增** `N-all-offices` |

#### N3 — 「业绩咋样了/排名/条线的业绩」零行桩 SQL

| 项 | 内容 |
|---|---|
| 现象 | "业绩咋样了" / "排名" / "条线的业绩" 确认后返回 0 行桩 SQL（`SELECT * FROM ... WHERE 1=0` 或类似） |
| 根因 | ①`bug#12` 修了主要追问场景，但"业绩咋样了"这种**口语化空问句**走 confirm 路径时，`refined_query` 被剥成纯问句 → `intent=unknown` → rule-based 兜底走"业绩" overview 但 target_level=""，最终桩 SQL；②"条线的业绩"中"条线"被解析为组织层级（行业条线/区域条线）走错 filter |
| 代码片段 | `four_agent_ask.py:8470-8520` 追问 intent 继承逻辑；`four_agent_ask.py:4765-4768` "行业条线/区域条线" 误匹配 |
| 复现步骤 | "业绩咋样了" → 确认 ds=3 → refined_query="业务" → intent=unknown → 0 行 |
| 严重度 | **P0**（用户场景高发） |
| 修复点 | G2 修复的一部分：`four_agent_ask.py:8470-8484` confirm 后 intent 解析只取 raw_question 不取 refined 末尾剥离补全；追问场景补"业绩咋样了/排名"→ 强制 aggregate + 默认分公司层级 |
| 风险 | 中（影响追问链路） |
| 关联用例 | **新增** `N-vague`、`N-tiaoxian` |

#### N4 — 「2025年的业绩」静默错年

| 项 | 内容 |
|---|---|
| 现象 | "2025年的业绩"→ SQL 仍走 `WHERE 当前年='2026'`，返回 2026 数据无任何提示 |
| 根因 | `syyb_rule_generator.py:98`、`four_agent_ask.py:5700/5737` 硬编码 `当前年='2026'`；无年份解析、无数据空集提示 |
| 代码片段 | `syyb_rule_generator.py:98` `WHERE COALESCE(NULLIF(TRIM(...当前年...), ''), '2026') = '2026'` |
| 复现步骤 | 输入"2025年的业绩" → SQL 仍 2026 → 静默返回 |
| 严重度 | P1（数据准确性问题） |
| 修复点 | G3 共修：①sql 加 year 解析（解析出问题中 2024/2025/2026），动态替换 `='2026'`；②数据为空时返回明确"2025 年无数据"提示而非 0 行 |
| 风险 | 中（影响 ds=3 主 SQL） |
| 关联用例 | **新增** `N-2025`（ds=3 应返回空 + 提示）；扩展 `cases/baseline.json` 全量场景含时间词的用例 |

#### N5 — 「西藏分公司的业绩」静默 82 行

| 项 | 内容 |
|---|---|
| 现象 | "西藏分公司的业绩"→ SQL 走 `WHERE 节点名称 IN ('西藏分公司')`，0 命中但仍返回 82 行（兜底全表 200 行被 LIMIT 截到实际行数） |
| 根因 | `four_agent_ask.py:4708` `节点名称 IN (...)` 0 命中后**未走空集校验**，rule 兜底返回全表；`_node_index_subject_names_from_question`（L1842）虽能解析"西藏分公司"但被 `_has_specific_node`（L1895）放过 |
| 代码片段 | `four_agent_ask.py:4701-4719` 主路径 `WHERE {where_clause}` 无 `LIMIT 0` 短路 |
| 复现步骤 | "西藏分公司的业绩" → 节点不存在 → 兜底 82 行 |
| 严重度 | P1（错误数据风险） |
| 修复点 | G4 共修：①node_index 校验不过时**降级到"未找到节点"提示**而非 SQL；②SQL 主路径加 `entity_count > 0 AND hit_count == 0 → empty` |
| 风险 | 中 |
| 关联用例 | **新增** `N-unknown-node`（预期空集 + 提示）；同步扩展 `cases/baseline.json` 节点校验用例 |

#### N6 — 「谁业绩最好」confirm 后 ranking 丢失

| 项 | 内容 |
|---|---|
| 现象 | "谁业绩最好" 选 ds=3 confirm 后，返回非 ranking（intent 未知），走默认 SQL |
| 根因 | ①`refined_query` 中"业绩最好"被剥离补全文本淹没；②ranking detection 未覆盖口语化变体"谁最/哪个最"（`ranking_policy` 词表 `four_agent_ask.py:2452` 只有"最高/最低/最好/最差"） |
| 代码片段 | `four_agent_ask.py:2452` `ranking_policy_keywords = ["排名", "排行", "排序", "名次", "榜", "最高", "最低", "最好", "最差"]` 缺"谁/哪个" |
| 复现步骤 | "谁业绩最好" → 确认 ds=3 → intent=unknown |
| 严重度 | P1 |
| 修复点 | G7 修复：ranking_policy_keywords 补"谁最?/哪个最?/哪家最"正则模式；confirm 后 intent 解析优先取 raw_question |
| 风险 | 中 |
| 关联用例 | **增强** `R-best-confirm`（已存在）：补"谁业绩最好"问法；新增 `N-who-best` |

#### N7 — 「电商的业绩」KPI 张冠李戴

| 项 | 内容 |
|---|---|
| 现象 | "电商的业绩" ds=3 → 顶层 KPI 显示 8.8亿，真实应是 14.96亿 |
| 根因 | `flattened_tree` CTE（`syyb_rule_generator.py:101-137`）投影时：`WHEN 分公司 <> '' AND 分公司 LIKE '%业务部'` 这一行**先把"业务部"字样的分公司判定为业务部**，但下游 ds=3（商用）数据中有些"电商业务部"被串入"分公司"层级时 KPI 取错；电商事业部根行的 KPI 被错误地取了非"电商业务部"组织路径的数据 |
| 代码片段 | `syyb_rule_generator.py:106-107` `WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'` + `WHEN 业务部 <> '' THEN '业务部'` 重复投影 |
| 复现步骤 | "电商的业绩" → ds=3 → 顶层 KPI 8.8亿 vs 真实 14.96亿 |
| 严重度 | **P0** |
| 修复点 | G1 核心：①`flattened_tree` 投影逻辑合并"分公司含业务部字样"与"业务部字段"为单 CASE；②明确电商事业部行使用 `dataset_dimension_profiles`（profile 数据源恢复后才能彻底）作为 fallback |
| 风险 | **高**（影响 ds=3 全量 SQL） |
| 关联用例 | **新增** `N-ecom-kpi`（预期 14.96亿） |

#### N8 — 「四大分公司区域业绩整体盘点」101 行瀑布

| 项 | 内容 |
|---|---|
| 现象 | "四大分公司区域业绩整体盘点" ds=3 → 101 行（4 分公司+25 代表处+72 业务代表），用户期望 29 行 |
| 根因 | `flattened_tree` 投影 `WHEN 分公司 <> '' AND 分公司 LIKE '%业务部'` 把数据中部分代表处错分到"业务部"层级，下游 RECURSIVE 下钻放大多层（4+25+72） |
| 代码片段 | `syyb_rule_generator.py:101-137` 投影 + `four_agent_ask.py:4720+` aggregate SQL |
| 复现步骤 | 团队领导实测坐实：输入"四大分公司区域业绩整体盘点" → 101 行 |
| 严重度 | **P0** |
| 修复点 | G1 核心：同上 G1 修复 |
| 风险 | **高** |
| 关联用例 | **新增** `N-four-regions`（预期 29 行：4 分公司+25 代表处） |

#### 商用的四个分公司（用户上午拍板未修）

| 项 | 内容 |
|---|---|
| 现象 | "商用的四个分公司" → 层级颠倒 + KPI 张冠李戴；返回的不是"商用事业部下 4 个分公司"，而是层级链全展开 |
| 根因 | 同 N7/N8：`flattened_tree` 投影把"商用"过滤后走"四个分公司"叠加触发递归下钻 |
| 修复点 | G1 同源修复 |
| 风险 | 高（同 N7/N8） |
| 关联用例 | **增强** `N-qysg4`（已存在 baseline §1.4 上下文但 row_count 期望从"递归全展开"修正为 4） |

#### 业绩最好的分公司（用户上午拍板未修）

| 项 | 内容 |
|---|---|
| 现象 | "业绩最好的分公司" → KPI 单薄（只榜首/末位）+ 缺下级两段式 |
| 根因 | `_build_layered_management_report` ranking 分支（`four_agent_ask.py:841-979`）top_n=1 时走 L905-932 极值口径，**无 SUM 汇总行**，**无下级两段式 SQL** |
| 代码片段 | `four_agent_ask.py:905-932` 仅展示 leader 与风险节点；`four_agent_ask.py:1067-1141` comparison 分支有 sides 但 ranking 缺 |
| 修复点 | G6 独立修复 |
| 风险 | 中（影响报告生成层） |
| 关联用例 | **增强** `R-best-confirm` 期望加 KPI 文本断言；**新增** `N-best-with-children`（row_count + 下级行） |

#### 大于5000万的呢（用户上午拍板未修）

| 项 | 内容 |
|---|---|
| 现象 | "大于5000万的呢"→ 追问层级错乱（bug#12 修复不彻底） |
| 根因 | bug#12 修了主要场景，但遗漏：①`filter_metric_column` 默认值未在追问时正确继承；②多重追问变体（"大于 5000 万的呢"/"业绩大于 5000 万的呢"/"超过 5000 万的"）；③threshold 单位歧义（万/亿）与 `normalize_syyb_threshold_value`（L4636）顺序 |
| 代码片段 | `four_agent_ask.py:8490-8520` 追问 filter intent 强制分支 + `format_syyb_threshold`（L4647-4656） |
| 修复点 | G2 共修的一部分 |
| 风险 | 中 |
| 关联用例 | **增强** `cases/baseline.json` §5 追问变体扩展（加 6 个追问变体） |

#### R-bottom5 — 今日实测坐实的新回归

| 项 | 内容 |
|---|---|
| 现象 | "垫底的5个城市分公司"→ `top_n=5`、`direction=asc` 解析正确，但 `row_count=0` |
| 根因 | `_question_subject_names`（`four_agent_ask.py:1893`）→ `_looks_like_org_subject_question`（`ask_engine_entity.py:71`）对"垫底的5个城市分公司"返回 True（"垫底"被吞入），被吞 entity_names；下游 ranking SQL 走 `层级 IN ('分公司','业务部')` 但 ds=2 实际无该组合，0 行 |
| 代码片段 | `four_agent_ask.py:1893-1931` 实体提取；`ask_engine_entity.py:71-118` org_subject 拦截 |
| 复现步骤 | 团队领导实测坐实：`top_n=5 direction=asc` 但 `row_count=0` |
| 严重度 | P1 |
| 修复点 | G8 独立修复：①`ask_engine_entity.py:71-118` 修"数量+层级词"提取逻辑，对"5个城市分公司"提取"城市分公司"而非"5个城市分公司"；②ranking SQL 主路径加 `target_level='城市分公司'` 默认兜底 |
| 风险 | 低 |
| 关联用例 | **已有** baseline.json R-bottom5（row_count 期望 5） |

---

## 三、修复分组（同族合并）

### G1 — ds=3 SQL 投影组（flattened_tree 一处修，N7+商用的四个分公司+N8 一处修一堆）

| 字段 | 内容 |
|---|---|
| 成员 | N7 + 商用的四个分公司 + N8 |
| 同源 | 三者均落 `flattened_tree` CTE（`syyb_rule_generator.py:101-137`）投影错误 |
| 关键代码 | `syyb_rule_generator.py:101-137`（CTE 定义）；`four_agent_ask.py:4710+` aggregate SQL 兜底 |
| 修复方式 | ①合并 `WHEN 分公司 <> '' AND 分公司 LIKE '%业务部'` 与 `WHEN 业务部 <> ''` 为单 CASE；②电商事业部根行 KPI 严格走 profile 数据源（若 profile 不可用兜底 SUM(明细)）；④`RECURSIVE` 下钻增加 `max depth = 2`（分公司+代表处）截断 |
| 受益 | 3 个 P0 问题同时修 |
| 风险 | **高**（影响 ds=3 全量 4 个确认分支 + 13 个 ranking 分支） |
| 缓解 | 修完必须跑 ds=3 全量回归（baseline §1-§3 共 25 用例 + bugs §1-§3 共 6 用例 + 商用电商对比 1 用例） |

### G2 — 追问层级继承组（bug#12 修复不彻底，N3+大于5000万的+N6 残余）

| 字段 | 内容 |
|---|---|
| 成员 | N3 + 大于5000万的呢 + N6（部分） |
| 同源 | bug#12 已修主链路，但 confirm/追问场景下 ①refined_query 末尾污染 + ②intent 继承不全 |
| 关键代码 | `four_agent_ask.py:8470-8520` 追问 intent 继承；`four_agent_ask.py:8961-8963` resolve_followup；`backend/memory/short_term_memory.py:93-115` |
| 修复方式 | ①intent 解析优先 raw_question（已部分实施，扩展到 confirm 场景）；②追问 intent=unknown 时强制 filter/aggregate；③filter_metric_column 默认值在追问时继承；④threshold 单位歧义排序提前 |
| 受益 | 3 个问题同时修 |
| 风险 | 中（追问链路） |
| 缓解 | 跑 baseline §5 全部追问用例（已 PASS 需保持） |

### G3 — 时间词解析组（N1+N4）

| 字段 | 内容 |
|---|---|
| 成员 | N1 + N4 |
| 同源 | 时间词"去年"/"前年"未被 blocked，且硬编码 `当前年='2026'` 不接受用户年 |
| 关键代码 | `four_agent_ask.py:1679-1684` blocked 列表；`syyb_rule_generator.py:98` 年份硬编码 |
| 修复方式 | ①blocked 列表补时间词；②SQL 接受用户年（解析 2024/2025/2026 → `当前年 = 'YYYY'`）；③数据为空时返回明确提示 |
| 受益 | 2 个 P1 |
| 风险 | 中（影响 ds=3 主 SQL 年份） |
| 缓解 | baseline §2 加 2 个时间词用例 |

### G4 — 节点校验组（N5+确认后桩 SQL）

| 字段 | 内容 |
|---|---|
| 成员 | N5 + 桩 SQL 兜底（G2 的延伸） |
| 同源 | entity_names 0 命中后未走空集校验 |
| 关键代码 | `four_agent_ask.py:4701-4719` 主路径 where；`four_agent_ask.py:1842-1885` `_node_index_subject_names_from_question` |
| 修复方式 | ①node_index 校验不过降级提示；②SQL 主路径 `hit_count == 0 → empty`；③ranking 桩 SQL 加 debug 日志便于发现 |
| 受益 | 2 个 P1 |
| 风险 | 中 |
| 缓解 | baseline §3 加节点校验用例 |

### G5 — 层级泛称组（N2）

| 字段 | 内容 |
|---|---|
| 成员 | N2 |
| 同源 | structural_tokens 缺"各" |
| 关键代码 | `four_agent_ask.py:1694` structural_tokens |
| 修复方式 | 单条修复 |
| 受益 | 1 个 P1 |
| 风险 | 低 |

### G6 — rank top1 增强组（业绩最好的分公司独立）

| 字段 | 内容 |
|---|---|
| 成员 | 业绩最好的分公司（用户拍板） |
| 同源 | top_n=1 ranking 报告缺 SUM 汇总 + 缺下级两段式 |
| 关键代码 | `four_agent_ask.py:841-979` ranking 分支；`four_agent_ask.py:905-932` 极值分支 |
| 修复方式 | ①top_n=1 时核心结论补 SUM 汇总行（任务/开单/达成率/缺口）；②补下级两段式 SQL（同级 + 命中节点下级）；③report_spec_builder.py ranking 分支同步 |
| 受益 | 1 个 P1 |
| 风险 | 中 |
| 缓解 | R-best-confirm 跑 2 个数据集分支 |

### G7 — ranking 生成路径（N6 谁业绩最好）

| 字段 | 内容 |
|---|---|
| 成员 | N6 |
| 同源 | ranking_policy_keywords 缺"谁/哪个" |
| 关键代码 | `four_agent_ask.py:2452`；`four_agent_ask.py:8470-8484` confirm intent 解析 |
| 修复方式 | ①ranking_policy_keywords 补"谁/哪个"；②confirm 后 intent 解析优先 raw_question |
| 受益 | 1 个 P1 |
| 风险 | 低 |

### G8 — R-bottom5 回归（独立）

| 字段 | 内容 |
|---|---|
| 成员 | R-bottom5 |
| 同源 | "数量+层级"提取错误 |
| 关键代码 | `ask_engine_entity.py:71-118`；`four_agent_ask.py:1893-1931` |
| 修复方式 | 单一文件单一函数 |
| 受益 | 1 个 P1 |
| 风险 | 低 |

---

## 四、修复排期（按依赖顺序）

> 每步独立 commit，QA 验收通过后再进下一步。所有改动经 `docker cp` + `docker compose restart backend` 后跑 `qa_runner.py` 验证。

| 步骤 | commit 前缀 | 主要改动 | 改动行数估计 | 风险 | 验证（QA 已有用例 + 新增） |
|---|---|---|---|---|---|
| **Step 1 — G5 止血** | `fix(G5): blocker list 补"各"层级泛称` | `four_agent_ask.py:1694` structural_tokens +1 | +2 行 | 低 | baseline 全量 + 新增 `N-all-offices` |
| **Step 2 — G3 止血-解析层** | `fix(G3): 时间词 blocked + 年份解析入口` | `four_agent_ask.py:1679-1684` +5 + 新增 `_resolve_question_year` 入口 | +20 行 | 低 | baseline 全量 + 新增 `N-last-year`、`N-2025` |
| **Step 3 — G8 止血** | `fix(G8): 数量+层级实体提取守卫` | `ask_engine_entity.py:71-118` 重写 entity 提取 | +25 行 | 低 | R-bottom5 baseline + 新增 `N-垫底X` 变体 |
| **Step 4 — G4 节点校验** | `fix(G4): 空集校验 + 节点不存在降级` | `four_agent_ask.py:4701-4719` 主路径加空集短路；`four_agent_ask.py:1842-1885` node_index 校验 | +40 行 | 中 | baseline 全量 + 新增 `N-unknown-node`（3 变体） |
| **Step 5 — G7 ranking 路径** | `fix(G7): ranking_policy 补"谁/哪个" + confirm intent 修复` | `four_agent_ask.py:2452` +3；`four_agent_ask.py:8470-8484` +10 | +13 行 | 低 | R-best-confirm + 新增 `N-who-best` |
| **Step 6 — G2 追问继承** | `fix(G2): confirm/追问 intent 链路收口（bug#12 不彻底残余）` | `four_agent_ask.py:8470-8520` 扩展；`backend/memory/short_term_memory.py:93-115` 加固 | +60 行 | 中 | baseline §5 全部追问 + 新增 6 变体 + 大于5000万的呢 |
| **Step 7 — G6 rank top1** | `fix(G6): ranking top1 补 SUM 汇总 + 下级两段式` | `four_agent_ask.py:841-979` + `report_spec_builder.py` | +50 行 | 中 | R-best-confirm 增强 + 新增 `N-best-with-children` |
| **Step 8 — G1 投影核心** | `fix(G1): flattened_tree 投影合并 + 电商 KPI fallback + RECURSIVE max depth` | `syyb_rule_generator.py:101-137` 改写 + `four_agent_ask.py:4710+` + `RECURSIVE` 截断 | +60 行 | **高** | **必跑 ds=3 全量回归**：baseline §1-§3 共 25 用例 + bugs §1-§3 共 6 用例 + 4 个 G1 相关新增/增强 |
| **Step 9 — G3 收口-SQL 层** | `fix(G3-sql): 当前年='YYYY' 动态 + 空集提示` | `syyb_rule_generator.py:98` 动态；新增空集提示 | +30 行 | 中 | baseline §2 + 新增 N-2025 |

**关键依赖**：

- Step 1-3 独立可并行（互不依赖）
- Step 4 依赖 Step 1（节点校验要 G5 的泛称先过滤掉）
- Step 6 依赖 Step 5（confirm intent 解析依赖 G7 的 ranking 入口正确）
- Step 7 独立（仅依赖 report_spec_builder.py）
- **Step 8 必须在 Step 4/5/6 完成后**（避免 G1 投影修改与 G4 空集短路冲突）
- Step 9 必须在 Step 8 之后（G3 SQL 层依赖 G1 投影修复后的稳定形态）

**总工期估计**：核心修复 1 个工作日（Step 1-8）+ 0.5 天全量 ds=3 回归（Step 8 后的强制项）

---

## 五、风险评估

| 风险点 | 影响范围 | 等级 | 缓解措施 |
|---|---|---|---|
| **G1 flattened_tree 投影改写** | ds=3 全量 4 个 confirm 分支 + 13 个 ranking 分支 + RECURSIVE 下钻 | **高** | ①Step 8 必须在 Step 4-7 完成后执行（避免叠加变量）；②Step 8 后强制跑 ds=3 全量回归 25 用例；③G1 改动行数控制 < 60 行便于 bisect；④先 commit G1 投影合并（CTE 改写）独立验证，再 commit RECURSIVE max depth（截断）独立验证 |
| **G2 追问链路扩展** | 追问场景全部链路 | 中 | ①Step 6 优先修 confirm 后 intent 解析（raw_question 优先），与已修 bug#12 不冲突；②扩展 `_metric_pattern` 单位歧义修复独立 commit |
| **G3 SQL 年份动态** | ds=3 主 SQL + 电商 SQL + 消费者 SQL | 中 | ①Step 9 顺序在 Step 8 后（投影稳定后再改年份）；②空集提示走独立 if 分支不影响主流程 |
| **G4 空集短路** | 主路径 aggregate + ranking + filter SQL | 中 | ①`hit_count == 0` 短路仅在 WHERE 含 entity 过滤时启用；②桩 SQL 仅在 debug 模式打日志 |
| **G6 report_spec 改动** | 报告生成层 | 中 | ①与 G1 投影修复独立 commit；②report_spec_builder.py 加单元断言 |

**回归测试矩阵**（Step 8 后必跑）：

- baseline §1 跨数据集对比（4 用例）
- baseline §2 ranking（10 用例含 R-bottom5）
- baseline §3 单数据集查询（15 用例含 N-henan）
- baseline §5 追问（10 用例含大于5000万的）
- baseline §6 行业/区域条线（3 用例）
- baseline §7 直营零售/承接人（5 用例）
- baseline §8 多人/并列（3 用例）
- bugs.json 全部 22 用例
- 4 个新增 G1 用例（N-ecom-kpi / N-four-regions / N-qysg4 / N-best-with-children）

合计 76 用例 250+ 断言，0 FAIL 即视为回归通过。

---

## 六、遗留观察项（P2，不阻塞本次修复）

| # | 项 | 现象 | 根因（初步） | 建议 |
|---|---|---|---|---|
| L1 | think 标签泄漏 | Agent1 refined_query 含 `<think>...</think>` 内容（实测 14 处） | prompt 模板未过滤 <think> 块 | 下个迭代单独立项过滤逻辑 |
| L2 | 单数"最多"歧义 | "业务代表最多的是谁"被误判为 ranking（"最多"=最广 vs 最多） | ranking_policy_keywords 未区分"最多"歧义 | 词表扩展或加歧义问询 |
| L3 | 代表处指代歧义 | "代表处"在商用 ds=3 = 二级，在电商 ds=62 = 缺失 | 跨数据集同名不同义未归一化 | 数据字典层 alias 表 |
| L4 | profile 数据源恢复 | `dataset_dimension_profiles.json` 0709 被删，10+ 处静默返回 None；G1 修复的电商 fallback 受阻 | 文件被误删 | 与运维协调恢复（不阻塞 G1，G1 走 SUM(明细) 兜底） |

**L1-L3 不影响本次修复的核心路径**，建议下个迭代单独立项处理。**L4 是数据恢复项**，需运维/数据团队协同，但 G1 修复已预留兜底路径不阻塞。

---

## 七、参考资料

- `fix-report-2026-08-18.md` — 8-13~17 修复闭环的 15 项 + 复测 PASS 4 项 + 非代码项 3 项
- `bug-backlog-2026-08-14.md` — 已修复的 14 项原始 backlog（已闭环）
- `cases/baseline.json` — 85 用例基线（含本次新增/增强的 G1-G8 用例）
- `cases/bugs.json` — 22 用例（含 G1 关键路径断言）
- `.workbuddy/memory/2026-08-18-*.md` — 今日实测日志（团队领导/用户复现记录）

---

> 文档维护：本文档随 G1-G8 修复推进逐步减少条目（标记为 ✅）；新增问题按格式追加。