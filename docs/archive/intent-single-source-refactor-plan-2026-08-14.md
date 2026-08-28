# SmartAsk 结构化意图单一真相源 · 改造方案 v1.0

> 日期：2026-08-14 ｜ 产出：架构师 + 后端 + QA + 数据工程师 4 角色并行
> 目标：把"三层意图判断各自为政"收敛为"LLM 结构化拆解 = 单一真相源"，恢复 aggregate / comparison / overview / ranking 等意图的灵活识别，**只动问数链路，不碰飞书 sync / 部署 / 登录**。

---

## 〇、一句话病根

你的设计本意（LLM 结构化拆解意图 + 提取维度给下游）是对的，代码里 `Agent1.5` 的 prompt 就是铁证。走偏在**两处**：
1. **主体重写越界**：`_agent1_resolve_org_subject` 生成 `rewritten_question="{subject}的业绩"`，0801 之后 `route_question=effective_question` 让这个简化版替换了原始问题，把意图信号抹掉了。
2. **三层意图判断各自为政**：Agent1.5（LLM 结构化）→ IntentResolver（规则+配置）→ SQL 生成器（正则），各判各的，结构化结果拆出来没人消费。

---

## 一、目标态架构（架构师）

```
原始问题 question
  │
  ▼
[阶段0] 主体纠正 _agent1_resolve_org_subject  —— 只纠"主体"，输出 subject_name + metric_hint
        （禁止：产出 rewritten_question 替换全文、动 intent）
  │
  ▼
[阶段1] Agent1.5 LLM 结构化拆解  —— 意图的【单一权威】
        输入 question + 节点索引；输出 QueryIntentSignals
  │
  ▼
[阶段2] IntentResolver  —— 【校验 + 配置 + 兜底】，不重判
        ① 枚举/边界/实体合法性校验 ② 配置短路 ③ LLM 失败→规则产出(source=rule)
  │
  ▼
[阶段3] SQL 生成器  —— 【纯翻译，零意图判断】
        只读 QueryIntentSignals → 翻译成 SELECT/LIMIT/ORDER BY/WHERE
```

**数据流铁律：意图只被判断一次（阶段1），阶段2只"校正"不"重判"，阶段3只"翻译"不"判"。**

### QueryIntentSignals 统一契约

| 字段 | 类型 | 来源 | 消费 |
|---|---|---|---|
| `intent` | compare/single/aggregate/ranking/filter/overview/unknown | LLM(权威)+Resolver 补 filter/overview | SQL 模板选择 |
| `scope_mode` | 同上 | LLM | Resolver 校验、路由 |
| `target_level` | str | LLM + Resolver 规则 | SQL 层级过滤 |
| `rank_limit` | `{top_n, rank_sides:top/bottom/both, unspecified}` | LLM ranking_params | SQL LIMIT |
| `direction` | asc/desc | LLM | SQL ORDER BY |
| `metric` | `{key,column,label}` | LLM metric_hint + Resolver 词表 | SQL 排序/聚合列 |
| `filter` | `{metric,operator,value,unit}` | Resolver(规则) | SQL WHERE |
| `entities` | `[{dimension_name,members,matched_phrase}]` | LLM | SQL 节点过滤 |
| `has_specific_node` | bool | LLM | 层级 Overview 判定 |
| `source` | llm/rule/fallback | Resolver 标记 | 调试/灰度 |

> ⚠️ **关键缺口**：LLM prompt 枚举（`four_agent_ask.py:2591/2686`）目前只有 `compare|single|aggregate|ranking|unknown`，**缺 `filter`/`overview`** —— 契约必须补枚举，否则这两类永远进不了 LLM 权威。

### 收敛策略：推荐【渐进】

结构化字段为主 + SQL 正则做 feature-flag 兜底（灰度），理由：9300 行上帝文件的正则承载大量长尾（`asks_best_branch` 取1条、头尾对比等），LLM 尚未全覆盖，激进废弃会大面积回归。

---

## 二、改造清单（后端，行号级）

### 前置关键事实
- `resolver.py` / `ask_engine_entity.py` / `short_term_memory.py` 是**共享模块**，问题 2/3/4/6 改一处即全局生效。
- ⚠️ **双文件红线**：存在 `four_agent_ask_container.py`（容器版副本，未跟踪）。问题 1/5 涉及 `four_agent_ask.py` 时，**两份必须同步**，否则容器与本地行为分叉。

| # | 问题点 | 位置 | 风险 | 状态 |
|---|---|---|---|---|
| 1 | intent_question 丢信号 | `four_agent_ask.py:8326-8331` + 8767/9033（容器 +3） | 中 | 新增 |
| 2 | level_overview 根节点反例 | `resolver.py:674-684` | 低 | 新增 |
| 3 | ranking.enabled 短路 | `resolver.py:605-606` | 低 | 新增 |
| 4 | 拦截器漏 3 排除项 | `ask_engine_entity.py:98-118` | 低 | **已做未提交** |
| 5 | SQL 层正则各自为政 | `four_agent_ask.py:6104/6344-6366/6442-6469` | 中 | 新增 |
| 6 | 追问词表窄 | `short_term_memory.py:118-125` | 低 | 新增 |

### 问题 1 — intent_question 修复（核心，三处联动）

① 透传原始问题（`four_agent_ask.py` L8767 后加一行）：
```python
raw_question = question          # 锁定本轮原始输入
```
路由分支结束后、权限过滤前（约 L9033）加：
```python
route["raw_question"] = raw_question
```
（确认流程里 `route` 随 `_create_confirmation_session` 持久化，`confirm_by_boss` 用 `dict(pending["route"])` 还原，`raw_question` 自动带过，无需改签名。）

② 重构 intent_question 组装（L8326-8331）：
```python
refined_question = str(route.get("refined_query") or question or "").strip()
raw_question = str(route.get("raw_question") or question or "").strip()
resolved_subject = self._safe_dict(context.get("resolved_subject"))
if resolved_subject.get("subject_name"):          # 主体已纠正（商用事业部丁杰→丁杰）
    intent_question = refined_question or raw_question
else:                                              # 否则以原始问题为主体，保住 aggregate/ranking/compare 信号
    intent_question = raw_question or refined_question
if refined_question and refined_question not in intent_question:
    intent_question = f"{intent_question}\n{refined_question}"
query_intent = self._resolve_query_intent(intent_question, context)
```

三条保证：①无主体纠正时 `intent_question=raw_question`，信号完整；②丁杰案例靠 `resolved_subject.subject_name` 判定 + L8333-8336 强制覆盖 subject，不回归；③多轮追问 `raw_question` 是本轮追问、`refined_query` 含上轮主体被追加，不回归。

### 问题 2 — resolver 根节点反例（L674-684）
反例判定加根节点排除：
```python
if any(name and name not in level_like_values
       and not self.ports.is_dataset_root_name(name, dataset)   # 新增：根节点不关概览
       and any(name.endswith(alias) for alias in target_aliases)
       for name in resolved_names):
    is_level_overview = False
```
（"事业部"层级只有根节点，子层是分公司/业务部，排除精准无副作用。）

### 问题 3 — ranking.enabled 短路（L605-606）
**删除** `if ranking_policy.get("enabled") is False: return intent` 两行。让 `enabled` 只作语义开关、不再阻断解析；`matched_triggers` + `has_ranking_token` 足以判定显式排名。

### 问题 4 — 拦截器 3 排除项（已做未提交）
`ask_engine_entity.py:98-118` 已含 aggregate/comparison/overview 三组排除。动作：确认容器同步 → `git fsck`（仓库有对象损坏）→ commit。

### 问题 5 — SQL 层结构化优先、正则仅兜底
- L6104：`intent_is_ranking = query_intent.get("intent") == "ranking"`，另存 `regex_ranking_hint` 仅兜底。
- L6350-6366 `asks_branch_ranking` / `asks_city_ranking`：正则分支包进 `not intent_is_ranking`。
- L6447-6469 `consumer_rank_limit()`：正则兜底逻辑包进 `if not intent_is_ranking`，避免 resolver 已给 `top_n=0`（概览）时被正则改写。
- `consumer_order_direction` / `consumer_sort_column` 已是结构化优先，不动。

### 问题 6 — 追问词表补指标（`short_term_memory.py:122` 前）
```python
metric_tokens = ("达成率", "完成率", "进度", "多少", "咋样", "怎么样", "如何", "怎样")
org_level_tokens = ("事业部", "分公司", "代表处", "业务部", "城市公司", "业务代表")
if any(t in compact for t in metric_tokens) and len(compact) <= 12 \
   and not any(t in compact for t in org_level_tokens):
    return True
```
（"丁杰业绩→达成率咋样"主体保留；"各分公司业绩咋样"不误判。）

---

## 三、Phase 迁移顺序

| Phase | 内容 | 依赖 | 风险 | 回滚 |
|---|---|---|---|---|
| **P0** | commit 工作区拦截器排除（问题4） | 无 | 低 | git revert |
| **P1** | resolver 根节点 + 删 enabled 短路（问题2/3） | 无 | 低 | resolver.py 单文件 revert |
| **P2** | intent_question 修复 + raw_question 透传（问题1） | P1 | 中 | 双文件一起 revert |
| **P3** | SQL 层结构化消费（问题5） | P1（需结构化 ranking 字段） | 中 | 双文件 revert |
| **P4** | 追问词表扩列（问题6） | 无 | 低 | 单文件 revert |

**顺序**：P0 → P1 → P2 → P3 → P4（P0/P1/P4 可并行先行；P2/P3 依赖 P1 的结构化输出）。

---

## 四、配置 / 数据层收敛（数据工程师）

### 1. ranking.enabled 统一
**推荐 SQL-2**（删显式 false，回退默认 true）：
```sql
UPDATE bs_dataset_report_config
SET config_json = config_json #- '{intentPolicies,ranking,enabled}', updated_at = NOW()
WHERE dataset_id = 2
  AND config_json #> '{intentPolicies,ranking,enabled}' IS NOT NULL;
```
**防再不一致**：`app.py` 加启动期 `_ensure_ranking_policy_consistency()` 只读告警（不自动改数据）。

### 2. get_dataset_profile 静默失效
**推荐 B（立即）+ 逐步收敛到 A（长期）**：
- **B**：`load_dataset_profiles()` 在 json 不存在时，从 `config/dataset_node_index.json` 兜底重建画像（levels 映射自 nodes），并**清掉 `@lru_cache(maxsize=1)`** 或改 mtime 缓存 key（否则飞书同步重建索引后缓存不刷新）。
- **A（终态）**：确认 group/compound 能力迁入节点索引后，删掉 profile 语义函数。

### 3. 数据健康常态化
- 电商"刘志伟"6 同名节点：**代码层 (name,parent) 联合处理，不做数据 dedup**（是"一人多细分业务"真实语义）。
- 商用 synonym 缺排除代词：**不塞进 synonym 表**（那是正向权重表），在打分处加排除词处理。

### 4. 影响面
所有改动**不影响**飞书 sync / 部署 / 登录；get_dataset_profile 方案 B 与飞书同步有轻微耦合（需缓存失效），已在方案内处理。

---

## 五、验证矩阵（QA，18 case）

> 试金石：**A1-A3（aggregate）/ C1-C3（comparison）/ O1-O3（overview）** 的 `scope_mode` 必须分别落 `aggregate` / `compare` / `ranking(top_n=0)`，**绝不允许落 unknown**。

| # | 数据集 | 问题 | 期望 | 关键断言 |
|---|---|---|---|---|
| R1 | 商用3 | 看下前三的业务代表 | ranking | top_n=3, direction=desc, target=业务代表, LIMIT 3 |
| R2 | 消费者2 | 消费者事业部垫底的5个城市分公司 | ranking | top_n=5, rank_sides=bottom, direction=asc |
| R3 | 电商62 | 看下前三的业务承接人 | ranking | top_n=3, 层级=承接人 |
| F1 | 商用3 | 低于10%的业务代表 | filter | filter_metric=达成率, op=<, value=10 |
| F2 | 消费者2 | 达成率低于50%的城市分公司 | filter | 阈值 + 层级=城市分公司 |
| F3 | 电商62 | 国内业务部完成超过500万的 | filter | 下钻到承接人子层 |
| C1 | 商用3 | 东部分公司和南部分公司的业绩对比 | comparison | scope=compare, 成员[东,南] |
| C2 | 消费者2 | 河北分公司和山东分公司的业绩对比 | comparison | scope=compare |
| C3 | 电商62 | 国内业务部和跨境业务部的业绩对比 | comparison | scope=compare |
| A1 | 商用3 | 每个分公司的平均达成率 | aggregate | scope=aggregate, has_specific_node=false |
| A2 | 消费者2 | 各分公司的平均达成率 | aggregate | scope=aggregate |
| A3 | 电商62 | 各业务部的平均达成率 | aggregate | scope=aggregate |
| D1 | 商用3 | 东部分公司的业务代表 | drilldown | 父=东部分公司, 子=业务代表 |
| D2 | 消费者2 | 江浙沪分公司的城市分公司 | drilldown | target=城市分公司 |
| D3 | 电商62 | 国内业务部的业务经理有哪些 | drilldown | 子=承接人 |
| O1 | 商用3 | 业务部的业绩情况 | overview | top_n=0 全量, 无 LIMIT |
| O2 | 消费者2 | 城市分公司的业绩咋样 | overview | top_n=0 全量 |
| O3 | 电商62 | 业务部的业绩情况 | overview | top_n=0 全量 |

### 回归红线（绝不能破坏）
- **§1.4** 电商根节点默认带下级（`电商事业部的业绩`→3 业务部，非事业部单行）
- **§2.7** 最X默认1条（`业绩最好的分公司`→top_n=1）
- **§2.5** 排名不被 drilldown 拦截
- **§3.3** 多轮追问沿用（命中唯一节点不再弹确认）
- **商用整体业绩**（268440c 已修，不误下钻）
- **§8.3** 多轮 hint 跨数据集冲突检测（东部分公司案例）

### 验收标准（三层闸门）
- **L1 白盒**：读 `resolved_entities.scope_mode/ranking_params` 断言结构化输出本身正确
- **L2 黑盒**：读最终 SQL（LIMIT/WHERE/ORDER BY）+ rows 层级分布
- **L3 交叉一致性**：L1 与 L2 必须一致（scope=ranking+top_n=3 ⇒ SQL LIMIT 3）

验证脚本骨架：`backend/scripts/qa_intent_matrix.py`（容器内 `four_agent_ask_service.ask()` 跑 18 case + 多轮，打印 route/query_intent/resolved_entities/SQL LIMIT/rows 层级）。

---

## 六、执行红线汇总

1. **双文件同步**：问题 1/5 改 `four_agent_ask.py` 时，`four_agent_ask_container.py` 必须同改（行号 +3），否则容器与本地分叉。
2. **git 先 fsck**：仓库存在对象损坏（`unable to read f62f861...`），commit 前先 `git fsck`。
3. **P3 依赖 P1**：SQL 层结构化消费需要 resolver 先产出结构化 ranking 字段，不可跳序。
4. **不碰其他功能**：所有改动仅限 `four_agent_ask.py` / `resolver.py` / `ask_engine_entity.py` / `short_term_memory.py` + 1 条 DB UPDATE，飞书/部署/登录零接触。
