# SmartAsk 全景代码审计报告

> 日期：2026-08-06/07
> 分支：`docker-setup`　HEAD：`8858bef`
> 性质：**只读审计**。全程未修改 `backend/` `frontend/` `config/` 下任何文件
> 审计团：架构师（高见远）/ 后端（贝洛奇）/ 前端（贾思敏）/ QA（严过关）/ 运维（卜宕机）/ 项目总监（大湾区靓仔）
> 证据准则：每条结论带 `文件:行号`。凡推断显式标注「推断，未实证」。未触发任何缺陷，未发起任何活体请求

---

## 0. 基线失效声明

`backend/four_agent_ask.py` 当前 **9063 行**。项目已有历史报告全部基于 **10748 行**版本。所有旧报告中的行号已失效。本报告全部行号在 HEAD `8858bef` 上重新核对。

---

## 1. 执行摘要

这个系统最大的风险不是"测试不够多"或"代码不够快"，是**它把几乎所有失败都翻译成了看起来正常的输出**。

Agent2 没生成出 SQL、Agent3 复核否决、SQL 执行报错、LLM 调用挂掉、权限过滤把结果滤空——这些性质完全不同的硬失败，最终都汇流成同一句用户可见文案：「本次围绕『XX』未查询到匹配数据」。用户读到的是"这块没数据"，真相是"这个查询坏了"。对一个内部 BI 问数系统，错误结论会被当作业务事实带进决策会议。

叠加三组结构性问题：
- **部署不可复现**——表结构依赖"运维恰好执行过哪个脚本"，不是迁移保障
- **安全护栏装反**——可信路径校验严，不可信路径校验松，执行点零护栏
- **LLM 状态共享**——进程级单例，并发请求互相覆盖模型选择

**裁决：不可交付。P0 缺陷必须全部清零。**

---

## 2. 缺陷分级总表

### 2.1 P0（11 条——不做就会炸）

| # | ID | 缺陷 | 证据(file:line) | 后果 | 修复成本 | 来源 |
|---|---|---|---|---|---|---|
| 1 | **B-27** | 组织主体识别零缓存，同输入重复 LLM 调用，temperature 非零致非确定性路由 | `four_agent_ask.py:7069-7159`（定义）；`:8493`/`:8656`（ask 内重复调用，入参完全相同）；`llm_client.py:142` `temperature=0.1` | 同一用户问同一问题两次可能选不同数据集。占全部 LLM 耗时 99.4%。trace 实证 | S | 总监 |
| 2 | **L-01** | `angel_group_data` 表单点建表，非全新数据卷环境必然缺表 | `docker/postgres/init/002_angel_group_data.sql`（唯一建表途径）；`docker-compose.yml:19`（仅首次执行）；`bootstrap.py:45-57` MIGRATIONS 无对应项 | 已有数据卷升级 / 换机器 / 恢复备份 → 表不存在 → 查询报错或静默降级 | S | 总监 |
| 3 | **L-02/B-23** | 三张生产表不在任何迁移文件中，唯一定义在请求处理器内联 DDL | `controllers/bookshelf.py:526-570`（唯一定义，且缺 `bs_dataset_report_config`）；`backend/migrations/` 全部 7 个 sql 无此三表 | 干净环境部署后缺表，健康检查给假阳性 | S | 总监+后端 |
| 4 | **A-01** | 只读护栏方向反置：批准的 SQL 不校验，否决的 SQL 才校验，执行点零护栏 | `four_agent_ask.py:8225-8263`（approved=True 直落执行）；`:8238`（approved=False 才过校验）；`datasource_router.py:192-199`（执行点无校验） | LLM 改写的 SQL 直达数据库，纵深防御为零 | S | 架构 |
| 5 | **SD-6** | 否决态被伪造为成功态——步骤条无条件写 success | `four_agent_ask.py:8217-8223`（写在 `:8225` 判断 approved **之前**） | 前端显示绿色"结果稳定"，用户拿不可信数字做决策 | S | 总监→QA核实 |
| 6 | **B2** | Agent3 复核否决不阻断执行 | `four_agent_ask.py:8225-8249`（approved=False → fallback_sql 赋回 → `:8263` 照常执行） | 被否决的 SQL 照常执行、数字照常渲染 | S | QA |
| 7 | **B3** | 行级数据权限默认 fail-open | `data_permission_store.py:475-476`（`rule.get("mode") != "org_tree": return sql`）；`config/data_permissions.json` 仅 3 条规则覆盖 2 个数据集 | 其余数据集零行级过滤，用户看到越权数据 | S | QA |
| 8 | **B4** | 行级权限外层包裹对聚合与排名无效 | `data_permission_store.py:514`（`SELECT * FROM (...) WHERE`）；`ask_engine_sql.py:36-47`（排名 SQL 全域计算后截断，再过滤） | 排名序号本身跨域泄露；TopN 语义塌缩为"全公司前10 ∩ 可见范围" | L | QA |
| 9 | **SD-2** | 三条硬失败路径统一降级为"未查询到匹配数据" | `four_agent_ask.py:8139-8154`/`8228-8237`/`8358-8367` → `_build_graceful_dataset_result:1196-1232` → `_build_fallback_analysis:506,535-546` | 错误结论被当作业务事实 | M | QA |
| 10 | **A-02** | 语义画像层静默空转——数据文件不存在，31 个调用点全部拿到 None | `dataset_dimension_profiles.py:9`（`PROFILE_PATH` 指向不存在的文件）；`backend/data/` 目录存在但为空 | 路由层级判定、实体消解、同义词映射全部退化 | S（补文件）/ M（补+自检） | 架构 |
| 11 | **A-03/SD-1** | 进程级单例 + 每请求写共享 LLM 配置 + 无锁 | `four_agent_ask.py:9063`（单例）；`:8487`（写共享 `_preferred_model_id`）；`llm_client.py:46-51`（`_activate_llm` 改共享态）；全后端唯一锁在 `smartask_report_history_store.py:23` | 并发请求模型互相覆盖，答案用错模型 | M | 架构+QA |

### 2.2 P1（16 条——高优先级）

| ID | 缺陷 | 证据 | 成本 | 来源 |
|---|---|---|---|---|
| **L-04/B16-c** | LLM 失败自动跨候选重发——潜在外发通道（当前配置同源，未跨厂商） | `llm_client.py:74-83`（无归属过滤）；`:157-172`（retryable 循环）；`ask_engine_core.py:31-39`（含日常事件）；`config/ai_settings.json`（4 激活配置 base_url 全相同） | S | 总监（后端修正定性） |
| **B-25** | 负缓存永久钉死，一次瞬时读失败致组织路由整进程失效 | `organization_route_resolver.py:104-113`（`{}` is not None → 永久缓存） | S | 后端 |
| **B-5** | 数据源连接无 connect_timeout、无 statement_timeout、结果集无上限 | `datasource_router.py:156-173`（对比 `bookshelf_repository.py:41-58` 有 `connect_timeout=8`） | S | 后端 |
| **B-6** | N+1：catalog 循环内每数据集 7 条 SELECT + 7 次建连 | `four_agent_ask.py:3953`；`bookshelf_repository.py:131-246` | M | 后端 |
| **B-8/SD-3** | `_chat_json` 吞全部异常返回 fallback（有埋点但不阻断不告警不上抛） | `llm_client.py:251-261` | S | 后端+QA |
| **B-9** | `_is_read_only_sql` 关键字黑名单可绕过（`pg_read_file`/`pg_sleep`/dblink 拼接） | `ask_engine_sql.py:50-67` | M | QA |
| **B-10** | 小额非零值截断显示为 0（`f"{0.001:.2f}"` → "0.00" → "0"） | `ask_engine_display.py:58-61`；同型 `:88-91` | S | QA |
| **B-11** | NaN/Inf 导致格式化崩溃（`int(nan)` → ValueError） | `ask_engine_display.py:54,59` | S | QA |
| **B-12** | SQL 自动修复把已注入权限谓词的 SQL 发给 LLM（组织范围出境） | `four_agent_ask.py:8253`（先包权限）→ `:8280`（`failed_sql=final_sql` 送 LLM） | S | QA |
| **A-04** | 同一 LLM 调用在单次请求内可重复执行（B-27 的架构师侧视角） | `four_agent_ask.py:8491-8492` 与 `:8655-8656` 入参完全一致 | S | 架构 |
| **A-06** | 多数据集查询串行，无并行 | `four_agent_ask.py:7872`（`for dataset_id in dataset_ids:` 串行循环） | M | 架构 |
| **A-09** | 三套规则 SQL 引擎实为"一数据集一引擎"，新增数据集需新增数百行 Python | `four_agent_ask.py:4497-4515`（硬编码 `dataset_code` 分派） | L | 架构 |
| **A-10** | Agent3 否决不具约束力（B2 的架构师侧视角） | `four_agent_ask.py:8225-8249` | S | 架构 |
| **A-12** | 数据访问层被架空：Repository 零 DDL，建表散落 10 文件且已漂移 | `bookshelf_repository.py`（CREATE TABLE 0 次）；5 份 `_ensure_optional_tables` md5 全不同 | L | 架构 |
| **B6/B7/B8** | 确认会话状态机缺陷（重复确认双跑 / 失败也 pop / 无锁迭代 RuntimeError） | `four_agent_ask.py:8878`/`9058`/`7837-7849` | S/S/S | QA |
| **A-15** | 会话态在进程内存，锁死单进程部署 | `four_agent_ask.py:55`（`_pending_confirmations: Dict = {}`） | M | 架构 |

### 2.3 P2/P3（15 条——技术债与规范）

| ID | 级别 | 缺陷 | 证据 | 成本 |
|---|---|---|---|---|
| A-05 | P2 | 快路径被人为注入 2-3 秒睡眠 | `four_agent_ask.py:8071-8074` | S |
| A-07 | P2 | 规则引擎无条件预跑，结果常被丢弃 | `four_agent_ask.py:1380` | S |
| A-08 | P2 | 校验过的 SQL 字符串不是执行的字符串（TOCTOU） | `four_agent_ask.py:7425`→`8187`→`8188`→`8253`→`8263` | S |
| A-13 | P2 | `_connect()` 私有方法跨 4 层被 44 处直接调用（13 文件 / 3 套独立定义） | AST 实证：`bookshelf.py` 12 / `dataset_transform_service.py` 9 / `system_log_store.py` 7 / 其余 10 文件 16 | M |
| A-14 | P2 | 循环依赖 `feature_flags` ↔ `rbac_store` | `feature_flags.py:1403,1523`；`rbac_store.py:88` | S |
| A-16 | P2 | advanced 引擎 3649 行、零流量、配置与代码默认值相反 | `smartask_advanced/` 3649 行；`ask_flow/controller.py:54` 恒返回 basic | S（下线） |
| A-18 | P2 | `config/` 混装配置/运行态/业务数据/凭据约 20MB | `smartask_report_history.json` 10.5MB 在 config/ 内 | M |
| B-13 | P2 | SSE 客户端断连不取消工作线程 | `controllers/smart_chat.py:769`/`1042` 裸起线程 | M |
| B-20 | P2 | trace 事件内存累积 + 流式增量全量落盘（单次 94KB） | `trace_logger.py`；`smart_chat.py:710` | S |
| B-22 | P2 | 配置文件每次调用重读磁盘（实测 2.38ms，占 0.03%） | `config_manager.py:124` | S |
| B-26 | P2 | `dataset_node_index` 315KB 加载一次永不失效（守卫是死代码） | `four_agent_ask.py:84-93`（失败也返回 dict，守卫永不进入） | S |
| L-03 | P2 | 两套迁移体系已分叉（docker init 独有 angel_group_data；migrations 独有 2 个） | `docker/postgres/init/` 6 个 vs `backend/migrations/` 7 个 | M |
| L-08 | P2 | 行级权限实际只覆盖 2 个数据集（config 仅 3 条规则） | `config/data_permissions.json` | S |
| A-11 | P3 | 上帝文件：9063 行 / 1 类 / 156 方法（但 58% 零状态依赖，可机械外提） | AST 实证 | L（但低于预期） |
| L-09 | P3 | `bootstrap.py:408` 日志含 emoji（全仓唯一，违反 P0-1） | `bootstrap.py:408` | S |

---

## 3. 性能实测

### 3.1 真实耗时分布（生产 trace 实证）

数据源：`backend/logs/smartask_trace.jsonl`，79 条事件。

| 环节 | 占比 |
|---|---|
| LLM 调用 | **94.4%** |
| 数据库执行 | 5.6% |

LLM 内部：

| stage | 往返 | 总耗时 | p50 | max |
|---|---|---|---|---|
| `agent1.org_subject` | 19 | **151.8s** | 7.15s | 16.74s |
| 其余全部 stage 合计 | — | 约 0.9s | — | — |

**`agent1.org_subject` 单个 stage 占全部 LLM 耗时 99.4%。** 这不是"LLM 整体慢"，是一个函数慢。其中至少 1/3 是同输入重复调用。

### 3.2 配置读盘不构成瓶颈

| 操作 | 耗时 | 相对 LLM p50 |
|---|---|---|
| `json.load` feature_flags.json (63KB) | 0.984ms | 0.014% |
| `json.load` dataset_node_index.json (316KB) | 3.803ms | 0.053% |
| 合计 | 2.38ms | 0.03% |

### 3.3 上帝类拆分可行性（推翻"难拆"共识）

AST 实测：9063 行中 9009 行属于单个 class，156 个方法。但：

- **58% 的代码零实例状态依赖**（35 个方法 / 5215 行）
- 三套规则 SQL 引擎合计 2112 行，实例属性引用 = **0**（被误写成方法的纯函数）
- `__init__` 仅 11 个实例属性，最高引用热度 13 个方法

正确估法分两层：零状态纯函数机械外提（5215 行）+ 有状态的少数方法做架构解耦。合成一个笼统的 L 会严重高估。

---

## 4. 安全护栏现状（架构师 §6.3 详述）

| 路径 | 可信度 | 只读校验 | 字段校验 | 行级权限 |
|---|---|---|---|---|
| 规则引擎/Golden SQL | **最高** | 有 | 有 | 后置 |
| Agent3 修复后 SQL | 低 | 有 | 无 | 后置 |
| 被 Agent3 否决的 fallback | 低 | 有 | 无 | 后置 |
| LLM 自由生成（normal） | **最低** | **无** | 有 | 后置 |
| **物理执行点** | — | **无** | **无** | — |

规律：越可信校验越严，越不可信越松。**防护强度和路径重要性完全倒挂。**

正确修复：在 `datasource_router.execute_sql_for_source` 设唯一强制闸口（语句校验 + 表白名单 + 行级权限 + LIMIT + statement_timeout + 审计日志），上层全部分支式校验删除。

---

## 5. 测试安全网评估（QA §5 详述）

**150 个测试，1.58 秒跑完，全部纯函数级，不碰 DB 不走链路。**

对结果数值正确性的断言数：**0**。全系统最安全关键的函数 `apply_row_level_filter`：**0 测试 0 覆盖**。

反作弊五项独立复核全过（无常驻 skip、无 `assert True`、无 mock 被测逻辑、无框架篡改），但网本身没为"结果错了但没人发现"设计过。

**安全网在开发者本机不可运行**——宿主机 `import openai` 失败，150 全绿是容器内专属。对一个"改一行规则就可能让数字错掉"的系统，安全网在开发环节实际缺席。

---

## 6. 分批路线图

### W0：先修不需要动结构的（0.5 周，全部 S 成本）

| # | 动作 | 解决 | 理由 |
|---|---|---|---|
| 0.1 | **产出 `backend/data/dataset_dimension_profiles.json`** + 启动期存在性自检 | A-02 | 全项目唯一"补一个文件激活 31 个已写好调用点"的机会。必须配合 90 题回归 |
| 0.2 | 消除 `agent1.org_subject` 重复调用：`:8656` 改复用 `:8491` 结果 | B-27 | 实测省 27.8% 端到端，且同时修非确定性路由。冗余性已由三条命题证明 |
| 0.3 | `approved=False` 阻断执行 + 步骤 status 按 approved 落 | B2 + SD-6 | 后端先改，前端自然正确 |
| 0.4 | 行级权限改默认 deny（无规则返回 `1=0`） | B3 | 成本 S，当天可完成 |
| 0.5 | 删除 `time.sleep(random.uniform(2.0, 3.0))` | A-05 | 前端节奏层有独立兜底，删除对感知提速约 0，但不删白占线程 |
| 0.6 | 三张表补进 `backend/migrations/` + `bootstrap.py` MIGRATIONS | L-01/L-02/B-23 | 唯一"不做就会在新环境炸"的 |
| 0.7 | 删除请求路径内联 DDL（`bookshelf.py:526-576`） | B-16/B-24 | 依赖 0.6 完成 |
| 0.8 | `_select_sql_strategy` 改惰性求值 | A-07 | 规则引擎不再无条件预跑 |
| 0.9 | 补 C1/C2/C3 规则引擎 characterization 快照测试 | 拆分前置 | 纯新增，零风险 |
| 0.10 | LLM 候选链加归属域过滤 + `AuthenticationError`/`PermissionDeniedError` 移出重试集合 | L-04 | 潜在外发通道关闭 |

**W0 投入产出比最高**：1 周解决 11 个 P0 中的 7 个，且直接砍掉 LLM 重复调用（约 4s，占端到端 27.8%）。

### W1：安全闸口（0.5 周）

| # | 动作 | 解决 |
|---|---|---|
| 1.1 | `datasource_router.execute_sql_for_source` 建唯一闸口（正则版校验 + LIMIT + statement_timeout + 审计日志） | A-01 |
| 1.2 | `apply_row_level_filter` 从 4 个调用点下沉进闸口 | A-01/A-08 |
| 1.3 | 删除上层全部分支式校验 | A-08 |
| 1.4 | 删除 Agent3 的 LLM 复核，降级为确定性校验器 | A-10（省一次 LLM 往返约 7s） |

### W2：并发正确性与部署解锁（1 周）

| # | 动作 | 解决 |
|---|---|---|
| 2.1 | LLM 配置请求级化：`model_id` 不再写共享单例 | A-03/SD-1 |
| 2.2 | 会话态外置到 DB 表 | A-15 |
| 2.3 | 数据集循环并行化 | A-06 |

W2 完成后服务才真正无状态，才具备切 WSGI + 多 worker 的前提。

### W3：数据形态与规则引擎收敛（2 周）

| # | 动作 | 解决 |
|---|---|---|
| 3.1 | 建 `v_angel_business` / `v_consumer_business` 视图，与 `v_feishu_tbldianshang` 同构 | A-09 前置 |
| 3.2 | syyb/消费者引擎改查视图，删除 13 个内联 CTE 与 16 处 jsonb 抽取 | A-09 |
| 3.3 | 三引擎塌缩为 `sql/builder.py` 单装配器 + 声明式 spec | A-09 |

W3 结束时 2112 行规则代码降到约 300 行，新增数据集边际成本从数百行 Python 变成一段 JSON。这是达成 70% 通过率目标的结构前提。

### W4：数据层归位（1.5 周）

| # | 动作 | 解决 |
|---|---|---|
| 4.1 | 建 `migrations/` 承接全部 DDL，删除 5 份分叉 `_ensure_optional_tables` | A-12/L-03 |
| 4.2 | `_connect()` 转 public `connection()`，44 处统一；引入连接池 | A-13 |
| 4.3 | `config/` 拆为 config/（入 git）+ state/（运行态）+ secrets/（凭据） | A-18 |

### W5：上帝文件拆分（3 周）

按 S1-S8 顺序执行（架构师 §4.4 详述）。前置 W1-W4 全部完成。关键：**不要先拆上帝文件**——三个最大簇分别卡在 A-13、A-03、A-15 上，前置不解决硬拆只会把 god state 复制成 N 份。

### W6：收尾（0.5 周）

advanced 引擎下线 / `smartask_basic` 薄壳删除 / `sys.path.insert` 全删 / 加 import 方向门禁测试。

### 路线图总结

| 波次 | 工期 | 解决 P0 数 | 关键收益 |
|---|---|---|---|
| W0 | 0.5 周 | 7/11 | 砍 27.8% 端到端 + 补部署缺表 + 关降级通道 |
| W1 | 0.5 周 | +2 | 安全护栏归位 + 省一次 LLM 往返 |
| W2 | 1 周 | +2 | 服务无状态化，解锁多 worker |
| W3 | 2 周 | 0 | 2112 行→300 行，70% 通过率结构前提 |
| W4 | 1.5 周 | 0 | 数据层归位 |
| W5 | 3 周 | 0 | 上帝文件拆分 |
| W6 | 0.5 周 | 0 | 收尾 |
| **合计** | **9 周** | **11/11** | |

**如果只能做一件事**：做 W0.1（补 `dataset_dimension_profiles.json`）——补一个文件激活 31 个已写好的调用点，是全项目投入产出比最高的单点动作。

---

## 7. 工作量估算

### 7.1 按修复成本汇总

| 成本 | 定义 | 条目数 | 合计人日 |
|---|---|---|---|
| S | 1 人日内 | 22 | 22 |
| M | 2-5 人日 | 12 | 36 |
| L | 1 人周以上 | 5 | 25 |
| **合计** | | **39** | **83 人日（约 17 人周）** |

### 7.2 上帝文件拆分（W5）分层估算

| 层 | 内容 | 行数 | 估算 | 理由 |
|---|---|---|---|---|
| 零状态纯函数外提 | 35 个方法，机械操作 `self._foo(x)` → `_foo(x)` | 5215 | 1.5 周 | 三套规则引擎 2112 行无 DB 无 LLM，外提后立即可单测 |
| 有状态架构解耦 | 11 个实例属性周边的少数方法 | ~3800 | 1.5 周 | 需先完成 W2（请求级化）+ W4（连接池）才能动 |
| facade 收敛 | FourAgentAskService 类名不变（兼容 16 个测试文件） | ~300 | — | — |

合计 3 周，低于"上帝文件 L/XL"的直觉判断。

### 7.3 测试补测优先级（QA §8 详述）

| # | 补测项 | 压住的缺陷 | 成本 |
|---|---|---|---|
| 0 | 修复宿主机测试可运行性（`openai` 依赖隔离） | 前置项 | S |
| 1 | `apply_row_level_filter` 全分支（含锁死当前 fail-open） | B3/B4 | S |
| 2 | `_build_fallback_analysis` 三种失败入参 golden | SD-2 | S |
| 3 | `_agent3_review` 的 trusted/rule 分支 | B2 | S |
| 4 | 三套规则引擎 golden SQL 快照（含分母为零） | B5 | M |
| 5 | `confirm_by_boss` 状态机五态 | B6/B7 | M |
| 6 | SD-1 Barrier 确定性测试 | SD-1 | M |

---

## 8. 运维域发现（运维报告未落盘，内容来自回传纪要）

> 运维专家（卜宕机）因 429 限流未完成落盘。以下内容来自其回传纪要，行号待运维报告补齐后核实。

**D-A 部署形态**：生产跑 Flask 内置开发服务器（非 gunicorn），`app.run()` 内部 `threaded=True`，多请求并发进入同一进程。SSE 为裸线程 + 内存 queue，多 worker 部署会丢确认会话状态。

**D-B 可观测性**：trace 日志 75 条事件中 60 条缺 `trace_id`，链路断裂。182 处 print 全仓混进 stdout，仅 2 个文件用 logging。

**D-C 配置管理**：`config/` 目录 20MB，混装配置/运行态/业务数据/凭据。`smartask_report_history.json` 10.5MB 写入 config/。`runtime_migration.py` 1284 行的存在意义就是给这个错位打补丁。

**Q1 DB 账号权限**（卡 B9 定级）：待运维核实数据源连接账号是否为 superuser。若为 superuser，B9a（`pg_read_file` 任意文件读）从 P1 升 P0。

**Q2 并发模型**：Flask 3.0.3 `threaded=True` 确认（总监已实证），非单进程。

**Q3 迁移执行**：`bootstrap.py:420-425` 全部迁移跑完但失败仅记日志，注释标为"非致命"。迁移失败不阻断启动，服务带着残缺表结构对外提供服务。

---

## 9. 交叉验证裁决记录

以下三条专家分歧由总监用 AST/Python 脚本实证裁决：

| 分歧点 | 架构师 | 后端 | 总监实证 |
|---|---|---|---|
| `_connect()` 调用点 | 20 | 34 | **44**（13 文件 / 3 套独立定义） |
| DDL 散落 | 15 处/7 文件 | 各 5 处 | **5 份副本全部分叉**（md5 全不同） |
| `node_index` 定性 | 频繁重读 | 死代码 | **采纳后端**（守卫永不进入） |

一条定性修正：
- **B16-c**：总监初始定性"跨服务商外发、数据出境级、整盘第一"。后端用 `config/ai_settings.json` 实证反驳——4 个激活配置 base_url 全相同。总监逐行核实后**采纳后端修正**，降为 P1（潜在外发通道 + 无管控）。

---

## 10. 已推翻的基线结论

| 旧结论 | 复核 | 说明 |
|---|---|---|
| `feishu_sync.py:214/267` 缺 `daemon=True` | **误报** | 两处均已写 `thread.daemon = True` |
| 全仓零锁 | **错误** | 有 2 处 RLock。准确说法是"漏在最该用的共享 LLM 状态上" |
| 配置读盘是性能瓶颈 | **口径错配** | 实测 2.38ms，占 0.03% |
| `node_index` 频繁重读 | **死代码** | 守卫 `if not isinstance(node_index, dict)` 永不成立 |
| `_chat_json` 无日志 | **错误** | `llm_client.py:252-259` 埋点完整含 traceback。准确说法："有埋点但不阻断、不告警、不上抛" |
| B4 聚合场景是越权泄露 | **定性反转** | `to_jsonb(row)->>'键'` 缺键返回 NULL → WHERE 恒假 → 0 行。实为 fail-closed 误杀，且撞进静默降级族 |
| 9063 行上帝文件难拆 | **推翻** | 58% 零状态依赖，三套规则引擎 2112 行实例属性引用 = 0。机械外提 5215 行不是架构手术 |

---

## 附录：审计产出索引

| 文件 | 行数 | file:line 引用 | 角色 |
|---|---|---|---|
| `docs/audit/2026-08-06_architecture-audit.md` | 575 | 79 | 架构师 |
| `docs/audit/2026-08-06_backend-audit.md` | 332 | 92 | 后端 |
| `docs/audit/2026-08-06_frontend-audit.md` | 329 | 98 | 前端 |
| `docs/audit/2026-08-06_qa-audit.md` | 553 | 61 | QA |
| `docs/audit/2026-08-06_lead-crossvalidation.md` | — | — | 总监交叉验证 |
| `docs/audit/2026-08-06_devops-audit.md` | 未落盘 | — | 运维（429 限流） |
