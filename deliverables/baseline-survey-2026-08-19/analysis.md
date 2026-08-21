# 基线拓展全量实测 — 专家团根因分析（2026-08-19）

> 数据基础：`report.md`（204 用例 / 238 轮次实测，PASS 170 / FAIL 21 / INFO 13）。
> 本文件由 4 个后端排查专家并行分析 21 题 FAIL 后汇总，全部根因经容器内只读实证。
> 纯分析，未改任何代码。

## 判定总览

| 簇 | 用例 | 判定 | 根因位置 |
|---|---|---|---|
| B 电商承接人个人 | B11/13/15/17 | **新 bug**（G5 修复漏网分支） | `four_agent_ask.py:6290-6311` ranking 分支丢弃 focus_member |
| C 业务部对比 0 行 | C05/06 | **新 bug** | `four_agent_ask.py:5611-5612`（及 5595/5700 兄弟分支）按恒空的 `业务部` 列过滤 |
| D 跨数据集对比 0 行 | D01/02/03/04 | **已知 backlog（§1.2.2 未落地）**，本次定位到具体机制 | `organization_route_resolver.py:360` 整句复制 + `four_agent_ask.py:5919` 层级值错误 + `:5613-5615` 短别名 + `:6139` 守卫条件过窄 |
| E10 drilldown 层级错位 | E10 | **新 bug**（三缺陷叠加，15-30% 概率退化） | `resolver.py:50` `\b` 对中文失效 + `four_agent_ask.py:8759` 后缀污染 + `:7822` LLM 重写丢子层级 |
| G "各X的" intent=aggregate | G03/04/06/08 | **产品裁决点**（数据全对，仅 intent 标签与排序不同） | `resolver.py:220-249` aggregate 分支优先于 level_overview（663）且互斥 |
| G05 代表处混入 95 行 | G05 | **新 bug**（golden sample 劫持 + 守卫有洞） | ChromaDB 样本 id=2635 + `four_agent_ask.py:1480` 守卫对纯层级问法放行 |
| G07 业务代表 0 行 | G07 | **新 bug**（100% 必现） | `four_agent_ask.py:5247-5262` 业务代表手写分支 `rank_limit=0` → `WHERE 全局排名<=0 LIMIT 0` |
| G09/K01/K04 confirm 后 3 行 | G09、K01、K04 | **已知 bug#14/#17 残留面** | `four_agent_ask.py:8828/8868` SQL 构建仍吃带"补充确认…先汇总后分析"后缀的 refined_query，"后"字命中 ranking token → rank_limit=3 |
| L07 山东裸节点未确认 | L07 | **新 bug** | `organization_route_resolver.py:302` single_clear_node 抢跑直出 + 组织树不含代表处级节点 + `:204-205` org_tree 模式跳过节点索引 |

## 分簇详情

### 1. B 簇：电商承接人个人业绩返回全量排名（新 bug）

- 调用链：resolver.py:182「承接人→target_level」→ 663-720 level_overview → intent=ranking/top_n=0 → `_build_ecommerce_sql`。
- **丢点**：`four_agent_ask.py:5954-6004` 已正确解析出具体人名（focus_member='黄超'），但 6225-6361 分支顺序中 ranking(6290) 先于 focus_member(6341) 命中，且 ranking 分支只在 focus_dimension=='业务部' 时才用 focus_member —— 承接人维度的人名被静默丢弃。
- 商用侧（靳锋等）能 PASS 是因为 ds=3 最终 intent=unknown，走实体分支有 `业务代表 IN (...)` 锁定（:4861-4862），两侧不对称。
- 黄超连 11 行里都没有：PG 实证黄超 2026 年仅 1 行且 `层级级别='业务部'`（国内业务部负责人），不是业务经理，被 ranking 的 `层级级别='业务经理'` 过滤排除。
- 这就是 G5 修复（commit 6f06f57，修了 focus/compare 分支）的未修孪生分支。
- **最小修复**：6290-6311 ranking 分支内，focus_member 非空且维度∈{承接人/任务承接人/负责人/业务经理} 时追加 `负责人 = 'X'`（不要加层级级别过滤——黄超是业务部级）。

### 2. C 簇：业务部对业务部对比 0 行（新 bug）

- `four_agent_ask.py:5611-5612` 对比分支按后缀分派：实体以「业务部」结尾 → 生成 `业务部 = '{name}'`。
- 但 ds=3 数据字典无 `业务部` jsonb_key，base SQL 把业务部提取替换成 `'' AS 业务部`（:4697-4701）→ **该列恒空**，0 行是必然。
- 真实值在 `分公司` 字段（分公司='公共办公业务部'）；单对象路径能出数是靠递归 CTE 按 `节点名称` 匹配。
- 基线 §1.2 代表题（东部/南部分公司对比）能过，只是因为分公司列有真实值 + :5839-5845 还有硬编码特判。
- **最小修复**：5611-5612（连同 5595-5596、5700-5701）改为按 `节点名称` 匹配。

### 3. D 簇：跨数据集对比一侧/两侧 0 行（已知 backlog，机制新定位）

- **路由层未拆句**：`organization_route_resolver.py:360` 给每个数据集的 sub_query 都是同一句原话（§1.2.2 要求拆成逐数据集主体查询）。
- ds=3 两个 0 行陷阱（新定位）：
  - `:5916-5919` 兜底 `WHERE 层级 = '{intent_target_level}'`，直接用了节点名「商用事业部」当层级值（值域应为 事业部/分公司/…）；4716-4724 已有正确的别名→层级映射（actual_sy_level_value）但兜底没用它。
  - `:5613-5615` 短别名（'商用'/'电商'）直接拼 `节点名称 = '商用'` → 恒 0 行（真实节点名是「商用事业部」）。
- ds=62：`:6139` 自引用守卫只在 `intent == "comparison"` 时触发，LLM 抽到 drilldown/None 时守卫失效（抖动性失败）。
- **治本**：resolver.py:344-361 按数据集生成各自 sub_query；**治标**：5919 用 actual_sy_level_value、5613/6524 短别名先归一全名、6139 放宽为 is_comparison。

### 4. E10：「南部分公司下面业务代表的业绩」层级错位（新 bug，三缺陷叠加）

- 缺陷 A：`resolver.py:63/93` 用 rfind 找层级词，refined_query 后缀「组织树标准名称：南部分公司…」里的"分公司"位置最靠后，压过题干的"业务代表" → target_level 恒为分公司。
- 缺陷 B：`resolver.py:50` child-level 快路径正则的 `\b` 对中文失效（"表"与"的"都是 \w），永远匹配失败。
- 缺陷 C（随机性）：`_agent1_resolve_org_subject`（:7822）LLM 重写为空时套模板 `{subject}的{metric}`，「下面业务代表」被丢弃 → 退化成「南部分公司的业绩」→ 7 行。13 次采样约 15-30% 退化。
- 对照：「南部分公司的业务代表」句式确定性 PASS（27 行）。
- **最小修复**：① resolver.py:50 去 `\b` 改 `(?=$|[^\u4e00-\u9fa5])`；② 8759 意图解析剥离后缀行；③ 7822 重写前保留「下面+层级词」片段。

### 5. G 簇「各X的」intent=aggregate（产品裁决点，非缺陷）

- `resolver.py:220-249`：「各/每个/分别」命中 aggregate_tokens → 提前 return aggregate；level_overview（663-720）前提 `not asks_aggregate` → 互斥不可达。
- **数据全对**（69/25/82 行齐全），实际影响仅两点：排序按开单金额而非达成率；前端 ranking 专属展示（风险 pill、榜首/末位卡片、排名列表标题）不生效。
- 基线 §2.4 原文前提是「无聚合关键词」，代表问题里没有「各X的」句式——这是锚点外推。**需产品裁决**：接受 aggregate 口径（放宽锚点）或让 level_overview 接管。

### 6. G05「代表处的业绩咋样」混入 95 行（新 bug）

- ChromaDB golden sample id=2635（原问题「分析下河南代表处的业绩」）以 score=70 走 sample_direct 直通；该样本 SQL 为具体节点写的 `LIKE '%代表处%'` 模糊匹配，对纯层级问题拉出 25 代表处+全部业务代表 ≈95 行。
- **bug#1 守卫（:1466-1492）就是为这个失败模式写的**，但 `:1480` `if not requested: return False`——纯层级问法没有具体节点名 → 守卫放行。**守卫只挡点了具体节点的问法，挡不住 §2.4 场景。**
- 附带：样本 2635 对自己的原问题也返回 95 行，本身就是坏样本，建议数据侧清理。
- **最小修复**：守卫扩展——纯层级 Overview 意图时 LIKE '%层级词%' 样本同样视为劫持，弃样本走规则 SQL（规则库代表处全局排序分支 5284-5302 行为正确）。

### 7. G07「业务代表的业绩」0 行（新 bug，100% 必现）

- level_overview 契约 top_n=0=全量，但 `four_agent_ask.py:5247-5262` 业务代表全局/分组两个手写内联 SQL 分支直接 `WHERE 全局排名 <= 0` + `LIMIT 0` → 0 行。
- 兄弟代表处分支（5279-5283）和公共函数 `_build_ranked_select_sql`（ask_engine_sql.py:49-51）都有 `rank_limit=0 → LIMIT 10000` 守卫，**唯独业务代表这两个手写分支漏了**。
- **最小修复**：复用 `_build_ranked_select_sql` 或照抄代表处分支守卫，一处改动。

### 8. G09/K01/K04：confirm 后行数缩成 3（已知 bug#14/#17 残留面）

- 意图侧已修（:8736-8739 剥离后缀再送 resolver），**SQL 侧没修**：`:8828` `_select_sql_strategy` 和 `:8868` `_agent2_generate_sql` 仍传带后缀的 `route["refined_query"]`。
- 后缀「输出方式：先汇总后分析」的"后"字被两个 SQL 引擎的裸 token 匹配命中 → `rank_limit=3`（消费者 ASC 取倒数 3 名、商用 DESC 取前 3 名截掉西部）。
- **最小修复**：8828/8868 两处改传剥离后的问题文本（复用 8739 已算出的 `refined_for_intent`），不动引擎 token 列表。
- 注意：K02（垫底的三个分公司）、K03（前3的分公司）、I06-I08（最好/垫底/最差的分公司）本轮已 PASS——它们题干自带明确数量词，top_n 已被题干锁定，后缀影响被覆盖；只有「无数量的通用分公司问法」（G09/K01/K04）仍被后缀劫持。

### 9. L07「山东的业绩」裸节点未弹确认（新 bug）

- `route_with_agent1` 先调 OrganizationRouteResolver，命中即 return（:3899-3909），轮不到后面的节点索引多命中确认路径。
- 三叠加：① 组织树只有 26 节点、最深 level 2，「山东代表处」不在树里；② `_node_aliases('山东分公司')` 派生别名「山东」→ 唯一命中 ds=2；③ resolver 的节点索引兜底（:204-205）跳过 org_tree 模式数据集 → 山东代表处在 resolver 视野中不存在 → single_clear_node 直出（score 98）。
- 「上海」历史上弹确认纯属侥幸（组织树里没有任何上海节点，resolver 返回 None 才落到正确路径）。
- 节点索引本身完备：`_node_index_matches('山东')` 实测双命中（2:山东分公司，3:山东代表处）。
- **最小修复**：:302 single_clear_node 直出前，用 matched_alias 对 flat_alias_index 做跨数据集冲突检查，多命中则返回 None 交给节点索引确认路径。

## 修复优先级建议

1. **P0（数据错误/问不出）**：G07（0 行必修）、C 簇（0 行）、D 簇（0 行）、G09/K01/K04（confirm 后缀污染 SQL）
2. **P1（结果缺层级/不确认）**：B 簇、E10、L07、G05
3. **产品裁决**：G03/04/06/08「各X的」intent 口径
4. **数据侧**：清理 golden sample 2635
