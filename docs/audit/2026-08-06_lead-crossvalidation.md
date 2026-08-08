# SmartAsk 审计 - 总监交叉验证记录

> 日期：2026-08-06
> 分支：`docker-setup`　HEAD：`8858bef`
> 作者：项目总监（团队编排 + 独立复核）
> 性质：**只读审计**。本文件记录总监亲自复核的实证结果、专家间分歧的裁决依据、以及五位专家均未覆盖的独立发现
> 定位：本文件不是审计报告，是**交叉验证台账**。最终交付文档在其之上汇编

---

## 0. 为什么需要这份台账

五位专家（架构 / 后端 / 前端 / QA / 运维）并行审计同一份代码，必然出现三类问题：

1. **同一事实给出不同数字**——同样统计 `_connect()` 调用点，架构师报 20、后端报 34
2. **同一现象给出相反定性**——`node_index` 究竟是「频繁重读的性能热点」还是「死代码」
3. **集体盲区**——五个人都从各自专业视角切入，没人负责的缝隙里藏着东西

前两类我用脚本实证裁决，不采信任何一方的口头数字。第三类是我这份台账的主要价值。

**证据准则**：本文件每条结论要么带 `文件:行号`，要么带可复现的脚本输出。凡属推断，显式标注「推断，未实证」。

---

## 1. 基线失效声明（先读这一条）

仓库内已有的历史分析报告（`nl2sql_improvement_plan.md` 及 `docs/` 下若干篇）以 **`four_agent_ask.py` 为 10748 行**为前提标注行号。

**实测当前该文件为 9063 行。**

```
$ wc -l backend/four_agent_ask.py
    9063 backend/four_agent_ask.py
```

差 1685 行。**基线报告中的全部行号已失效**，不可直接引用。本次审计所有行号均为本轮实测，与基线不构成延续关系。

凡本轮报告引用基线结论者，必须重新定位行号后才可复核——已要求全部五位专家遵守，QA 报告 §9 已按此执行。

---

## 2. 专家分歧裁决

### 裁决一：`_connect()` 调用点数量

| 来源 | 声称 |
|---|---|
| 架构师（高见远） | 20 处 |
| 后端（贝洛奇） | 34 处 |
| **总监 AST 实证** | **44 处调用 / 13 文件 / 3 处定义** |

两边都错，且都是低估。用 Python `ast` 遍历全部 `.py` 文件的 `Call` 节点统计（`grep` 会漏掉跨行调用与被注释干扰，故不用 grep）：

**3 处独立定义**：
- `backend/dataset_transform_service.py:34`
- `backend/bookshelf_repository.py:41`
- `backend/system_log_store.py:60`

**裁决**：采信 44。三处独立定义意味着连接管理逻辑本身就有三份，这比调用点数量更值得写进架构结论——它是「无统一数据访问层」的直接证据，而不只是一个计数。

已要求架构师按 44 修正，并把「3 处独立 `_connect` 定义」作为 `backend/repositories/` 目录缺失的实证支撑（该目录经确认**不存在**）。

### 裁决二：`.py` 内 DDL 与 `_ensure_optional_tables` 分叉

| 来源 | 声称 |
|---|---|
| 架构师 | DDL 15 处 / 7 文件 |
| 后端 | 各 5 处 |
| **总监实证** | **`CREATE TABLE` 33 处 / 15 文件；`_ensure_optional_tables` 5 份同名副本** |

关键发现不是数量，是**5 份同名函数互不相同**。用 `ast` 提取每个 `_ensure_optional_tables` 的函数体源码算 md5：

| 文件:行号 | 建表数 | md5 |
|---|---|---|
| `backend/controllers/bookshelf.py:526-576` | **3** | 各不相同 |
| `backend/runtime_migration.py:616-674` | 4 | 各不相同 |
| `backend/import_bookshelf_bundle.py:39-101` | 4 | 各不相同 |
| `backend/create_consumer_standard_dataset.py:659-716` | 4 | 各不相同 |
| `backend/export_bookshelf_bundle.py:45-57` | 1 | 各不相同 |

**5 个文件，5 个不同 hash，无一相同。**

这不是「代码重复」，是**已经发生分叉的代码重复**——五份副本各自演进过，现在语义已经不等价。

最要命的一处：`backend/controllers/bookshelf.py:526` 这份只建 **3** 张表，**缺 `bs_dataset_report_config`**。而这份恰好是**唯一走业务流量的路径**——另外四份分别在 runtime migration、bundle 导入导出、数据集创建脚本里，都是运维/一次性动作。

即：常态请求路径用的是**建表最少的那一份**。

**裁决**：采信 33 处 / 15 文件 + 5 份分叉。已要求架构师把此项从「代码重复」重新定性为「数据层一致性缺陷」，并挂到我在 §4 记录的 L-02。

### 裁决三：`node_index` 定性

| 来源 | 声称 |
|---|---|
| 架构师 | 频繁重读，性能热点 |
| 后端 | 死代码 |
| **总监** | **采信后端** |

依据：`_current_dataset_ids_for_node_index(context)` 在 `context` 无 `dataset` 键时于 `four_agent_ask.py:1789-1790` **直接 return []**，返回点**恰在触碰 `self._dataset_node_index` 之前**。QA 在其报告 §7.1 独立走到同一结论，且给出了额外佐证——正因为提前 return，`object.__new__(FourAgentAskService)` 夹具下 261 条 PoC 才没有因访问未初始化属性而崩溃。

两条独立路径指向同一结论，采信。

**裁决**：该项从架构师报告的「性能」章节移出，改列「技术债 - 疑似死代码」。性能章节不得保留此条，否则会把优化预算引到一条不执行的路径上。

---

## 3. 性能实证：真实耗时分布

专家们对性能瓶颈的判断分散在「LLM 慢」「SQL 慢」「前端 sleep」三处。我直接解析生产 trace 日志定论。

数据源：`backend/logs/smartask_trace.jsonl`，79 条事件记录。

**首次解析出错并已更正**：初次按顶层 `stage` 字段取值，得到 79 条 `stage=None`。实际结构为嵌套——`row['event']['stage']`。修正后重新解析。此处记录该错误，是为了说明本文件后续数字均来自修正后的口径。

### 耗时分布

| 环节 | 占比 |
|---|---|
| LLM 调用 | **94.4%** |
| 数据库执行 | 5.6% |

### LLM 内部分布

| stage | 事件数 | 往返 | 总耗时 | p50 | max |
|---|---|---|---|---|---|
| `agent1.org_subject` | 57 | 19 | **151.8s** | 7.15s | 16.74s |
| 其余全部 stage 合计 | — | — | 约 0.9s | — | — |

`agent1.org_subject` 单个 stage 占全部 LLM 耗时的 **99.4%**，占端到端总耗时的 **93.8%**。

数据库侧：`datasource.execute_sql` n=1，0.86s。retry / error 计数均为 0。

### 结论

**这个系统的性能问题就是一个函数的问题。** 不是「LLM 整体慢」，是 `_agent1_resolve_org_subject` 一个 stage 慢。任何不针对这一点的性能优化——连接池、SQL 索引、前端渲染——都在优化剩下的 6%。

这直接推翻了几处基于直觉的优化建议。已同步全体专家。

---

## 4. 总监独立发现（五位专家均未覆盖）

以下五条不在任何一位专家的回传中。前三条属部署完整性，第四条属数据安全，第五条属规范违规。

### L-01 | `angel_group_data` 表单点建表，重建环境即丢

**唯一正规建表途径**：`docker/postgres/init/002_angel_group_data.sql`

**挂载方式**：`docker-compose.yml:19`
```yaml
- ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
```

**Postgres 语义**：`docker-entrypoint-initdb.d` 下的脚本**仅在数据目录为空时执行一次**。数据卷已存在则整个目录被跳过。

**关键缺口**：`backend/bootstrap.py:45-57` 的 `MIGRATIONS` 列表共 7 个 sql 文件，**其中没有 `angel_group_data` 对应项**。

后果链条：
- 已有数据卷的环境升级 → init 不跑 → bootstrap 也不建 → 表不存在
- 换机器、换环境、卷损坏后恢复 → 同上
- 该表一旦缺失，依赖它的查询直接报错，或（更糟）落入 QA 报告 §3 的静默降级族，显示「未查询到匹配数据」

**定性**：这是**单点建表**，不是「迁移不完整」这种程度的问题。生产环境的表结构依赖一个只在首次启动执行的脚本，等于没有迁移保障。

**修复方向**：把 `angel_group_data` 的 DDL 补进 `backend/migrations/` 并登记到 `bootstrap.py:45-57` 的 `MIGRATIONS`，使其走幂等迁移路径。

### L-02 | 三张表在两套迁移体系中均不存在，只靠分叉副本创建

`bs_dataset_report_config` 等三张表：
- `backend/migrations/` 下 7 个 sql —— **无**
- `docker/postgres/init/` 下 6 个 sql —— **无**

它们的**唯一创建途径**是 §2 裁决二中那 5 份互不相同的 `_ensure_optional_tables`。

而走业务流量的那一份（`backend/controllers/bookshelf.py:526`）**恰好不建 `bs_dataset_report_config`**。

这意味着：如果一个环境从未跑过 runtime migration、从未导入过 bundle、从未执行过数据集创建脚本，那么 `bs_dataset_report_config` **永远不会被创建**，而业务路径也不会去建它。

**定性**：表结构的存在性依赖于「运维恰好执行过某个一次性脚本」这一偶然条件。这是比 L-01 更隐蔽的一类缺陷——L-01 至少有一个明确的建表文件，L-02 连文件都没有。

**修复方向**：三张表的 DDL 收敛到 `backend/migrations/`，5 份 `_ensure_optional_tables` 全部删除，改为统一调用迁移入口。

### L-03 | 两套迁移体系已经分叉

| 体系 | 文件数 | 独有内容 |
|---|---|---|
| `docker/postgres/init/` | 6 | `angel_group_data.sql` |
| `backend/migrations/` | 7 | `dataset_transforms.sql`、`ecommerce_standard_view.sql` |

两套体系存在**双向差集**——不是「一套是另一套的子集」，而是各有对方没有的东西。

叠加 `CREATE TABLE IF NOT EXISTS` 语义（**先跑者定义结构，后者静默跳过，不做结构比对**），产生的实际后果是：

**同一份代码在不同环境下会得到不同的表结构，且没有任何机制会报错。**

- 全新 docker 环境：init 先跑 → `angel_group_data` 有，`dataset_transforms` 待 bootstrap 补
- 已有卷的环境：init 跳过 → `angel_group_data` 缺
- 手工建过表的环境：`IF NOT EXISTS` 静默跳过 → 结构可能是任意历史版本

加重项：`backend/bootstrap.py:420-425` 全部迁移**跑完但失败仅记日志**，注释标为「非致命」。即迁移失败不阻断启动，服务照常拉起，带着残缺的表结构对外提供服务。

**定性**：这三条（L-01/L-02/L-03）合起来是一个问题——**这个项目没有一个可信的、单一的、幂等的数据库结构真相源**。任何「我在我机器上是好的」都无法推广到别的环境。

**修复方向**：迁移体系单一化。保留 `backend/migrations/` 作为唯一真相源，`docker/postgres/init/` 只保留数据库/用户初始化（不含业务表），bootstrap 迁移失败必须阻断启动。

### L-04 | LLM 失败自动跨候选重发（B16-c）—— 潜在外发通道，降为 P1

这条是我在复核 QA 与后端的 B16 争论时挖出来的。后端在 §5.2 用 `config/ai_settings.json` 实证反驳了我的初始定性，我已逐行核实配置文件，**后端的修正成立**。

**机制描述（双方一致认可的部分）**：

候选链构造无归属域过滤，叠加失败自动跨候选重发同一份 prompt。

1. `backend/llm_client.py:74-83` `_candidate_llm_configs` 尾段遍历全部 `is_active` 配置入候选，唯一去重依据是 `_config_signature`（`:87-93`）= `(model, base_url, api_key)` 三元组。无服务商归属、租户、数据域的任何过滤。

2. `llm_client.py:118` 顺序遍历候选链，`:119` 逐个换 api_key 与 base_url。

3. `llm_client.py:157-172`：`retryable` 为真则循环继续，把逐字相同的 system_prompt + user_prompt 发给下一个候选。

4. `backend/ask_engine_core.py:31-39` 重试命中集合含 `RateLimitError` / `APITimeoutError` / `AuthenticationError` / `PermissionDeniedError` 等日常事件。

**初始定性与后端修正**：

我最初将此条定性为「跨服务商外发、数据出境级、整盘第一」。后端在 §5.2 指出当前配置下所有激活配置的 `base_url` 相同。

我已逐行核实 `config/ai_settings.json`：

| id | model | base_url | api_key_b64 前缀 | is_active |
|---|---|---|---|---|
| 4 | MiniMax-M2.5 | `https://api.edgefn.net/v1` | `c2stenBP...` | true |
| 9 | GLM-5.1 | `https://api.edgefn.net/v1` | `c2stenBP...`（与 id=4 相同） | true |
| 10 | MiniMax-M2.5 | `https://api.edgefn.net/v1` | `c2stenBP...`（与 id=4 相同） | true |
| 11 | DeepSeek-V4-Pro | `https://api.edgefn.net/v1` | `enc:v1:8g32...`（不同） | true |

4 个激活配置的 `base_url` **全部是** `https://api.edgefn.net/v1`——同一家服务商。id 4/9/10 共享同一个 api_key，id 11 用不同 api_key。

**后端修正成立**：当前配置下的重试行为是**跨模型、跨计费账号**，不是跨服务商。数据不会流向第二家厂商。trace 中的 `candidate_count: 3` 也完全吻合——`_config_signature` 以 `(model, base_url, api_key)` 三元组去重，id=4 与 id=10 三元组完全相同被合并，故 4 个激活配置产生 3 个候选。

**修正后的定性（P1）**：

B16-c 是一个真实存在的**潜在**数据外发通道——机制上代码会把完整 prompt 发往任何被配置的 `base_url`，且触发条件（限流、超时）是日常事件。但当前配置下所有候选同源，**尚未构成跨厂商外发**。风险在于：任何管理员在 AI 模型管理页新增一个不同厂商的激活配置，该通道即刻打开，且无任何提示或审批。

定级 P1（潜在外发通道 + 无管控），不列整盘第一。整盘第一应为 B-27（已实证的非确定性路由，见 §5）或 L-01/L-02（已实证的部署缺表）。

仍需修复的四个方向不变：
1. 候选链按归属域切分，只有同一服务商域内的配置可互为 fallback；
2. `AuthenticationError` / `PermissionDeniedError` 移出重试集合，直接失败 + 告警；
3. 若确需跨厂商容灾，做成显式配置项 + 独立开关，trace 留 `cross_provider_fallback` 标记；
4. retry 埋点补记实际外发 endpoint。

**成本**：S。

### L-05 | `bootstrap.py:408` 日志含 emoji（P0-1 违规）

`backend/bootstrap.py:408` 日志输出含 warning-sign emoji 字符（U+26A0 U+FE0F）。全仓唯一一处。违反团队 P0-1（禁止 emoji 作功能标识）。本次只审不改。

---

## 5. B-27：性能第一现场的根因定位

§3 已实证 `agent1.org_subject` 占 LLM 耗时 99.4%。这一节记录我定位到的根因。

**函数**：`_agent1_resolve_org_subject`（`backend/four_agent_ask.py:7069-7159`），`:7121` 每次 `_chat_json` 打 LLM，**零缓存**。

**三处调用点**（后端修正：`:8981` 在 `confirm_by_boss()` 内，不在 `ask()` 内。单次 `ask()` 最多 2 次）：

| 调用点 | 所属方法 | 条件 | 传 trace | context |
|---|---|---|---|---|
| `:8493` | `ask()`（`:8472`） | `:8492` | 是 | 有 |
| `:8656` | `ask()` | `:8655` | 是 | 有 |
| `:8981` | `confirm_by_boss()`（`:8848`） | `:8980` | **否** | `[]` |

**三条结论**：

1. **`:8656` 是纯冗余调用。** 逐行核对：`:8656` 的入参与 `:8493` 完全相同（`question` / `memory_history` / `trace` 三者在 `8493` 至 `8656` 区间内无重新赋值），且 `:8655` 的条件是 `:8492` 条件的**严格子集**——`:8655` 成立时 `:8492` 必然已成立，即第一次调用必然已经执行过。第二次调用不可能得到新信息。

2. **`temperature=0.1` 非 0，导致同输入不同输出。**（`llm_client.py:142`）两次相同入参的调用可以返回不同结果，构成**非确定性路由**——已观察到第二次返回空、从而跳过 `node_index` 歧义释放检查的情形。这不是「多花一次钱」，是「同一个问题走了不同的分支」。

3. **`:8981` 不传 trace，可观测性隐形。** 该调用的耗时不进 trace 统计，意味着 §3 实测的 151.8s **是低估值**。

**修复方向**：`:8656` 直接删（条件为子集，无信息增益）；`:8981` 补 trace；`_agent1_resolve_org_subject` 增加请求内结果缓存。这是本项目投入产出比最高的性能改动——删一处调用即可砍掉约三分之一的 LLM 耗时。

---

## 6. 前后端共谋缺陷：Agent3 否决在链路上全程无声

这一条是我把后端与前端两份产出对撞出来的，单看任何一方都不完整。

| 环节 | 事实 | 出处 |
|---|---|---|
| 后端 | Agent3 返回 `approved=False` 时，`fallback_sql` 过 `_is_read_only_sql` 后仍赋给 `final_sql` 继续执行 | `four_agent_ask.py:8249` 附近 |
| 后端 | 步骤条无条件写 `status: "success"` | `four_agent_ask.py:8217-8223` |
| 前端 | 全仓**唯一**读取 `approved` 的地方只用于扣信心分 | `frontend/src/views/SmartAsk.vue:1672` |
| 前端 | 且该逻辑在 `else` 分支——后端返回 `confidence.result` 时**根本不执行** | `SmartAsk.vue:1711-1718` |
| 前端 | 信心徽章 tone 只看分数阈值，不看 `approved` | `SmartAsk.vue:1691` |
| 前端 | `reviewStatusText` 不读 `approved`、只数 risks 长度、risks 空时返回「SQL通过」，且**全仓零引用**（死代码） | `ResultDigestCard.vue:283-287` |

**完整链条**：Agent3 判定这条 SQL 不可信 → 后端照常执行 → 步骤条谎报 success → 前端唯一的 `approved` 读取点可能压根不执行 → 徽章只看分数 → 唯一可能显示复核状态的组件是死代码 → **用户拿到一个看起来完全正常的数字**。

**定性**：这条归入 QA 的「静默降级族」，但它比族内其他成员严重——其他成员是「失败被伪装成空结果」，这条是「失败被伪装成**正确结果**」。空结果至少会让用户困惑，错误数字不会。

**QA 已收录**：QA 在更新版报告（553 行）中将此条收录为 **SD-6**（P0），标注「总监交叉验证发现，本人已逐行核实」，并补充了「前端还有一条独立腿」的额外发现。QA 将 B2（控制流不阻断）与 SD-6（可信呈现伪造）拆为两条独立缺陷，理由是两者互不蕴含、修复方案不同。总监认可此拆法。

**修复方向**：`approved=False` 必须阻断执行并走显式降级分支；后端步骤 status 由 `approved` 决定；前端把复核状态提升为一等展示元素（`ResultDigestCard.vue` 的死代码要么接上要么删掉，不能留着假装有这个能力）。

---

## 7. 一处校正：后端 sleep 与前端节奏层

后端存在 2-3s 的人为 sleep。初判为「可直接删除以提速」。

前端实证推翻了这一判断的**前半段**，但支持了后半段：

- `frontend/src/state/smartAskSession.js:354-362` `getTraceMinVisibleMs`：每阶段最小可见时长 **3200-5200ms**
- 同文件 `:470` `MIN_ANALYSIS_VISIBLE_MS = 4200`

后端 2-3s 的 sleep **完全落在前端地板之下**，被节奏层吸收。删掉它对用户**感知**提速约等于 0。

但——前端有**独立的**节奏层兜底，不依赖后端 sleep 存在。

**结论**：后端 sleep 可以单独拆除，不需要前端配合改动，也不会造成界面跳变。只是不要指望它带来感知提速——真正的提速在 §5 的 B-27。

---

## 8. 专家产出落盘状态

反剧场铁律：无产物不设席位。产出必须落盘才进 Phase 3 汇编。

| 角色 | 文件 | 状态 | 门禁 |
|---|---|---|---|
| 前端（贾思敏） | `docs/audit/2026-08-06_frontend-audit.md` | **已落盘** 329 行 | 98 处 file:line，P0 emoji 0 命中，通过 |
| QA（严过关） | `docs/audit/2026-08-06_qa-audit.md` | **已落盘** 553 行 | 61 处 file:line，P0 emoji 0 命中，通过；已补 SD-6（总监 L-06 收录）；B16-c 未进报告（后端实证修正后定级 P1，在最终交付文档中补） |
| 后端（贝洛奇） | `docs/audit/2026-08-06_backend-audit.md` | **已落盘** 332 行 | 92 处 file:line，P0 emoji 2 命中（均为引用 `bootstrap.py:408` 代码中的 emoji 字符作为审计证据，非功能图标，判定通过）；含 B16-c 配置实证修正（§5.2） |
| 架构（高见远） | `docs/audit/2026-08-06_architecture-audit.md` | **已落盘** 575 行 | 79 处 file:line，P0 emoji 0 命中，通过；三个必答问题全答（§6.1/6.2/6.3）；A-13 `_connect` 仍写 20 处未按 44 修正（已知偏差） |
| 运维（卜宕机） | `docs/audit/2026-08-06_devops-audit.md` | **未落盘**（429 限流失败，14:17 重置后补） | — |
| 总监交叉验证 | `docs/audit/2026-08-06_lead-crossvalidation.md` | **已落盘** 本文件 | 已修正 L-04 定性（采纳后端配置实证修正）、L-05 调用点归属、L-09 emoji 引用方式 |

---

## 9. 待结清项

| 项 | 依赖 | 说明 |
|---|---|---|
| B9 定级 | 运维 Q1 数据库账号权限 | `_is_read_only_sql` 的绕过危害取决于 DB 账号是否 superuser。若为 superuser，B9a（`pg_read_file` 任意文件读）从 P1 升 P0 |
| L-01/L-02/L-03 归属 | 运维报告 | 三条部署完整性发现需运维在其报告中确认迁移执行现状 |
| 三大架构决策 | 架构师报告 | 9063 行第一刀切哪 / 是否引入 services+repositories 分层 / basic-advanced 双引擎存废 |

---

## 10. 本台账的确定性边界

如实声明，避免把推断说成实证：

**已实证**（脚本可复现）：
- `four_agent_ask.py` 行数、`_connect` 44 处、`CREATE TABLE` 33 处、5 份 `_ensure_optional_tables` md5 分叉
- 两套迁移体系文件差集、`angel_group_data` 单点建表
- trace 耗时分布、`candidate_count: 3`
- 全部引用的 `文件:行号` 均逐行核对

**未实证**（代码路径推断）：
- L-04 的实际外发未触发观察——没有制造过限流或凭据失效来看它真的转发。结论来自代码路径与配置的确定性推导，**不是观察到的事件**
- §6 的完整链条未做端到端 UI 复现
- 所有并发类缺陷（QA 的 SD-1 三出口）均未活体复现

**未执行**：
- 未运行任何活体请求，未跑测试套件，未修改任何代码
- 未做 UI 截图对比或用户行为观察。样本 = 0，观察周期 = N/A
