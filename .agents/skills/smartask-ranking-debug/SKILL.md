---
name: smartask-ranking-debug
description: >
  SmartAsk 排名/TopN/层级 Overview 类问数效果异常时的快速排查与定位。
  适用于：用户问「前N的业务承接人/业务部/分公司/代表处」「X层级的业绩咋样」
  「X节点下的Y层级」等问题，但返回行数不对、标题重复/截断、层级被覆盖、
  层级 Overview 没走 ranking、前三问题误走 drilldown、0% 显示相对领先、
  非对比问题出现「本次对比」文案、垫底/落后等口语化数量未被识别等场景。
  当用户反馈「问的是前三，但返回了全部」「标题出现重复文本」
  「城市分公司的业绩咋样没走排名」「0% 怎么还相对领先」「没问对比怎么出现对比」
  「垫底 3 家怎么返回了全部」「业绩最差怎么一条都没返回」时触发使用。
---

# SmartAsk 排名类问题排查

## 环境假设

- 后端容器：`smartask-backend`，端口 `5002`
- 代码目录（容器内）：`/app/backend`
- 本地代码目录：`backend/`
- 认证文件：`config/auth_tokens.json`，可取 super_admin token 直接调用 API
- 关键文件：
  - `backend/four_agent_ask.py` — 意图解析、SQL 生成、confirm 流程
  - `backend/dataset_report_config.py` — 默认 ranking policy 配置
  - `backend/report_spec_builder.py` — 报告契约、answerSummary 文案
  - `backend/tests/test_ecommerce_filter_intent.py` — 电商承接人相关回归测试
  - `backend/tests/test_query_intent_metrics.py` — 消费者/商用意图识别回归测试
  - `frontend/src/components/smartask/ResultDigestCard.vue` — 结果展示、分组、标签、对比模板
  - `config/confirmed_behaviors_baseline.md` — 已确认效果基线

## 快速复现脚本

容器内已内置复现脚本 `backend/scripts/simulate_ranking_ask.py`：

```bash
cd smartask
docker exec smartask-backend python /app/backend/scripts/simulate_ranking_ask.py "看下前三的业务承接人" 62
```

输出示例：
```text
question: 看下前三的业务承接人
display_title: 排名前3的承接人
row_count: 3
sql tail: ... ORDER BY 总任务达成率 DESC LIMIT 3;
query_intent: {"intent": "ranking", "target_level": "承接人", "top_n": 3, ...}
```

关键观察项：
- `question` 是否还是用户原话（不应被改写成 `XX的业绩`）
- `intent` 是否为 `ranking`，`top_n` 是否正确
- SQL 是否包含 `LIMIT N`
- `display_title` 是否简洁无重复

重点关注：
- `question` 是否还是用户原话（不应被改写成 `XX的业绩`）
- `intent` 是否为 `ranking`，`top_n` 是否正确
- SQL 是否包含 `LIMIT N`
- `display_title` 是否简洁无重复

## 排查清单

### 1. 层级是否命中目标层级？

检查 `intent.target_level`：
- 电商「业务承接人/承接人/负责人/任务承接人」应收敛为 `承接人`
- 商用/消费者「分公司/代表处/业务部/业务代表/城市公司」应匹配对应层级

若层级错误，检查 `four_agent_ask.py`：
- `_resolve_query_intent` 中 `resolve_target_level_from_text()` 之后是否被电商/通用别名兜底覆盖
- `_build_ecommerce_sql.infer_user_level` 中是否有硬兜底

### 2. 返回行数不是 TopN？

若 `intent.intent != "ranking"` 或 `top_n` 为 null：
- 检查 `question` 在 ask/confirm 后是否被改写（常见：`_looks_like_org_subject_question` 把 ranking 问题误当组织主体重写）
- 检查 `_rank_request_spec` 是否解析出 `limit`
- 检查 ranking policy triggers 是否包含对应触发词

若 `intent` 正确但 SQL 无 LIMIT：
- 检查 `_build_ecommerce_sql` / `_build_consumer_business_sql` / `_build_syyb_sql` 的 ranking 分支是否正确读取 `top_n`
- 检查是否走了 agent_generate 分支，模型生成了不带 LIMIT 的 SQL
- 检查用户是否用了口语化表达（如「垫底 3 家」「落后 3 个」），当前 `_rank_request_spec` / `_rank_limit_match` 的正则未覆盖这些词

### 3. 标题重复或截断？

- `display_title` 由 `_build_display_title(question, primary_dataset_result)` 生成
- 若 `question` 已被改写，标题会基于错误文本生成
- 电商 ranking 标题预期格式：`排名前N的承接人`
- 若出现 `的业务承接人的业务承接人` 等重复，通常是 `question` 被改写 + 前端 kicker 拼接导致

### 4. Confirm 后结果失真？

确认流程关键路径：
1. `ask()` → `_looks_like_org_subject_question()` 决定是否重写 `effective_question`
2. `_create_confirmation_session(question=effective_question, route=route)`
3. `confirm_by_boss()` → 重写 `route["refined_query"]` → 调用 `_run_pipeline(question, route, ...)`

常见坑：
- `effective_question` 被 Agent1 重写后丢失原问题关键词
- `route.refined_query` 变成 `XX的业绩`，与 `original_question` 拼接后覆盖 ranking 语义

### 5. 层级 Overview 没走 ranking？

代表问题：
- `城市分公司的业绩`
- `业务部的业绩情况`
- `电商事业部的业绩`

预期：
- `intent=ranking`，`top_n=0`
- `answerMode=ranking`

若变成 `drilldown`/`filter`/`comparison`：
- 检查 `_resolve_query_intent` 是否先命中了 filter 条件（如数值阈值、范围）
- 检查是否被 drilldown 规则（`具体节点 + 目标子层级`）提前拦截
- 检查 `_looks_like_org_subject_question` 是否把问题重写成普通详情

电商根节点特殊口径：
- `电商事业部的业绩` 普通问法应返回直接下级 `业务部`，不是 `事业部` 汇总单行；只有明确 `整体/总体/总览/汇总/全部` 才按事业部整体汇总理解。
- 若左侧卡片没有下级，先用后端直接调用确认 `row_count` 是否为 3、SQL 是否含 `层级级别 = '业务部'`、`report_spec.scope.focusNodeIsLeaf` 是否为 `false`。
- 若后端正常但页面不展示，优先查前端卡片 `ResultDigestCard.vue` 的 `secondaryDrillRows` 分支、浏览器缓存或历史会话旧响应。

注意：
- 当问题同时包含层级词（如 `业务代表`）和 Overview 词（如 `业绩/情况/咋样`）时，即使带了具体人名（如 `业务代表靳锋 的业绩情况`），也会按层级 Overview 走 `ranking/top_n=0`，不会提取单个人名做过滤。这是当前已确认行为。

### 6. 排名问题误走 drilldown？

代表问题：
- `看下前三的城市分公司`
- `前5的业务代表`

预期：
- `intent=ranking`，`top_n` 正确

若 `answerMode=drilldown`：
- 检查 `_resolved_entity_names(context)` 是否被 LLM 解析出错误实体（如把“前三的城市分公司”解析成多个分公司）
- 检查“具体节点+目标子层级” drilldown 规则是否在 ranking 词前拦截
- 修复：确保该规则跳过含排名/TopN 词的问题

### 7. 0% 显示「相对领先」？

排查：
- `ResultDigestCard.vue` 中 `secondaryRelativeTier` 是否按全局 `rate` 排序
- 是否误按 ranking 指标（如任务金额、开单金额）排序分层
- 0% 是否被特殊处理为 `pressure`

### 8. 非对比问题出现「本次对比」文案？

排查：
- `isComparisonDigest` 是否只基于返回行数（`comparisonDigestRows.length >= 2`）判断
- `showComparisonDigest` 是否同时要求问题文本含明确对比词
- 前端收紧后，只有 `对比/比较/差异/和…比/跟…比/与…比/vs` 才走对比模板

### 9. 垫底/落后等口语化数量未识别？

代表问题：
- `消费者事业部，业绩排名垫底的 3 家分公司`
- `消费者事业部垫底的5个城市分公司`
- `倒数前三的分公司`
- `垫底的三个分公司`

预期：
- `intent=ranking`，`rank_sides=bottom`，`top_n=3`
- SQL 应按达成率升序并 `LIMIT 3`
- `垫底/落后 + 的 + 数字/中文数字 + 个/家/名/位` 必须按明确数量解析，例如 `垫底的三个分公司` -> `top_n=3`，不能走“垫底无数量默认 1”
- 若问题没有明确事业部/数据集限定，且多个数据集都通过 `dataset_node_index.json` 支持目标层级，应先返回数据集确认，不得让 LLM 或同义词评分自动选一个
- 后续新增服务商等数据集时，只要节点索引显示它也支持该层级，确认候选应自动扩展，不需要写死商用/消费者

排查：
- 大模型语义拆解是否输出 `ranking_params`
- `_normalize_entity_resolution` 是否正确解析并校验 LLM 返回的 `ranking_params`
- `_run_pipeline` 是否把 LLM 的 `ranking_params` 合并进 `context["resolved_entities"]`
- `_resolve_query_intent` 是否在规则未提取到 `top_n` 时读取 LLM 的 `ranking_params.top_n`
- `config/dataset_node_index.json` 是否存在并包含目标数据集的真实层级/节点；它是事实校验底座
- `route_with_agent1("垫底的三个分公司")` 是否返回 `requires_confirmation=true`、`arbiter_reason=generic_level_requires_confirmation:分公司`，且 `dataset_ids` 覆盖当前所有支持“分公司”的候选数据集
- `ask(question="垫底的三个分公司", preferred_dataset_ids=[...])` 也应释放旧数据集选择并返回确认，不能进入 `agent1.preferred_dataset_bypass`
- `route_with_agent1("上海的情况")` 应在 `上海城市公司`、`上海代表处`、未来的 `上海服务商` 等真实节点之间确认；同一 dataset_id 内多个不同节点也不能视为唯一
- 最终 `top_n` 是否经过 `0-20` 范围校验

若返回全部或只返回 1 条：
- 检查 `_rank_request_spec` 是否把「垫底」仅识别为方向词，没有提取后面的数字
- 检查 `_rank_limit_match` 是否覆盖 `垫底/落后` + 可选 `的` + 数字/中文数字 + `个/家/名/位`
- 检查是否因为 `backend/data/dataset_dimension_profiles.json` 缺失导致旧 Agent1.5 画像链路返回 `source=no_profile`，从而没有 LLM `ranking_params`
- 修复方向不是恢复旧画像当事实源，而是让大模型稳定输出结构化意图，再用 `dataset_node_index.json` 和规则做校验
- 规则可以保留少量业务约定，例如「垫底/最差/最低」无数量时默认 1；但明确数量如「垫底的5个」必须优先保留数量
- 如果新问已经正确但历史记录仍只返回 1 条，检查 `config/smartask_report_history.json`：旧快照可能保存了 `query_intent.top_n=1`。这类过期历史应由 `backend/smartask_report_history_store.py` 拒收/剔除，前端同步时也要清掉 localStorage 中被后端判定为 `stale_history_snapshot` 的本地独有记录。

若后端直接调用会确认，但页面没有确认：
- 检查前端请求是否携带 `selected_dataset_ids` 或会话态 `selectedDatasetId`
- `frontend/src/state/smartAskSession.js` 会在部分连续追问中复用已确认数据集；纯通用层级排名/筛选问题不应复用
- 通用跨数据集层级问题不应被误当作“已确认数据集内的追问”，否则会掩盖真实口径歧义

### 10. 末端个人节点展示错误？

代表问题：
- `商用事业部业务代表靳锋的业绩`

预期：
- `answerMode=drilldown`
- `answerSummary.text` 为「已定位到 靳锋，当前展示其个人业绩指标」
- 前端 KPI 卡片展示：总任务金额、年度开单金额、达成率、剩余任务金额
- 不应出现「下一级 1 个业务代表」

排查：
- 检查 `report_spec_builder.py` 对末端节点是否使用个人业绩文案
- 检查 `ResultDigestCard.vue` 中 `isLeafFocus.value` 分支是否正确展示个人 KPI

### 11. "最X" 没数量时返回 0 条或全部？

代表问题：
- `业绩最差的业务代表` → 预期返回倒数第 1
- `业绩最好的分公司` → 预期返回正数第 1
- `垫底的分公司` → 预期返回倒数第 1
- `业务代表业绩排名` → 预期返回全量排序（不受影响）

排查：
- 检查 `_resolve_query_intent` 是否把 `最好/最差/最高/最低/垫底` 识别为 ranking triggers
- 检查 `_resolve_query_intent` 中"最X"默认 1 的逻辑是否生效
- 检查 `_build_rule_based_sql` / `_build_syyb_sql` 的 ranking 分支是否优先使用 `query_intent.top_n`
- 检查 LLM 补漏的 `ranking_params.top_n` 是否会覆盖"最X"默认 1（应仅在没有 LLM 数量时才默认 1）

## 修复后必做

1. 更新/新增单元测试 `backend/tests/test_ecommerce_filter_intent.py`
2. 跑全量测试：
   ```bash
   docker exec smartask-backend python -m pytest tests/ -q
   ```
3. 重建后端镜像：
   ```bash
   docker compose up -d --build backend
   ```
4. 用上面的复现脚本验证效果
5. 更新 `config/confirmed_behaviors_baseline.md` 记录新约束

## 架构口径：模型拆解 + 节点索引校验

排名、TopN、层级 Overview 和下钻类问题的长期方向：

- 大模型负责自然语言拆解，输出结构化意图：`intent`、`target_level`、`top_n`、`rank_sides`、`direction`、`metric_hint`、候选节点。
- `config/dataset_node_index.json` 是真实节点、层级、别名、叶子节点的事实底座；飞书同步成功后按受影响数据集重建。
- 规则负责校验而不是主理解：schema、范围、权限、SQL 安全、节点/层级是否存在、冲突裁判。
- `backend/data/dataset_dimension_profiles.json` 是旧语义画像增强；可以辅助别名或集合口径，但不能覆盖节点索引，也不能成为 TopN 数量识别的必要条件。

已落地的关键函数：
- `four_agent_ask.py::_resolve_question_entities_with_node_index`：旧画像缺失时，基于节点索引/字段层级让 LLM 输出结构化 `ranking_params`。
- `four_agent_ask.py::_node_index_subject_names_from_question`：用节点索引识别真实主体，覆盖“东西部”“东部西部分公司”等旧画像依赖场景。
- `four_agent_ask.py::_node_index_members_by_level`：用节点索引判断业务代表/业务员等末端成员，避免叶子节点误下钻。
- `smartask_advanced/skills/dataset_route.py::_node_index_supported_levels`：路由评分缺少旧画像时，从节点索引判断数据集是否支持代表处/城市分公司等层级。

## 参考

- 已踩过的具体坑与修复记录：见 [references/common-pitfalls.md](references/common-pitfalls.md)

## 审计发现（2026-08-06，详见 docs/audit/2026-08-06_final-audit-report.md）

### B4：行级权限外层包裹对排名 SQL 无效（P0）

排名 SQL（`ask_engine_sql.py:36-47` `_build_ranked_select_sql`）的执行序为：

```
全域排名（ROW_NUMBER OVER 全部行）
→ 全域截断 TopN（WHERE 全局排名 <= N + LIMIT N）
→ 才按用户权限过滤（外层 SELECT * FROM (...) WHERE 权限条件）
```

权限包裹发生在最外层（`data_permission_store.py:514`），排名在全域数据上计算，TopN 在全域上截断，**然后**才过滤。

产生两条泄露/失真路径：

**路径 A：排名序号本身跨域泄露**
`SELECT *` 把 `全局排名`（双向模式下还有 `前排名`/`后排名`/`排名分组`）带进结果。用户即使只看到本部门行，也能读到该行的全公司排名值——"全局排名 = 47"即可推知全公司至少有 46 个同级单位业绩优于自己。行级权限过滤了行，没过滤聚合量。

**路径 B：TopN 语义塌缩**
用户问"前10的代表处"，内层先取全公司前10，外层再按权限滤成可见部分。若用户部门无人进全公司前10 → 返回零行 → 落入静默降级族 → 显示"未查询到匹配数据"。正确语义应是"用户可见范围内的前10"，实际给出的是"全公司前10 ∩ 用户可见范围"，两者在非超管账号下不等价。

**修复方向**：权限谓词必须下推到最内层事实表扫描（在 `source_cte` 的 WHERE 内），使排名在授权子集上计算。外层包裹方案对任何含窗口函数或聚合的 SQL 都不成立。

### B5：达成率分母为零显示 0%（P1）

`four_agent_ask.py` 多处（`:4881` / `:5471` / `:5497` / `:6108`）在节点 `总任务金额=0` 但有实际开单额时，`ELSE 0` 把"没派指标的单位"报成"达成率 0%"。

后果：该节点在"达成率最低 TopN"中稳定占榜首，把"没派指标的单位"报成"业绩最差的单位"。用户不可察觉。

**修复方向**：分母为 0 返回 NULL 而非 0，排序 `NULLS LAST`，展示层区分"—"与"0%"。

### 关于 dataset_dimension_profiles.json

本 skill §9 提到"检查是否因为 `backend/data/dataset_dimension_profiles.json` 缺失导致旧 Agent1.5 画像链路返回 `source=no_profile`"——审计 A-02 确认该文件确实不存在，31 个调用点全部拿到 None。

补文件时注意：补的文件只含同义词映射和集合口径增强，不含节点层级关系定义。节点关系以 `config/dataset_node_index.json` 为唯一事实源。详见 `smartask-runtime-migration` skill §9.4。
