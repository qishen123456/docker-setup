---
name: smartask-ranking-debug
description: >
  SmartAsk 排名/TopN 类问数效果异常时的快速排查与定位。
  适用于：用户问「前N的业务承接人/业务部/分公司/代表处」等排名问题，
  但返回行数不对、标题重复/截断、层级被覆盖、confirm 后结果失真等场景。
  当用户反馈「问的是前三，但返回了全部」或「标题出现重复文本」时触发使用。
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
  - `backend/tests/test_ecommerce_filter_intent.py` — 电商承接人相关回归测试
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
