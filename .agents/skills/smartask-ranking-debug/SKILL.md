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

预期：
- `intent=ranking`，`top_n=0`
- `answerMode=ranking`

若变成 `drilldown`/`filter`/`comparison`：
- 检查 `_resolve_query_intent` 是否先命中了 filter 条件（如数值阈值、范围）
- 检查是否被 drilldown 规则（`具体节点 + 目标子层级`）提前拦截
- 检查 `_looks_like_org_subject_question` 是否把问题重写成普通详情

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
- `倒数前三的分公司`

预期：
- `intent=ranking`，`rank_sides=bottom`，`top_n=3`
- SQL 应按达成率升序并 `LIMIT 3`

排查：
- Agent1.5 的 prompt 是否已要求输出 `ranking_params`
- `_normalize_entity_resolution` 是否正确解析并校验 LLM 返回的 `ranking_params`
- `_run_pipeline` 是否把 LLM 的 `ranking_params` 合并进 `context["resolved_entities"]`
- `_resolve_query_intent` 是否在规则未提取到 `top_n` 时读取 LLM 的 `ranking_params.top_n`
- 最终 `top_n` 是否经过 `0-20` 范围校验

若返回全部：
- 检查 `_rank_request_spec` 是否把「垫底」仅识别为方向词，没有提取后面的数字
- 检查 `_rank_limit_match` 是否只支持 `前/后/倒数/最高/最低/第` + 数字，未覆盖 `垫底/落后`
- 修复方向：规则优先，LLM 补漏；或在正则中把 `垫底/落后` 作为 `后N` 同义表达处理

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

## 参考

- 已踩过的具体坑与修复记录：见 [references/common-pitfalls.md](references/common-pitfalls.md)
