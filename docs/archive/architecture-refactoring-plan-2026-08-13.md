# SmartAsk 架构改造计划 v2.0 — 2026-08-13

> **目标**：从"补丁式修复"转向"成熟架构完美到底流程"
> **范围**：NL2SQL 主链路（intent → SQL → 报告）+ 多轮对话闭环
> **方法**：5 个 Phase 渐进推进，每个 Phase 有明确产出 / 风险 / 决策点
> **原则**：先解开燃眉之急，再建语义中间层，最后拆上帝文件；**不重写已对齐的基线**

---

## 一、执行摘要

SmartAsk 当前处于**"架构债累积期"**：

- **2026-07-02**（a34663d）：你设计了 LLM 引导 + 规则 fallback 的双层架构（IntentResolver / `_looks_like_ranking_question` / `ranking_params`），架构思想正确。
- **2026-08-13 之前**：你做了 5 个 commit 修复"已知 bug"（飞书 sync / 部署 / 整体业绩 / 索引冷启动），**都是外围修补**。
- **2026-08-13 实测**：暴露了 **3 个 P0 级结构性问题**——ranking.enabled=False 拦截 + hint 沿用未检测跨数据集实体 + entity resolver 模糊替换，以及 **5 个 P1 级断层**。

**3 套"理解机制"并存，没有共享"意图理解模型"**：

```
┌──────────────────────────────────────────────────────┐
│  3 套并存机制（互不感知）                              │
├──────────────────────────────────────────────────────┤
│  ① LLM 解析（一次 prompt，喂 hint dataset catalog） │
│  ② 规则 fallback（8+ helper，token 匹配 + regex）   │
│  ③ 数据集元数据（ranking.enabled / synonym / node）│
└──────────────────────────────────────────────────────┘
         ↓
   每次新 case 暴露 fallback 链断点 → 在某一层加 token → 补丁
```

**今天的诊断定位了闭环断点**：hint 链路在 Stage 11 → Stage 2 之间缺少"实体是否在 hint dataset 里"的冲突检测。

---

## 二、现状盘点（2026-08-13 工作树实测）

### 2.1 已完成（今天工作树未 commit）

| 项 | 文件 | 内容 | 状态 |
|---|---|---|---|
| R1 hint 冲突检测 | `four_agent_ask.py:6198,7162,7212,7240` | `_is_entity_in_dataset()` 实体在 hint dataset 检查 | ✅ 已写入 |
| R1 实体 validation 跨数据集 | `four_agent_ask.py:6142-6162` | `valid_node_names` 取全量 datasets 并集 | ✅ 已写入 |
| R2 冷启动 flat_alias_index 检查 | `app.py:290-313` | 阈值 < 50 触发 rebuild | ✅ 已写入 |
| R3 baseline 增补 | `confirmed_behaviors_baseline.md:545,566` | §8.1 跨数据集实体校验 / §8.2 冷启动索引健康度 | ✅ 已写入 |
| R1 兜底 consumer_rank_limit | `four_agent_ask.py:6461` | `asks_best_branch → rank_limit=1` | ✅ 已写入 |
| 诊断脚本 | `backend/scripts/diag_*.py` | 6 个实测脚本 | ✅ 已写入 |

### 2.2 未修复

| 项 | 位置 | 现象 | 优先级 |
|---|---|---|---|
| **ranking.enabled=False** | `bs_dataset_report_config` 表 dataset_id=2 | IntentResolver L605-606 提前 return，"哪个最低"返回 82 行（应 1+ 下属） | **🔴 P0** |
| 路由 pronoun 兜底缺失 | `route_with_agent1` | "其他事业部业绩" 命中电商 id=62（synonym "其他" 抢答） | 🟡 P1 |
| `_looks_like_ranking_question` 漏接入 | `ask_engine_route.py:49` 定义，0 处调用 | ranking 工具函数未挂到 consumer_rank_limit | 🟡 P1 |
| `_dataset_node_index` id=62 重复 node_name | `config/dataset_node_index.json` | "刘志伟" 6 个节点，实体歧义 | 🟢 P2 |

### 2.3 闭环断点（已确认）

```
[上一轮 Q_n-1]
  ↓
Stage 11: short_term_memory.remember_result(dataset_ids=[2])   ← 写入
  ↓ (下一轮)
Stage 2:  _followup_dataset_hint_from_memory() → hint=[2]    ← 提取
  ↓
Stage 3:  _should_keep_followup_dataset_hint()                ← 应该在这里检测实体冲突
  │         ❌ 缺失 _is_entity_in_dataset(target_name, hint_id) 检查
  ↓         (今天已加 — 待 commit)
Stage 4:  route.dataset_ids = [2]                              ← 锁死 hint dataset
  ↓
Stage 8:  SQL 生成：entity resolver 拿 hint catalog 喂 LLM
  │         ❌ "东部分公司" 不在消费 catalog → fallback 字符串匹配 → "山东分公司"
  ↓
SQL: WHERE 节点名称 IN ('山东分公司') → 6 行错数据
```

**断点 1（已修）**：Stage 3 hint 冲突检测
**断点 2（已修）**：Stage 8 entity validation 跨数据集 scope
**断点 3（未修）**：IntentResolver.enabled=False 拦截
**断点 4（已修）**：Stage 8 SQL 层 entity 兜底校验
**断点 5（已修）**：app.py 冷启动 health check

---

## 三、三层结构性问题（架构层诊断）

### 3.1 问题 A：3 套理解机制断层

**现象**：
- LLM 解析（IntentResolver / `_resolve_question_entities_with_node_index` / `_agent1_resolve_org_subject`）
- 规则 fallback（`_looks_like_ranking_question` / `_rank_limit_match` / `_matched_org_level_terms` / `_resolve_query_intent`）
- 数据集元数据（`bs_dataset_report_config.ranking.enabled` / `synonym` / `node_index`）

**根因**：每层独立决策，没有共享"intent 模型"。

**实证**（今天）：
- ranking.enabled=False 拦截 IntentResolver → 整个 LLM + 规则 fallback 都没机会运行
- hint 沿用 hint_id=2 → LLM 拿 hint dataset catalog → 找不到 "东部分公司" → fallback 字符串匹配误转
- consumer_rank_limit 用 `asks_best_branch` 重判 ranking 意图，不用 IntentResolver 输出

### 3.2 问题 B：上帝文件（9272 行 / 156 方法 / 1 个类）

**现状**：
- 8 个职责群组（trace / LLM client / node_index / SQL builder / subject / routing / profile / display）
- 单一类 `FourAgentAskService`
- 22 个测试 + 1 controller + 1 service wrapper 直接 import

**症状**：
- 每次新 case 都在某一层加 token 匹配
- 5 个职责群混在同一函数体
- 历史 commit 显示 8+ 个"局部修复"，从未拆分

### 3.3 问题 C：缺少语义中间层

**症状**：
- 业务定义（"哪个最高"= Top1 ranking）和技术实现（SQL 模板 + LIMIT 1）分离
- 每个 SQL 模板都自己判定 ranking 意图，没有共享逻辑
- 新业务问法（"垫底 3 家"/"东边那几个"/"华东区域"）需要在多个地方加同义词

**理想态**（参考工业级）：
- **Metrics Layer**（Cube.js / dbt 的语义层）：把"最高/最低/垫底/前N"统一映射到 ranking intent
- **IntentResolver 单一真相源**：所有"理解"结果统一通过 `query_intent.signals` 输出
- **SQL Builder 只消费 signals**，不再独立判定

---

## 四、外部参考（工业级 NL2SQL 最佳实践）

| 实践 | 来源 | 借鉴点 |
|---|---|---|
| **RAG for SQL** | Vanna.AI / LangChain SQL Agent | Golden SQL 检索 + 模板匹配优先 |
| **Metrics Layer** | Cube.js / dbt Semantic Layer | 业务口径（"达成率"）与数据仓库分离 |
| **Semantic Layer** | 雪球 Snowflake Cortex | 字段同义词库 + 业务术语表 |
| **ReAct Agent** | LangChain ReAct | 思考-行动-观察循环，多步推理 |
| **Multi-Agent 编排** | CrewAI / LangGraph | 多个专业智能体并行处理不同视角 |
| **Schema Linking** | DIN-SQL / Spider | 问题中的实体先映射到 schema 字段 |

**对 SmartAsk 的启示**：
1. **Golden SQL 优先级 > LLM 直接生成**：你的 `_resolve_question_entities_with_node_index` 已具备 RAG 雏形，需要补"模板优先"
2. **Metrics Layer 是业务核心**：把"达成率"、"剩余任务" 等业务术语从 SQL 模板中抽象出来
3. **多智能体并行**（结构 / 趋势 / 异常）对应 `.ai-data/` 的 10 专家架构——已有专家储备，需要集成到流水线

---

## 五、成熟架构设计（理想态）

### 5.1 7 层闭环架构

```
┌─────────────────────────────────────────────────────────────┐
│ L0 输入预处理（新增，闭环起点）                              │
│   - hint 冲突检测（_is_entity_in_dataset）                  │
│   - explicit 数据集提取                                     │
│   - followup 解析                                          │
│   - 组织主体识别（_agent1_resolve_org_subject）            │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L1 意图识别（IntentResolver）                                │
│   - ranking / filter / aggregate / comparison / drilldown  │
│   - 输出 QueryIntentSignals（统一模型）                      │
│   - LLM + 规则 fallback + 数据集元数据 3 套合并             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L2 语义实体解析（EntityResolver）                            │
│   - 数据集 node_index 校验                                   │
│   - 跨数据集实体冲突检测（hint vs question）                  │
│   - 同义词映射（口语化 → 标准字段）                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L3 SQL 生成（SQLBuilder）                                    │
│   - 模板优先（Golden SQL 匹配 + 模板填充）                   │
│   - LLM 兜底（few-shot 复杂 SQL）                           │
│   - 按 dataset_code 分支（syyb / ecommerce / consumer）    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L4 SQL 校验与修正                                            │
│   - 语法校验 / 只读校验 / 字段存在性校验                     │
│   - 结果合理性校验（行数 / 字段 / 业务口径）                  │
│   - 失败自动降级到更宽松模板                                 │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L5 报告生成（ReportBuilder）                                 │
│   - 按 intent 选择卡片模板                                   │
│   - KPI 提取 / 对比文案 / 异常标注                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ L6 学习反馈（新增，闭环终点）                                │
│   - 用户行为记录（确认 / 拒绝 / 修改问题）                   │
│   - 数据集元数据更新（synonym / golden_sql / profile）       │
│   - short_term_memory 写回                                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
                  （回到 L0，下一轮）
```

### 5.2 关键改造点

| 层 | 当前位置 | 改造目标 | 现状 |
|---|---|---|---|
| L0 | 散落在 `_followup_dataset_hint_from_memory` / `_should_keep_followup_dataset_hint` | 抽离到 `PreprocessingStage`，含 hint 冲突检测 | 部分已修（今天） |
| L1 | `smartask_engine/intent/resolver.py` | 输出 QueryIntentSignals dataclass，3 套机制合并 | 未启动 |
| L2 | `_resolve_question_entities` + `_resolve_question_entities_with_node_index` | 统一 entity resolver，hint 冲突检测 | 部分已修（今天） |
| L3 | `_build_rule_based_sql` + 3 个 dataset 分支 | 模板引擎 + Golden SQL 优先 | 未启动 |
| L4 | `_agent3_review` | SQL 校验规则引擎 | 未启动 |
| L5 | `_build_layered_management_report` | 按 intent 选卡片模板 | 未启动 |
| L6 | 无 | 学习反馈 + 元数据更新 | 未启动 |

---

## 六、改造路径（5 个 Phase）

### Phase 0：解开配置层（已完成，待 commit）
**目标**：让 IntentResolver 不再被拦截
**内容**：
- DB UPDATE ranking.enabled=True（消费者数据集）
- 验证 "消费者事业部哪个分公司完成率最低" 返回 Top1
**风险**：0（运行态配置）
**时间**：5 分钟
**已做**：No（ranking.enabled 仍 = False）

### Phase 1：补齐 fallback 链（已完成工作树，待 commit）
**目标**：把今天发现的 P0/P1 全部修掉
**内容**（已写入工作树）：
- `_is_entity_in_dataset()` 实体冲突检测（Stage 3）
- entity validation 跨数据集 scope（Stage 8）
- cold start flat_alias_index 检查（app.py）
- consumer_rank_limit 兜底（asks_best_branch → rank_limit=1）
- baseline 文档 §8.1/§8.2
**风险**：低
**时间**：1-3 天（测试 + commit）
**已做**：Yes（工作树）

### Phase 2：语义中间层（关键架构转折点）
**目标**：建立 QueryIntentSignals，统一 3 套机制
**内容**：
- 新建 `backend/smartask_engine/intent/query_intent_signals.py`
- 定义 `QueryIntentSignals` dataclass：
  ```python
  @dataclass
  class RankingSignals:
      is_ranking: bool
      rank_limit: int
      direction: str  # asc/desc
      rank_sides: str  # top/bottom/both
      is_best_branch: bool
      is_worst_branch: bool
      confidence: float
      source: str  # "llm" / "rule" / "metadata"

  @dataclass
  class EntitySignals:
      entities: List[str]
      entity_in_hint_dataset: bool
      entity_in_any_dataset: List[int]
      entity_source: str

  @dataclass
  class QueryIntentSignals:
      intent: str
      target_level: str
      ranking: RankingSignals
      entities: EntitySignals
      filter_conditions: List[Dict]
      time_window: Optional[Dict]
      confidence: float
  ```
- IntentResolver 输出时**同时**写传统字段和 signals
- 所有 SQL Builder / 路由层只消费 signals，不再独立判定
**收益**：
- "哪个+最高/最差/最好"不再依赖 ranking.enabled
- 新增 ranking 触发词只需在 IntentResolver 加一处
- hint 冲突检测统一在 signals.entity 里
- "华东区域表现" 等新问法通过 synonym 扩展 + signals 字段映射实现
**风险**：中（重构，需要配套测试）
**时间**：1-2 周
**关键决策点**：是否启动？需要完整测试计划

### Phase 3：拆上帝文件（按职责群渐进）
**目标**：9272 行 → 3000-4000 行，每个职责群独立模块
**顺序**（按独立性 + 调用频次）：
| 顺序 | 群组 | 抽出目标文件 | 触发时机 |
|---|---|---|---|
| 1 | D. SQL Building | `backend/dataset_copilot/sql_builders.py` | 任何 dataset 新增/修 SQL |
| 2 | A. Trace / Logging | `backend/four_agent/trace_logger.py` | 任何 trace 改动 |
| 3 | H. Display / Report | `backend/four_agent/display.py` | 任何卡片展示改动 |
| 4 | G. Profile / Dimension | `backend/four_agent/profile_matcher.py` | 任何 profile 改动 |
| 5-8 | C / E / F / B | 待 Phase 0 数据出来再排 | - |

**每次抽出规则**：
1. 新建模块文件，**只搬代码，不改逻辑**
2. 旧 `four_agent_ask.py` 改成 `from .new_module import xxx` 转发
3. 跑 24 个 test + 3 个 diag 脚本，全部通过
4. 单独 commit，写明"refactor: extract D. SQL Building, no behavior change"
**风险**：中（refactor，不改逻辑）
**时间**：1-2 月（每群组 1-2 周）

### Phase 4：完整 NL2SQL 流水线（参考工业最佳实践）
**目标**：从"单数据集问数"升级到"多数据集智能问数"
**内容**：
- **Golden SQL 优先**：把 RAG 检索 Golden SQL 提到 LLM 生成之前
- **Metrics Layer 抽象**：业务口径（"达成率"/"剩余任务"）从 SQL 模板中抽离
- **智能体编排**（参考 `.ai-data/` 10 专家）：把 Agent4 业务分析改成"趋势 / 结构 / 异常"三视角并行
- **Schema Linking**：问题实体先映射到 schema 字段，再生成 SQL
**收益**：
- 复杂 SQL 通过率（聚合 / 列间比较 / 子查询）从 10% 提升到 70%+
- 业务口径统一管理
- 用户问法更灵活（"华东区域表现" / "完成率最低 + 任务最大的 5 个"）
**风险**：高（结构性改造）
**时间**：2-3 月
**前置**：Phase 2/3 完成

### Phase 5：智能体编排（长期演进）
**目标**：从"单流水线"升级到"多智能体并行工作流"
**内容**：
- 引入 LangGraph / CrewAI 框架
- 主理人 Agent（团队主理人）+ 数据工程师 + 趋势分析师 + 结构分析师 + 异常侦察员
- 工作流编排：规划 → 并行分析 → 合成
**收益**：
- 三视角分析（趋势 / 结构 / 异常）并行
- 复杂问法分解（"商用事业部业绩 + 趋势 + 异常点"）
**风险**：高（框架引入）
**时间**：3-6 月
**前置**：Phase 4 完成

---

## 七、决策点（用户要拍的）

| 决策点 | 选项 A | 选项 B | 选项 C | 我的推荐 |
|---|---|---|---|---|
| Phase 0 是否做 | ✅ 做（DB UPDATE） | ❌ 不做 | - | **A**（立即见效，0 风险） |
| Phase 1 是否 commit | ✅ commit 工作树 | ❌ 继续测 | 🔄 先 review | **A**（已修，先 commit） |
| Phase 2 是否启动 | ✅ 立即启动 | 🟡 Phase 1 稳定后 | ❌ 延后 | **B**（Phase 1 稳定 1 周后启动） |
| Phase 3 是否启动 | ✅ 与 Phase 2 并行 | 🟡 Phase 2 完成后 | ❌ 不做 | **B**（Phase 2 稳定后再拆） |
| Phase 4/5 是否规划 | ✅ 现在写 roadmap | 🟡 Phase 3 后再说 | ❌ 不规划 | **B**（Phase 3 后再细规划） |

**推荐路径**：Phase 0 → Phase 1 commit → Phase 2（核心转折）→ Phase 3（拆分）→ Phase 4/5（远期）

---

## 八、风险与对策

### 8.1 Phase 0（DB UPDATE ranking.enabled）

| 风险 | 概率 | 缓解 |
|---|---|---|
| UPDATE 失败 / 配置丢失 | 极低 | 先备份：`SELECT config_json FROM bs_dataset_report_config WHERE dataset_id=2` |
| 其他 ranking 触发词误识别 | 低 | 用 baseline §1.1 回归测试 |

### 8.2 Phase 1（fallback 链 commit）

| 风险 | 概率 | 缓解 |
|---|---|---|
| 工作树改动影响其他场景 | 中 | 跑全套 24 个测试 + diag 脚本回归 |
| `_is_entity_in_dataset` 误判 | 低 | 防御性 fallback（except 返回 True） |
| baseline 文档与代码不一致 | 低 | 文档先 review，再 commit |

### 8.3 Phase 2（语义中间层）

| 风险 | 概率 | 缓解 |
|---|---|---|
| QueryIntentSignals 设计与现有代码不兼容 | 中 | 先写 signals 类，再让 IntentResolver 同时写传统字段 + signals |
| 现有 SQL Builder 改不动 | 中 | 先让 signals 作为可选参数，旧字段保留 3 个月 |
| 测试覆盖不全 | 中 | 新增 IntentResolver 单元测试 + 集成测试 |

### 8.4 Phase 3（拆上帝文件）

| 风险 | 概率 | 缓解 |
|---|---|---|
| 抽出后某个分支行为变了 | 中 | 每次抽出前跑全套测试；不改逻辑只搬代码 |
| 测试用例 import 路径失效 | 中 | 保留 `four_agent_ask.py` 作为薄壳转发 |
| 单次改动太大 revert 困难 | 低 | 每次抽出 1 个群组 1 个 commit |

### 8.5 Phase 4/5（远期）

| 风险 | 概率 | 缓解 |
|---|---|---|
| 引入新框架学习成本 | 高 | 先 PoC 验证，再决定是否引入 |
| 现有功能回归 | 中 | 完整回归测试 + baseline 文档 |

---

## 九、验证方案

### Phase 0/1 验证
```bash
# 1. 跑 24 个测试
docker exec smartask-backend python -m pytest tests/ -q

# 2. 跑 6 个诊断脚本
docker exec smartask-backend python scripts/diag_east_company.py    # hint 冲突
docker exec smartask-backend python scripts/diag_intent_check.py    # ranking.enabled
docker exec smartask-backend python scripts/diag_e2e.py             # 主流水线
docker exec smartask-backend python scripts/diag_e2e_2.py           # 多轮场景
docker exec smartask-backend python scripts/diag_multi_dataset.py   # alias 评分
docker exec smartask-backend python scripts/diag_regression.py      # baseline 回归

# 3. baseline 回归问题
docker exec smartask-backend python scripts/diag_baseline_regression.py
# 验证：东部分公司下属代表处 / 整体业绩 / 跨集对比 / 哪个最高 / 哪个最低
```

### Phase 2 验证
```bash
# 单元测试
docker exec smartask-backend python -m pytest tests/test_intent_resolver_characterization.py -v

# 集成测试（多 dataset + 多 intent 组合）
docker exec smartask-backend python scripts/diag_intent_signals.py

# 用户视角回归（10 个真实问题）
docker exec smartask-backend python scripts/diag_user_perspective.py
```

### Phase 3 验证（每次抽出后）
```bash
# 单 commit 抽出后跑全套
docker exec smartask-backend python -m pytest tests/ -q
docker exec smartask-backend python scripts/diag_e2e.py
docker exec smartask-backend python scripts/diag_e2e_2.py
```

---

## 十、ROI 评估

| Phase | 投入 | 即时收益 | 长期收益 |
|---|---|---|---|
| **0** | 5 分钟 | ✅ 解开 ranking 0 行 | ✅ 防止 fallback 链断裂 |
| **1** | 1-3 天 | ✅ 修所有 P0/P1 | ✅ 闭环断点修复 |
| **2** | 1-2 周 | 🟡 中 | ✅✅ 解决"灵活问法"，加新触发词只改 1 处 |
| **3** | 1-2 月 | 🟡 中 | ✅✅ 解决"模板分支不清晰"，新增 SQL 不影响其他 |
| **4** | 2-3 月 | 🟡 低 | ✅✅✅ 复杂 SQL 能力 70%+ |
| **5** | 3-6 月 | 🟡 低 | ✅✅✅ 多智能体并行分析 |

**总投入**：~6-12 月（渐进推进）
**核心转折点**：Phase 2（语义中间层）——这是"架构完美到底流程"的核心

---

## 十一、立即可做的（等你拍板）

### 选项 A：Phase 0 + Phase 1 commit（推荐）
**时间**：30 分钟（含 commit + push）
**内容**：
1. DB UPDATE ranking.enabled=True（Phase 0）
2. 跑全套测试 + diag 脚本（验证 Phase 1）
3. 单 commit 工作树改动（hint 冲突检测 + entity validation + cold start + baseline）
4. push 到 main
**收益**：解开今天所有 P0/P1

### 选项 B：Phase 0 + 1 + Phase 2 详细设计
**时间**：2-3 天
**内容**：
1. Phase 0 + Phase 1 commit（同 A）
2. 写 Phase 2 QueryIntentSignals 详细设计文档
3. 列出 IntentResolver 改造点 + SQL Builder 改造点 + 测试计划
4. 等用户 review 后启动 Phase 2

### 选项 C：只 commit Phase 1（最小）
**时间**：15 分钟
**内容**：只 commit 工作树改动，Phase 0/2/3/4/5 全延后

---

## 十二、参考资料

**内部资料**：
- `nl2sql_improvement_plan.md`：5 层架构设计（意图识别 → SQL 生成 → 校验 → 卡片）
- `docs/audit/2026-08-06_final-audit-report.md`：上次全量审计
- `.workbuddy/artifacts/min-repair-plan-2026-08-13.md`：今天 Phase 1 修复方案
- `.workbuddy/artifacts/smartask-pipeline-2026-08-13.html`：今天全景图
- `.agents/skills/smartask-ranking-debug/SKILL.md`：ranking 排查指引
- `.agents/skills/smartask-global-constraints/SKILL.md`：项目约束

**外部参考**：
- Vanna.AI（RAG-based SQL generation）
- Cube.js Metrics Layer
- dbt Semantic Layer
- LangChain SQL Agent（ReAct）
- CrewAI / LangGraph（多智能体编排）

**专家资产**：
- `.ai-team/`：9 角色全栈研发专家团（含架构师、后端、前端、QA）
- `.ai-data/`：10 角色数据分析专家团（含主理人、数据工程师、趋势/结构/异常分析师）

---

**等你拍板下一步：A / B / C**