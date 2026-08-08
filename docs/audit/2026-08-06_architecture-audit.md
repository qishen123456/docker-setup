# 架构审计报告（只读）

> 审计人：高见远 | 日期：2026-08-06 | 基线：backend 43415 行 / frontend 40483 行

本报告全程只读取证（Read / Grep / Glob / 只读 Bash + AST 解析）。所有行号基于 2026-08-06 当前工作区实测，旧报告行号已作废、未做任何沿用。凡未实证的判断均显式标注「（推断，未实证）」。

---

## 1. verdict

**verdict: fail**

三条独立的阻断性理由，任意一条都足以判 fail：

1. **A-01（P0，安全）**：生产问数主路径上，被 Agent3 批准的 SQL 在执行前不做只读校验（`four_agent_ask.py:8225-8263`），而被 Agent3 否决的 SQL 反而要过安检（`:8238`）。护栏方向是反的。
2. **A-02（P0，正确性）**：`backend/data/dataset_dimension_profiles.json` 在仓库中不存在，`get_dataset_profile()` 全局返回 `None`（已运行时验证），而全后端有 31 个调用点依赖它，其中 23 个在 `four_agent_ask.py` 里、位于路由与实体消解热路径上。语义层静默空转，无任何日志告警。
3. **A-03（P0，并发）**：模块级单例 `four_agent_ask_service`（`:9063`）持有 `LLMClient` 单实例（`:120-125`），每请求把用户选的 `model_id` 写进这个共享实例（`:8487`）。全后端只有一把锁且不在此处（`smartask_report_history_store.py:23`），而 SSE 每请求起裸线程（`controllers/smart_chat.py:769`）。

同时对三个必答问题的结论也都指向 fail 侧：四智能体形态不是这个系统该有的形态（第 6.1 节）、三套规则引擎实为「一数据集一引擎」的伪抽象（第 6.2 节）、护栏层位错误且可一次性修正（第 6.3 节）。

---

## 2. 现状架构还原

### 2.1 真实的调用拓扑（不是文档上的那个）

`backend/services/`、`backend/repositories/` 目录不存在——分层只存在于文档。真实拓扑如下：

```
HTTP 请求
   |
   v
[L4 接口层] controllers/smart_chat.py
   :769  worker = threading.Thread(target=run_ask, daemon=True)   <- 每请求裸线程，无池无限流
   :550  ask_flow_controller.ask(AskRequest(...))
   |
   v
[L3 编排层] ask_flow/controller.py  (227 行)
   :15-22  DEFAULT_ASK_FLOW_CONFIG  defaultFlow=basic / advancedEnabled=False
   :54     active_service() -> return self.basic_service          <- 无分支，恒定 basic
   :143-182 ask() -> self._service_for(decision).ask(...)
   |
   +--[advanced 分支，0 流量]--> smartask_advanced/service.py:1472
   |        :1404 / :1463 最终 self.fallback_service.ask(...) 回落 basic
   |
   v
[L3 薄壳] smartask_basic/service.py  (34 行)
   :5   from four_agent_ask import four_agent_ask_service
   :14  self.delegate = delegate or four_agent_ask_service        <- 纯转发，无逻辑
   |
   v
[L2+L1+L0 全部压在这一层] four_agent_ask.py  (9063 行 / 1 个类 / 156 个方法)
   :9063  four_agent_ask_service = FourAgentAskService()          <- 进程级单例
   |
   +-- ask()  :8472-8846
   |     :8487  self._preferred_model_id = model_id               <- 写共享 LLMClient（竞态点）
   |     :8491-8492  _agent1_resolve_org_subject  [LLM #1]        <- 条件触发
   |     :8655-8656  _agent1_resolve_org_subject  [LLM #1 重复]   <- 同参数二次调用
   |     :8731  route_with_agent1(...)            [LLM #2]
   |     :8738  self.repository.get_agent1_catalog()              <- 新开连接
   |
   +-- _run_pipeline()  :7857-8466
   |     :7872  for dataset_id in dataset_ids:                    <- 串行循环，无并行
   |       :7873  get_dataset_context()                           <- 新开连接，内含 8 次 cur.execute
   |       :8064  _select_sql_strategy()                          <- 内部无条件跑一遍规则引擎
   |       :8071-8074  time.sleep(random.uniform(2.0, 3.0))       <- 人为注入延迟
   |       :8107  _agent2_generate_sql()          [LLM #3(+retry)]
   |       :8178  _agent3_review()                [LLM #4(+retry)]
   |       :8187  final_sql = review["final_sql"] <- LLM 可改写 SQL
   |       :8188  _coerce_city_company_level_sql() <- 校验后再次正则改写 SQL
   |       :8225-8249  approved is False -> 只读校验 -> 仍然执行
   |       :8253  apply_row_level_filter()        <- 再次包一层子查询
   |       :8263  _execute_sql()                  <- 无任何校验
   |       :8377  _agent4_analysis()              [LLM #5]
   |
   v
[L0] datasource_router.py:192  execute_sql_for_source()
        :199  pd.read_sql_query(sql, conn)                        <- 唯一物理执行点，零护栏
```

### 2.2 一次请求的完整时序（文字还原）

1. Flask 收到 `/api/smart-chat/ask`，`smart_chat.py:769` 起一个 daemon 线程跑 `run_ask`，主线程返回 SSE 流。Flask 3.0.3 的 `app.run()` 内部 `options.setdefault("threaded", True)`，因此多请求并发进入同一进程（该事实由项目总监在隔离环境实测确认，本次不重复验证）。
2. `ask()` 第一件事就是 `self._preferred_model_id = model_id`（`:8487`）——写进程级共享的 `LLMClient`。
3. 若问题像组织主体追问（`:8491`），调 LLM 做主体纠正，产出 `rewritten_question` 覆盖 `effective_question`（`:8497-8498`）。
4. 若 `preferred_dataset_ids` 存活到 `:8655`，用**完全相同的入参**再调一次同一个 LLM（`:8656`）。`llm_client.py` 全文无任何缓存（已确认无 `lru_cache` / `cache` 字样），因此这是一次真实重复的网络往返。
5. `route_with_agent1()`（`:8731`）做语义路由，返回 `dataset_ids`。
6. `_run_pipeline()`（`:7857`）对 `dataset_ids` **串行**循环。每个数据集：拉上下文（一次 DB 连接）→ 选 SQL 策略 → 生成/复用 SQL → Agent3 复核 → 行级权限包裹 → 执行 → Agent4 解读。
7. 结果聚合（`:8434-8457`），写报告历史，SSE 推送完毕。

### 2.3 这个拓扑最关键的三个结构事实

- **没有任何并行原语。** 全后端非测试代码里 `ThreadPoolExecutor` / `concurrent.futures` / `asyncio` 出现 **0 次**；`threading.Thread` 只有 4 处，全部用于「起一个后台 worker 跑整条流水线」（`smart_chat.py:769`、`:1042`，`controllers/feishu_sync.py:214`、`:267`），没有一处用于流水线内部提速。
- **只有一把锁。** 全后端 `threading.Lock` / `RLock` 仅 `smartask_report_history_store.py:23` 一处。共享单例的其余状态全部无保护。
- **抽象层不承载任何行为。** `ask_flow` + `smartask_basic` 合计 264 行，不提供隔离、降级、契约转换中的任何一项；`ask_flow/controller.py:54` 是一行 `return self.basic_service`。

---

## 3. 架构级缺陷

严重度：P0 阻断 / P1 高 / P2 中 / P3 低。修复成本：S（1 人日内）/ M（2-5 人日）/ L（1 人周以上）。

| 编号 | 缺陷 | 证据(文件:行号) | 影响面 | 根因 | 修复成本 |
|---|---|---|---|---|---|
| A-01 | 只读护栏方向反置：批准的 SQL 不校验，否决的 SQL 才校验，物理执行点零校验 | `four_agent_ask.py:8225` `if review.get("approved") is False:` → `:8238` `if not self._is_read_only_sql(fallback_sql)` → `:8249` `final_sql = fallback_sql`；approved=True 时从 `:8225` 直落 `:8251`，`:8263 _execute_sql` 前无只读校验；`:7676-7683` normal 策略只有 `_dataset_field_validation`；`datasource_router.py:192-199` 执行点无校验 | 全部走 LLM 自由生成/改写路径的问数请求。`normal` 策略下 `final_sql` 来自 LLM 输出（`:8187 review.get("final_sql", sql_text)`） | 护栏按「策略分支」逐个补，而不是在唯一出口设闸 | S |
| A-02 | 语义画像层静默空转：数据文件不存在，31 个调用点全部拿到 None | 运行时实测：`dataset_dimension_profiles.py:9 PROFILE_PATH=backend/data/dataset_dimension_profiles.json`，`os.path.exists()` = **False**，`load_dataset_profiles()` = **{}**，`get_dataset_profile('angel_business_2026_phase1','商用事业部开单金额')` = **None**。`backend/data/` 目录存在但为空。`:30-32` 文件缺失时静默 `return {}`。调用点：`four_agent_ask.py` 23 处（含 `:1851` `:2641` `:2948` `:3024` `:3162` `:3259`）、`disambiguation/llm_arbiter.py:137,169,172,173`，全仓非测试共 31 处 | 路由层级判定、实体消解、同义词映射全部退化。`_profile_supports_level:2929 if not profile: return False` 恒 False；`:1852 if profile:` 分支恒不进入 | 声明式配置层设计并编码完成（294 行），但数据文件从未产出，且缺失被 try/except 吞掉 | S（补数据文件）/ M（补 + 加启动自检） |
| A-03 | 进程级单例 + 每请求写共享 LLM 配置 + 无锁 = 跨请求模型串用 | `:9063 four_agent_ask_service = FourAgentAskService()`；`:120-125 _llm_component()` 惰性建一次并缓存到 `self.__dict__["llm_client"]`；`:141-149` 三个 setter 全部写进该共享实例；`:8487 self._preferred_model_id = model_id`；并发来源 `controllers/smart_chat.py:769` 裸线程 + Flask threaded 默认 True；全后端唯一锁在 `smartask_report_history_store.py:23`，不覆盖此处 | 任意两个并发请求选了不同模型时互相覆盖。用户 A 的问题可能用 B 选的模型回答 | 把「请求级参数」存进了「进程级对象」 | M |
| A-04 | 同一 LLM 调用在单次请求内可重复执行 | `:8491-8492` 与 `:8655-8656` 均调 `_agent1_resolve_org_subject(question, conversation_context=memory_history, trace=trace)`，入参完全一致；`_agent1_resolve_org_subject:7121` 走 `_chat_json`；`llm_client.py` 全文无缓存（方法清单仅 `_load_llm/_activate_llm/_candidate_llm_configs/_config_signature/_stream_delta_value_to_text/_extract_stream_delta/_chat/_consume_stream/_chat_json`） | 当 `preferred_dataset_ids` 存活到 `:8655` 且问题形似组织主体追问时，额外一次约 7s 的 LLM 往返 | 两处独立演进的分支各自调用，无请求级 memo | S |
| A-05 | 快路径被人为注入 2-3 秒睡眠 | `:8071-8074` `if not golden_hit_delay_applied: delay_seconds = random.uniform(2.0, 3.0); time.sleep(delay_seconds)`，随后 `:8083 simulated_delay_ms` 写进 trace | 所有 Golden SQL 直执行命中的请求。`time.sleep` 在请求线程内，占住线程 | 产品侧「回答太快显得不可信」的权宜实现被固化进流水线 | S |
| A-06 | 多数据集查询串行，无并行 | `:7872 for dataset_id in dataset_ids:`；循环体内 `:8107` `:8178` `:8377` 各一次 LLM；跨轮共享变量只有 `golden_hit_delay_applied`（`:7871` `:8071` `:8074`）与只追加的 `dataset_results`（`:8139` `:8228` `:8239` `:8358` `:8405`） | 跨 N 个数据集的问题，端到端耗时线性放大 N 倍 | 循环体本身无跨轮数据依赖，但从未并行化 | M |
| A-07 | 规则引擎无条件预跑，结果常被丢弃 | `_select_sql_strategy:1380 rule_based_sql = self._build_rule_based_sql(question, route, context)` 在任何分支判断之前无条件执行；而 `:1500-1534` 的四个 Golden SQL 分支命中时直接 return，`rule_based_sql` 被丢弃 | 每个数据集每次请求都白跑一遍 1040 行的规则引擎（CPU 侧，非 LLM 侧） | 为了在多个分支里复用同一个变量而提前求值 | S |
| A-08 | 安全校验与执行之间 SQL 被二次改写（TOCTOU） | `:7425` 对 `sql_text` 做 `_is_read_only_sql`；`:8187 final_sql = review.get("final_sql", sql_text)`；`:8188 _coerce_city_company_level_sql()` 正则替换（实现见 `:1581-1591`）；`:8253 apply_row_level_filter()` 把 SQL 包进 `SELECT * FROM (...) AS __smartask_row_scope WHERE ...`（`data_permission_store.py:513`，且 `.rstrip(';')`）；`:8263` 才执行 | 被校验的字符串与被执行的字符串不是同一个 | 校验位置在管线中段而非出口 | S（与 A-01 同批修） |
| A-09 | 三套规则 SQL 引擎实为「一数据集一引擎」，新增数据集需新增数百行 Python | 分派逻辑 `_build_rule_based_sql:4497-4515` 全靠硬编码 `dataset_code` / `dataset_name` 字符串：`:4508-4509` → `_build_consumer_business_sql`（`:5933-6599`，667 行）、`:4511-4512` → `_build_ecommerce_sql`（`:5526-5930`，405 行）、`:4514-4515` 非 syyb 直接 `return ""`、`:4517` 起为 syyb 内联引擎（约 1010 行）。`config/dataset_node_index.json` 实测数据集总数 = **3** | 数据集数 = 引擎数 = 3。第 4 个数据集将再增约 600 行进上帝文件 | 把「数据集差异」表达成了代码分支而不是数据 | L |
| A-10 | Agent3 的否决不具约束力 | `:8225-8249`：`approved is False` 时，只要 `final_sql` 非空且通过只读校验，`:8249 final_sql = fallback_sql` 后继续执行。否决与批准的唯一差别是「否决方多过一道只读校验」 | 所有 Agent3 判否的请求 | 复核结果只用于展示（`:8211-8215` 写 trace），未接入控制流 | S |
| A-11 | 上帝文件：9063 行 / 1 类 / 156 方法，13 个方法超 100 行合计 5522 行（占方法总行 8766 的 63%） | AST 实测：`_build_rule_based_sql:4485-5524`(1040)、`route_with_agent1:3662-4412`(751)、`_build_consumer_business_sql:5933-6599`(667)、`_run_pipeline:7857-8466`(610)、`_build_layered_management_report:619-1194`(576)、`_build_ecommerce_sql:5526-5930`(405)、`ask:8472-8846`(375)、`_agent3_review:7412-7683`(272)、`confirm_by_boss:8848-9060`(213)、`_agent2_generate_sql:6601-6787`(187)、`_select_sql_strategy:1371-1549`(179)、`_detect_ambiguity:3433-3560`(128)、`_build_dataset_profile_confirmation:3309-3427`(119) | 任何改动的爆炸半径不可估 | 见第 4 节 | L |
| A-12 | 数据访问层被架空：Repository 零 DDL，建表散落 10 文件且已漂移 | `bookshelf_repository.py`（317 行）内 `CREATE TABLE` 出现 **0** 次；DDL 分布 `controllers/bookshelf.py` 15 处、`runtime_migration.py` 8 处、`system_log_store.py` 7 处、`import_bookshelf_bundle.py` 5 处、`feishu_sync_service.py` 5 处、`create_consumer_standard_dataset.py` 5 处；`controllers/bookshelf.py:526 _ensure_optional_tables(cur)` 与 `runtime_migration.py:616 _ensure_optional_tables(cur)` 为两份重复实现，后者多建 `bs_dataset_report_config` | schema 无单一真值，表结构取决于哪条代码路径先执行 | 没有迁移体系，用 `CREATE TABLE IF NOT EXISTS` 就地兜底 | L |
| A-13 | 私有方法 `_connect()` 跨 4 层被 20 处直接调用 | `controllers/bookshelf.py:597,667,825,867,890,1071,1141,1444,1785,1795,1875,2079`、`controllers/rbac.py:148`、`controllers/data_permissions.py:58`、`system_log_store.py:61`、`dataset_transform_service.py:35`、`runtime_migration.py:908,973,1074,1200`；`controllers/bookshelf.py` 内 `cur.execute` 共 68 处 | 连接池、超时、慢查询日志、只读副本路由全部无法统一落地 | 无 Repository 契约，controller 直接下钻 | M |
| A-14 | 循环依赖 `feature_flags` ↔ `rbac_store`，靠函数级 lazy import 掩盖 | `feature_flags.py:1403 from rbac_store import effective_permissions`、`feature_flags.py:1523 from rbac_store import BUILTIN_ROLE_IDS, load_rbac, save_rbac`；`rbac_store.py:88 from feature_flags import DEFAULT_FEATURE_FLAGS`。三处均在函数体内 | 权限默认值双写，权威不明 | 常量与行为放在同一模块 | S |
| A-15 | 会话态在进程内存，锁死单进程部署 | `:55 self._pending_confirmations: Dict[str, Dict[str, Any]] = {}`；`:7835-7839 _cleanup_expired_sessions` 无锁遍历后 pop；读写点 `:8871` `:8878` `:9058` | 无法多 worker 横向扩展；与 Flask 开发服务器问题是同一死结的两端 | 请求间状态放在了服务对象上 | M |
| A-16 | advanced 引擎 3649 行、零流量、核心路径回退 basic；代码默认值与运行态相反 | `smartask_advanced/` 总计 3649 行（skills 13 文件 1763 行）；`:1404` `:1463` `:1466` `:1469` 四个出口全部委托 `fallback_service`；`ask_flow/controller.py:54` 恒返回 basic。**代码默认 `fallbackToBasicOnError=True`（`controller.py:20`），而 `config/ask_flow.json` 运行态为 `false`** | 无收益的同步维护成本；配置若丢失，容错行为翻转 | 第二引擎立项后未接流量也未下线 | S（下线）/ L（接流量） |
| A-17 | 存在绕过 ask_flow 总开关的直接导入 | `controllers/bookshelf.py:1169 from four_agent_ask import four_agent_ask_service`（函数体内 lazy import） | 该路径上 feature flag、角色校验（`controller.py:90-113`）、controller probe（`smart_chat.py:472`）全部失效 | facade 无强制约束 | S |
| A-18 | `config/` 混装配置、运行态、业务数据、凭据，约 20MB | 实测 16 json + 3 md + 1 py；`smartask_report_history_store.py:23 HISTORY_FILE="smartask_report_history.json"` 写入 config/ → 实测 10.5MB，另有 `.bak-20260731` 8.9MB；`query_history.json` 503KB、`dataset_node_index.json` 315KB、`auth_tokens.json` 20KB（凭据）；`docker-compose.yml` `./config:/app/config` 整目录 bind mount | 配置无法版本化；凭据与普通配置同权限；`runtime_migration.py` 1284 行的存在意义就是给这个错位打补丁 | 「配置」与「状态」概念未区分 | M |
| A-19 | 10 个生产模块 import 期自改 `sys.path` | `four_agent_ask.py:16-18`、`app.py:15`、`bootstrap.py:29`、`dataset_report_config.py:19`、`controllers/{smart_chat.py:15, ai_models.py:13, datasources.py:12, dashboard.py:8, agents.py:9, feishu_sync.py:12}` | 同一模块可能被以两种路径导入产生两份实例，单例语义失效（推断，未实证）；打包与静态检查受阻 | 无包声明 | S |
| A-20 | 跨域反向依赖：运行时依赖建模侧工具的硬编码 SQL 模板 | `four_agent_ask.py:24 from dataset_copilot.syyb_rule_generator import BASE_SQL as SYYB_BASE_SQL`，使用点 `:4479-4482`；`_build_syyb_base_sql:4478-4483` 对该常量做**字符串 replace** 来条件性删列 | 建模工具改模板会静默改变线上问数 SQL | 模板放在了错误的模块 | S |

**分级汇总：P0 = 3（A-01 / A-02 / A-03），P1 = 8（A-04 A-06 A-09 A-10 A-11 A-12 A-13 A-15），P2 = 7（A-05 A-07 A-08 A-14 A-16 A-18 A-20），P3 = 2（A-17 A-19）。**

---

## 4. 上帝文件解剖与拆分方案

### 4.1 规模实测

`four_agent_ask.py` = 9063 行，单类 `FourAgentAskService`（`:52`）承载 156 个方法，方法体合计 8766 行。13 个超 100 行的方法合计 5522 行，占方法总行的 63%。

### 4.2 职责清单（按内聚度聚类）

| 簇 | 职责 | 代表方法（行号 / 行数） | 小计 | 目标模块 |
|---|---|---|---|---|
| C1 | syyb 规则 SQL 生成 | `_build_rule_based_sql:4485-5524`(1040，含分派头 `:4497-4515`)、`_build_syyb_base_sql:4472-4483`(12) | ~1052 | `sql/syyb/` |
| C2 | 电商规则 SQL 生成 | `_build_ecommerce_sql:5526-5930`(405) | 405 | `sql/ecommerce/` |
| C3 | 消费者规则 SQL 生成 | `_build_consumer_business_sql:5933-6599`(667) | 667 | `sql/consumer/` |
| C4 | 路由与歧义消解 | `route_with_agent1:3662-4412`(751)、`_detect_ambiguity:3433-3560`(128)、`_build_dataset_profile_confirmation:3309-3427`(119)、`_agent1_resolve_org_subject:7069-7159`(91) | 1089 | `route/` |
| C5 | 流水线编排 | `_run_pipeline:7857-8466`(610)、`ask:8472-8846`(375)、`_agent3_review:7412-7683`(272)、`_agent2_generate_sql:6601-6787`(187)、`_select_sql_strategy:1371-1549`(179)、`_agent4_analysis:7751-7855`(105) | 1728 | `pipeline/` |
| C6 | 报告装配 | `_build_layered_management_report:619-1194`(576) | 576 | `report/` |
| C7 | 确认会话 | `confirm_by_boss:8848-9060`(213)、`_create_confirmation_session:7841`、`_cleanup_expired_sessions:7835` | ~250 | `confirmation/` |
| C8 | 校验与执行 | `_is_read_only_sql:354-355`、`_dataset_field_validation:357-406`、`_execute_sql:7685-7749`、`_coerce_city_company_level_sql:1568-1591` | ~180 | `guard/` + `execution/` |
| C9 | 其余 140 个 <100 行方法 | — | ~2800 | 按上述归属分派 |

### 4.3 耦合边界：真正卡住拆分的是共享 self 状态，不是行数

| 共享状态 | 定义 | 扩散 | 为什么卡住拆分 |
|---|---|---|---|
| `self.repository` | `:54-56` | `self.repository.*` 共 19 处（含 `:7873` `:8738`） | 每次调用新开连接。拆分后每个子模块都要持有它，等于把 god state 复制 N 份。必须先解 A-13 |
| `self._pending_confirmations` | `:55` | `:7837` `:7839` `:7849` `:8878` `:9058` | 进程内存态（A-15）。先外置，否则只是把内存 dict 搬个位置 |
| `self._dataset_node_index` | `:60` + 6 处懒重载（`:1691-1694` `:1731-1734` `:1760-1763` `:1805-1808` `:2414-2416` `:2981-2984`） | 6 写 / 8 读 | 与 `organization_route_resolver.py:98-113` 的永久缓存语义相反，拆分会放大不一致 |
| `self.llm_client`（经 `_llm_component()`） | `:120-125` | 8 个 LLM stage 全部经此 | 每请求被写（A-03）。必须先请求级化 |
| `self._intent_resolver` | `:342-347` 惰性建，`_build_intent_resolver:68-82` 注入 11 个 IntentPorts | 1 处 | **这是唯一已经健康的形态**，应作为其他簇的抽取范式 |

### 4.4 拆分顺序、风险与回滚点

前提门槛（不满足则不要动刀）：为 C1/C2/C3 三套规则引擎补齐「输入 → SQL 字符串」的 characterization 快照测试。这三簇合计 2112 行，是业务真值所在，现有 `backend/tests/` 下 16 个文件已直接 `from four_agent_ask import FourAgentAskService`，基座可用但覆盖不足。

| 步 | 动作 | 前置 | 风险 | 回滚点 |
|---|---|---|---|---|
| S0 | 补 C1/C2/C3 快照测试；建立「拆分前后 SQL 字节级一致」的对拍脚本 | 无 | 低 | 纯新增测试，无回滚需求 |
| S1 | 抽 C8 到 `guard/`，同时落地第 6.3 节的单闸口 | 无 | 低。函数纯粹，无 self 状态 | 单 commit revert |
| S2 | 抽 C2（电商，405 行，无 self 状态依赖，仅读 `v_feishu_tbldianshang`） | S0 | 低。**这是最佳试点**，用它验证对拍脚本 | 单 commit revert |
| S3 | 抽 C3（消费者，667 行） | S2 | 中 | 单 commit revert |
| S4 | 抽 C1（syyb，1052 行）；同批把 `SYYB_BASE_SQL` 移出 `dataset_copilot`（A-20） | S3 | 高。1040 行单函数分支密集 + 跨域常量 | 需分 3-4 个 commit，每个都跑对拍 |
| S5 | 抽 C6（报告装配）；**同批治理 `report_spec_builder.py:731-1755` 的 1025 行单函数** | S1 | 中。不同批做则搬家不减负 | 单 commit revert |
| S6 | 会话态外置（A-15）→ 抽 C7 | A-15 修复 | 中 | 需数据迁移，回滚需保留旧内存路径一个版本 |
| S7 | 解 A-13（`_connect` 转 public）→ 抽 C4 | A-13 修复 | 高。同时依赖 DB 与索引双状态 | 分 commit |
| S8 | 抽 C5，`four_agent_ask.py` 收敛为 ≤300 行 facade | S1-S7 全部完成 | 最高。god state 汇聚点 | 保留 facade 兼容层，`FourAgentAskService` 类名不变以免打断 16 个测试文件 |

**关键提醒**：`docs/架构优化方案.md`（v4）把全部注意力放在 S8，但 S6/S7 的前置没做，这正是为什么方案迭代到 v4、`_resolve_query_intent` 已成功拆出（现 `:342-347` 仅 6 行，`smartask_engine/intent/resolver.py` 789 行承接），而 `four_agent_ask.py` 仍是 9063 行。顺序错了，不是决心不够。

---

## 5. 边界与契约

### 5.1 `ask_flow/contracts.py` 的三个结构是不是真的边界？

**结论：AskRequest / ConfirmRequest 是真边界但形同虚设；FlowDecision 是真边界且有效。**

- `AskRequest` / `ConfirmRequest`：在 `controllers/smart_chat.py:550` `:716` `:871` `:992` 被构造，进入 `ask_flow/controller.py:143-182`，然后 `self._service_for(decision).ask(...)`。但下游 `smartask_basic/service.py:19 def ask(self, **kwargs)` 是 `**kwargs` 透传，`four_agent_ask.py:8472 def ask(...)` 又展开成 9 个位置参数。**契约在第一跳之后就解体了**——DTO 只活了一层，之后退化为 kwargs 字典。这意味着增删字段不会有任何类型层面的提示。
- `FlowDecision`：这个是有效的。`decide()`（`controller.py:90-113`）综合 requested_flow / datasetPolicies / defaultFlow / advancedEnabled / role 产出决策，`_service_for(decision)` 消费。逻辑内聚、可测试（`tests/test_ask_flow_controller.py` 存在）。
- **但这个有效边界有一个破口**：`controllers/bookshelf.py:1169` 在函数体内 `from four_agent_ask import four_agent_ask_service`，完全绕过 `ask_flow`。该路径上 FlowDecision 从未产生（A-17）。

### 5.2 basic/advanced 双引擎的实际分流

**实际分流：100% basic，0% advanced。**

证据链：
1. `config/ask_flow.json` 运行态：`"advancedEnabled": false`，`"advancedRoles": ["super_admin"]`。
2. `ask_flow/controller.py:54 def active_service(self): return self.basic_service` —— 无条件返回，无分支。
3. 即便 `decide()` 判出 advanced，`smartask_advanced/service.py` 的四个出口 `:1404`（ask）、`:1463`（confirm_by_boss）、`:1466`（route_with_agent1）、`:1469`（write_controller_probe）全部委托 `self.fallback_service`，而 `:40 self.fallback_service = fallback_service or basic_ask_service`。
4. 因此 advanced 的定性不是「半成品第二引擎」，而是**带插件框架的透传层**。3649 行代码（含 13 个 skill 共 1763 行）在生产上不改变任何一个字节的输出。

**附带发现（配置与代码语义相反）**：`ask_flow/controller.py:20` 代码默认 `"fallbackToBasicOnError": True`，而 `config/ask_flow.json` 运行态是 `false`。如果配置文件丢失或被重置，容错行为会静默翻转。

### 5.3 真正缺失的契约

系统里唯一被严肃对待的契约是「报告结构」——`report_spec_builder.build_report_spec`（`report_spec_builder.py:731-1755`，1025 行单函数）产出的 spec。但它没有 schema 定义、没有版本号、没有校验。前端消费它，advanced 的 `skills/answer_contract.py` 也试图复刻它。这是一个事实上的核心契约却完全隐式（推断：未逐条追前端消费点，仅从 advanced 侧存在 `answer_contract.py` 推断其重要性）。

---

## 6. 可演进性评估：要支撑 70% 通过率，当前架构缺什么

`nl2sql_improvement_plan.md:4` 记录当前商用 18% / 消费者 7.5%，`:436` 目标整体 70%+。该文档 `:41-72` 提出的五层架构（意图识别 → 语义实体解析 → SQL 生成策略 → SQL 校验 → 报告卡片）方向正确。逐层核对现状：

| 计划分层 | 现状 | 缺口 |
|---|---|---|
| Layer 1 意图识别 | **已建成**。`smartask_engine/intent/resolver.py`(789 行) 产出 `filter` / `comparison` / `aggregate` 等意图（`:209` `:244` `:287` 等），`_select_sql_strategy:1447` 已按意图分流到规则 SQL | 意图类型覆盖面待评估，但架构位到位 |
| Layer 2 语义实体解析 | **已编码但运行时为空**。`dataset_dimension_profiles.py` 294 行完整实现了同义词/成员/分组匹配，但数据文件不存在（A-02，已运行时验证） | **这是 70% 目标最便宜的一块**。计划里「口语化同义词 10% → 70%」对应的正是这一层。补一个 JSON 文件即可激活 31 个已有调用点 |
| Layer 3 SQL 生成策略 | **部分建成但形态错误**。策略选择器 `_select_sql_strategy:1371-1549` 存在且分层清晰；但底下的「模板」是三套硬编码 Python 引擎（A-09），不是模板 | 见 6.2。新增数据集/新增问题类型的边际成本是「写几百行 Python」而不是「加一条配置」 |
| Layer 4 SQL 校验 | **存在但方向反置**（A-01 / A-08） | 见 6.3 |
| Layer 5 报告卡片 | **已建成**。`build_report_spec` + `dataset_report_config.py:233-237 intentPolicies.ranking.defaultTopN` | 1025 行单函数，可维护性差但功能到位 |

**架构层面的总结论**：要到 70%，缺的不是新组件，缺的是（a）激活已建成但空转的 Layer 2，（b）把 Layer 3 从代码分支改成数据驱动。这两件事都不需要引入新框架。

下面正面回答三个必答问题。

---

### 6.1 问题一：四智能体流水线是不是这个系统该有的形态？

**不是。这个系统的正确形态是「一次 LLM 做语义翻译 + 确定性引擎做剩下全部」，四智能体串行流水线是错的。**

不和稀泥，理由如下：

**(1) LLM 在这条链上做的大部分事情，不需要 LLM。**

实测 8 个 LLM stage：`agent1.node_index_entity_resolution`(`:2621`)、`agent1.entity_resolution`(`:2716`)、`agent1.route`(`:3646`)、`agent2.sql_generate`(`:6714`,retry `:6755`)、`agent1.org_subject`(`:7126`)、`agent2.sql_repair`(`:7400`)、`agent3.sql_review`(`:7638`,retry `:7668`)、`agent4.analysis`(`:7822`)。其中：

- **Agent4 已经被规则替代了，而且是在代码里替代的。** `_agent4_analysis:7760-7770`：当数据集是 syyb（主力数据集）时，直接 `return self._build_fallback_analysis(...)`，不调 LLM。这是仓库内的既成事实，证明业务解读用规则可以接受。剩下两个数据集扩同样的处理即可，**成本 S**。
- **Agent2/3 在规则命中时已经被跳过。** `_run_pipeline:8093-8104` 走 `rule_based` 分支时不调 Agent2；`_agent3_review:7424-7487` 对 `rule_sql`/`trusted_sql` 策略直接 passthrough，不调 LLM。所以「最省路径 15.30s」里 94.4% 的 LLM 耗时，主要来自 Agent1 侧的多次调用与 Agent3 的 normal 路径。
- 因此真正不可替代的只有 **Agent1 的语义理解**（把自然语言翻译成结构化意图 + 实体）。这恰好就是 `nl2sql_improvement_plan.md:74` 自己写的原则：「不要让 LLM 直接生成复杂 SQL，而是让 LLM 把问题翻译成中间结构，再用确定性逻辑生成 SQL」。**计划文档的判断是对的，只是现有实现没有照它做。**

**(2) 关于「哪些 Agent 之间没有真实数据依赖、可以并行」——后端专家怀疑的那一对，答案是：不能并行，有硬依赖。**

`Agent1 组织主体解析` 与 `Agent1 路由` **存在真实数据依赖，不可直接并行**。证据链完整：

```
:8492  org_subject_resolution = self._agent1_resolve_org_subject(question, ...)
:8496  rewritten_question = str((org_subject_resolution or {}).get("rewritten_question") or "").strip()
:8497-8498  if rewritten_question: effective_question = rewritten_question
:8730  route_question = effective_question or question
:8731  route = self.route_with_agent1(route_question, ...)
```

并且 `:8728-8729` 有一条明确的代码注释解释这个依赖为什么必须存在：「主体纠正后 effective_question 已是"丁杰的业绩"，路由层应基于纠正后的问题走，避免再用原始"商用事业部丁杰"识别出事业部层级」。这是一次真实 bug 修复留下的约束，直接并行会让该 bug 回归。

**但可以做投机并行**：两者的输入都只是 `question` + `memory_history`，互不写对方状态。可以同时发起 `_agent1_resolve_org_subject(question)` 与 `route_with_agent1(question)`，仅当 `rewritten_question` 非空且与原问题不同时，丢弃投机路由结果并用改写后的问题重跑。命中率取决于「组织主体追问」占比（推断，未实证：需线上 trace 统计 `agent1.org_subject_resolved` 事件占比才能算收益）。这样最坏情况不变、最好情况省掉一整次 LLM 往返。

**(3) 真正没人提、但确定可并行的，是数据集循环。**

`_run_pipeline:7872 for dataset_id in dataset_ids:` 是串行的，循环体内含 Agent2/Agent3/Agent4 三次 LLM。我核对了跨轮依赖：循环体只写两个外部变量——`dataset_results`（`:8139` `:8228` `:8239` `:8358` `:8405`，纯 append）和 `golden_hit_delay_applied`（`:7871` `:8071` `:8074`，一个只用于「只 sleep 一次」的开关，本身就是 A-05 该删的东西）。`context` 每轮独立重建（`:7873`）。**除去那个该删的 sleep 开关，循环体之间零共享状态，是干净的 embarrassingly parallel。** 跨 N 数据集的问题可直接降到 1/N 的流水线耗时。这是全系统性价比最高的并行点，成本 M。

**(4) 关于 Agent3「LLM 复核 LLM 生成的 SQL」是否提供真实价值——不提供，应当删除。**

三条独立证据：

- **它的否决没有约束力。** `:8225-8249`，`approved is False` 时只要 SQL 非空且只读，`:8249` 照常执行。否决与批准的唯一差别是否决方多过一道只读校验——**这意味着 Agent3 当前唯一的实际作用，是充当那道本该在别处的安检门**。
- **它在可信路径上本来就不工作。** `:7424-7487`，`trusted_sql`/`rule_sql` 策略直接 passthrough 返回，不调 LLM。也就是说 Agent3 只在 `normal`（LLM 自由生成）路径上真正运行。
- **它在唯一真正运行的路径上，反而放大了风险。** `:7676-7678`，LLM 返回的 `final_sql` 直接成为待执行 SQL；`:8187` 采纳；而这条路径**没有只读校验**（A-01）。所以 Agent3 在 normal 路径上做的事是：花约 7 秒，让一个 LLM 去改写另一个 LLM 写的 SQL，然后把改写结果不加安检地送去执行。

**裁决**：删除 Agent3 的 LLM 复核，把它降级为纯确定性校验器（只读校验 + 字段字典校验 + 表白名单），放到第 6.3 节说的单闸口里。单次请求直接省一次 LLM 往返（约 7s，占端到端约 46%），且安全性上升而非下降。

**(5) 目标形态**

```
问题
 |
 v
[单次 LLM] 语义翻译：question -> {intent, target_level, entities, metric, filter, top_n}
 |         （复用现有 smartask_engine/intent/resolver.py + 激活 dataset_dimension_profiles）
 v
[确定性] SQL 装配器（数据驱动，见 6.2）
 |
 v
[确定性] 单闸口校验（见 6.3）-> 执行
 |
 v
[确定性] 报告装配（build_report_spec）+ 规则解读（_build_fallback_analysis 已有）
 |
 v
[可选 LLM，异步/流式] 业务解读润色——不阻塞首屏
```

按现有实测口径（单次 LLM p50 = 7.15s，SQL 执行 0.86s）粗算：LLM 调用从 5-7 次降到 1 次，端到端应落在 8-10s 量级；若把最后的解读润色改为答案先出、解读后补，首屏可进 3s 内（推断，未实证：需实际改造后压测确认）。

---

### 6.2 问题二：三套硬编码规则 SQL 引擎的边界在哪，能不能收敛成一套？

**边界是 `dataset_code` 字符串，没有任何业务语义。能收敛，而且目标形态已经在仓库里了。**

**(1) 三套各自的触发条件（全部是硬编码字符串匹配，无重叠）**

分派点在 `_build_rule_based_sql:4497-4515`：

| 引擎 | 触发条件（代码原文位置） | 命中数据集 |
|---|---|---|
| 消费者 | `:4497-4500` `dataset_code in {"consumer_business_standard_v1","public_feishu_tbl_xioafeizhe_609826"} or "消费者" in dataset_name` → `:4509` | id=2 `consumer_business_standard_v1` |
| 电商 | `:4506` `dataset_code == "feishu_tbldianshang" or "电商事业部" in dataset_name` → `:4512` | id=62 `feishu_tbldianshang` |
| syyb | `:4501-4504` `dataset_code in {"angel_business_2026","angel_business_2026_phase1"} or dataset_name in {"商用事业部","商用事业部（阶段一升级版）"}` → `:4517` 起内联 | id=3 `angel_business_2026_phase1` |
| （无） | `:4514-4515` 其余一律 `return ""` → 落 `agent_generate`，交给 LLM | 任何新数据集 |

`config/dataset_node_index.json` 实测数据集总数 = 3。**所以「三套引擎」的真相是「一个数据集一套引擎」，边界不是问题类型的边界，是数据集身份的边界。**

**(2) 覆盖的问题类型高度重叠——它们在做同一件事**

按行段统计同一批概念的出现次数：

| 概念 | syyb(`:4485-5524`) | 电商(`:5526-5930`) | 消费者(`:5933-6599`) |
|---|---|---|---|
| `达成率` | 22 | 7 | 25 |
| `filter_metric_column` | 7 | 0 | 7 |
| `filter_operator` | 5 | 1 | 4 |
| `ORDER BY` | 22 | 1 | 11 |
| `LIMIT` | 18 | 6 | 9 |

三者都在处理同一组问题类型：单点查询、条件过滤、排序取极值、TopN、层级汇总、对比。差异只在字段名、层级名和表名。

代码里有一处直接自证重复：`:4529-4530` 的注释写着「与 `_build_ecommerce_sql` 保持一致：intent 层保留原始值，SQL 阶段根据问题中的单位换算」——开发者在**手工维护三份副本的一致性**。

**(3) 真正的差异不是业务复杂度，是数据形态成熟度**

| 引擎 | FROM 目标（实测） | 内嵌 CTE 数 | `jsonb_typeof` 抽取处 | 内嵌 SQL 模板块 | 行数 |
|---|---|---|---|---|---|
| 电商 | `v_feishu_tbldianshang`（**数据库视图**） | 0 | 0 | 0 | 405 |
| 消费者 | `public.feishu_tbl_xioafeizhe`（原始 JSONB 表）+ 应用层拼 6 个 CTE（字段提取/标准行/汇总结果/分公司排序/头尾分公司/最佳分公司） | 6 | 0 | 1 | 667 |
| syyb | `angel_group_data`（原始 JSONB 表）+ 应用层拼 13 个 CTE | 13 | 16 | 14 | 1040 |

电商引擎最终产出就是一条 `SELECT {cols} FROM v_feishu_tbldianshang WHERE {where} ORDER BY {order} {limit};`（`:5929`）。**它已经是目标形态**：把 JSONB 拍平、层级计算、指标派生全部下沉到数据库视图，应用层只做"意图 → WHERE/ORDER/LIMIT"的装配。

syyb 之所以要 1040 行，不是因为商用事业部业务更复杂，而是因为它在 Python f-string 里做电商用视图做的事。极端案例：`_build_syyb_base_sql:4478-4483` 用 `SYYB_BASE_SQL.replace("TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务部') = 'array' ...)) AS 业务部,", "'' AS 业务部,")` —— **靠对 SQL 字符串做精确 replace 来条件性删掉一列**。这种写法一旦上游模板改一个空格就静默失效。

**(4) 收敛方案**

分两步，都可在停机窗口内做：

**第一步：数据形态对齐（消除 87% 的代码量差异）**
为 syyb 和消费者各建一个数据库视图 `v_angel_business` / `v_consumer_business`，产出与电商视图同构的拍平结果（条线 / 层级 / 节点名称 / 上级名称 / 总任务金额 / 年度开单金额 / 达成率 / 剩余任务金额）。做完后，`:4517-5524` 的 13 个 CTE 和 16 处 jsonb 抽取全部消失，syyb 引擎会塌缩到与电商同一量级（约 400 行）。这一步不改任何应用逻辑，风险最低。

**第二步：一个引擎 + 三份声明式数据集规格**
三个引擎塌缩后差异只剩：视图名、指标列名映射（`syyb_metric_map:4540-4553` 这类）、可过滤列白名单（`allowed_filter_columns:4527`）、层级序列、单位换算规则（`normalize_syyb_threshold_value:4529-4538`）。全部是数据。抽成：

```
sql/
  builder.py        # 唯一装配器：intent + spec -> SQL（<=300 行）
  spec_loader.py    # 读取数据集规格
data/dataset_sql_specs.json
  {
    "angel_business_2026_phase1": {
      "view": "v_angel_business",
      "levels": ["事业部","分公司","代表处","业务部","业务代表"],
      "metrics": {"总任务金额": {...}, "年度开单金额": {...}, "达成率": {"unit":"ratio"}},
      "filterable": ["总任务金额","年度开单金额","达成率","剩余任务金额"],
      "default_order": "年度开单金额 DESC"
    },
    "feishu_tbldianshang": { ... },
    "consumer_business_standard_v1": { ... }
  }
```

**收敛后的收益量化**：2112 行 → 约 300 行装配器 + 3 份 JSON。新增第 4 个数据集的成本从「写约 600 行 Python 进上帝文件」降到「建一个视图 + 加一段 JSON」。这同时是第 6.1 节目标形态和 `nl2sql_improvement_plan.md:41-72` Layer 3 的落地方式。

**（重要衔接）** 这份 `dataset_sql_specs.json` 应当与 A-02 里缺失的 `dataset_dimension_profiles.json` 合并成同一份数据集规格文件。目前系统里已经有四处分散的数据集元数据：`data/dataset_dimension_profiles.json`（缺失）、`config/dataset_node_index.json`（315KB，存在）、`dataset_report_config.py:233-237` 的 intentPolicies、以及散在代码里的硬编码 `dataset_code` 判断。收敛成一份，是拆分上帝文件的前提。

**(5) 回答「规则覆盖率能提到多少」**

当前规则覆盖 = 3/3 数据集，但**每个数据集内部的问题类型覆盖有限**——`nl2sql_improvement_plan.md:14-22` 记录聚合 / 多条件组合 / 列间比较 / 子查询「全部失败」。这些失败不是因为规则引擎写不出来，而是因为 Layer 2（实体与同义词，A-02）为空、以及规则分支要靠手写。

数据驱动化 + 激活 Layer 2 之后，规则可覆盖的类型是：单点查询、层级汇总、单/多条件过滤、排序极值、TopN、同层对比、列间比值。对照 `nl2sql_improvement_plan.md:427-436` 的目标矩阵，这几类占了整体权重的大部分，70% 是可达的（推断，未实证：需按 90 道测试题逐题标注可规则化比例才能给出精确数字，建议改造前先做这个标注，它比任何架构讨论都更能定方向）。

---

### 6.3 问题三：安全护栏的架构位置错了——正确的位置在哪？

**正确位置：`datasource_router.execute_sql_for_source` 作为唯一强制闸口。项目总监的倾向是对的，且不会影响其他调用方——恰恰相反，它会把现在最松的路径拉到和最严路径同一水平。**

**(1) 先把现状的荒谬程度量化**

| 路径 | 可信度 | 只读校验 | 字段校验 | 行级权限 | 位置 |
|---|---|---|---|---|---|
| Agent2 修复后的 SQL | 低 | 有 | 无 | 后置 | `:7407` |
| `trusted_sql`/`rule_sql`（规则引擎/人工 Golden） | **最高** | 有 | 有 | 后置 | `:7425` `:7441` |
| `normal`（LLM 自由生成/改写） | **最低** | **无** | 有 | 后置 | `:7676-7683` |
| 被 Agent3 否决的 fallback_sql | 低 | 有 | 无 | 后置 | `:8238` |
| 执行前修复后重试 | 低 | 有 | 无 | `:8298` | `:8296` |
| **物理执行点** | — | **无** | **无** | — | `:7694` / `datasource_router.py:192-199` |

规律：越可信校验越严，越不可信越松；被否决的要过安检，被批准的不用过。

**(2) 还有一个总监未提及、但更严重的问题：校验过的字符串不是执行的字符串（A-08）**

即便在有校验的 `trusted_sql` 路径上，时序也是：

```
:7425  _is_read_only_sql(sql_text)                 <- 校验 A 字符串
:8187  final_sql = review.get("final_sql", sql_text)
:8188  final_sql = _coerce_city_company_level_sql(...)   <- 正则改写（实现 :1581-1591）
:8253  final_sql = apply_row_level_filter(...)           <- 包一层子查询（data_permission_store.py:513）
:8263  _execute_sql(final_sql)                     <- 执行 B 字符串
```

在分支式护栏布局下，这类 TOCTOU 几乎不可能靠"再多加一处校验"根治——每加一条改写路径就要记得补一次校验。这本身就是"闸口应该在出口"的最强论据。

**(3) 关于"会不会影响 bookshelf 等其他调用方"——不会，我逐个核对了全部 5 个调用点**

| 调用点 | 现有防护 | 下沉后影响 |
|---|---|---|
| `four_agent_ask.py:7694`（生产问数） | 无 | **从零防护变为有防护。这是收益方** |
| `controllers/bookshelf.py:1090`（SQL 测试） | `:1068 _is_read_only_sql(sql_text)` + `:1088 apply_row_level_filter` + `_wrap_preview_sql(limit)` | 重复校验，幂等无害。可后续删除上层重复 |
| `controllers/bookshelf.py:1300`（数据集调试执行） | `:1280` **双重**校验 `service._is_read_only_sql(final_sql) or not _is_read_only_sql(final_sql)` + `:1295` 行级过滤 + limit 包裹 | 同上 |
| `controllers/bookshelf.py:1366`（修复后重试） | `:1343` 双重校验 + `:1362` 行级过滤 + limit 包裹 | 同上 |
| `build_dataset_node_index.py:248`（离线建索引脚本） | 无 | SQL 由脚本自己构造、全是 SELECT。需确认不误伤（推断，未实证：建议下沉时给该脚本走显式 `trusted=True` 旁路并记录审计日志） |

**这里有一个必须说破的事实**：`controllers/bookshelf.py` 的三个执行点是**开发调试用的 SQL 预览路径**，它们有三重防护（只读校验 + 行级权限 + LIMIT 包裹）；而 `four_agent_ask.py:7694` 是**生产问数主路径**，它一重都没有。防护强度和路径重要性完全倒挂。

**(4) 关于"是否该用 AST 解析替代关键字黑名单"——应该，但不是第一步**

先看现有实现 `ask_engine_sql.py:50-67`：

```python
normalized = re.sub(r"/\*.*?\*/", " ", str(sql_text or ""), flags=re.S)
normalized = re.sub(r"--.*?$", " ", normalized, flags=re.M).strip().lower()
if not normalized: return False
if not (normalized.startswith("select") or normalized.startswith("with")): return False
blocked_keywords = ("insert","update","delete","drop","truncate","alter",
                    "create","replace","grant","revoke","merge","call",
                    "execute","vacuum","analyze","copy")
return re.search(rf"\b(?:{'|'.join(blocked_keywords)})\b", normalized) is None
```

它的缺陷分两类：

*误杀（影响可用性，且是当下就在发生的）*：黑名单里 `analyze`、`copy`、`call`、`merge`、`create`、`update` 都是英文常用词。任何 SQL 只要在字符串字面量、列别名或注释残留里出现这些词就被拒。例如 `WHERE 渠道 = 'Call Center'` 会被判为非只读。这在中文字段为主的当前数据集里不常发生，但一旦接入英文字段数据集立刻爆发（推断，未实证：未构造实际用例触发）。

*漏放（影响安全）*：
- `_dataset_field_validation:391` 的表提取正则是 `\b(?:from|join)\s+((?:[a-zA-Z_][\w]*\.)[a-zA-Z_][\w]*)`，**要求表名带点（schema 限定）**。不带点的 `FROM pg_authid`、`FROM 其他数据集的表` 根本不会被捕获，`qualified_tables` 为空 → `missing_tables` 为空 → 校验通过。
- `:393 if allowed_tables:` —— 数据集若没有字段字典/schema 登记，`allowed_tables` 为空，表校验整个跳过。
- 只读 ≠ 安全。`SELECT * FROM pg_authid`、`SELECT pg_read_file(...)` 全部满足"以 select 开头且不含黑名单词"。是否可利用取决于数据源连接账号权限（推断，未实证：未查 `config/datasources.json` 的账号权限等级，建议 DevOps 侧核实连接账号是否为 superuser）。
- `apply_row_level_filter:513` 用 `.rstrip(';')` 只剥离尾部分号，对语句中段的 `;` 无处理；不过它把原 SQL 包进子查询，多语句会变成语法错误而失败（这是运气，不是设计）。

**结论**：AST 解析（`sqlglot` 或 `pglast`）能同时解决误杀和漏放——它能准确判断语句类型、枚举真实引用的表（不论是否 schema 限定）、检测多语句。但引入解析器有兼容性风险（对 PostgreSQL 方言、JSONB 操作符 `->>`、中文标识符的支持需验证）。所以分两步。

**(5) 正确的护栏架构**

```
[L0 唯一强制闸口]  datasource_router.execute_sql_for_source(source_id, sql, *, policy)
     |
     +-- 1. 语句形态校验     单语句 / 仅 SELECT|WITH        <- 第一步用现有正则，第二步换 AST
     +-- 2. 表白名单校验     真实引用表 ⊆ 数据集登记表        <- AST 后才准确
     +-- 3. 行级权限         apply_row_level_filter          <- 从 :8253 下沉到这里
     +-- 4. 结果集上限       统一 LIMIT 包裹                  <- 借用 bookshelf 的 _wrap_preview_sql
     +-- 5. 语句超时         SET LOCAL statement_timeout      <- 当前完全没有
     +-- 6. 审计日志         记录 谁/哪个数据集/最终SQL/耗时
     |
     v
   pd.read_sql_query(sql, conn)
```

关键设计点：

- **闸口接收的必须是最终字符串。** 所有改写（`_coerce_city_company_level_sql`、`apply_row_level_filter`）都必须发生在闸口**之内且在校验之前**，或者干脆禁止在闸口之外改写 SQL。这是根治 A-08 的唯一办法。因此建议把 `apply_row_level_filter` 的调用点从 `four_agent_ask.py:8253` / `controllers/bookshelf.py:1088,1295,1362` 全部收进闸口。
- **上层的分支式校验全部删除**（`:7407` `:7425` `:7441` `:8238` `:8296`，以及 bookshelf 的 `:1068` `:1280` `:1343`）。留着它们只会让人以为护栏是分散的、从而继续在新分支里忘记加。
- **Agent3 的 LLM 复核在此一并删除**（见 6.1(4)），其职责由闸口的确定性校验承接。
- **离线脚本走显式旁路**：`build_dataset_node_index.py:248` 用 `policy="trusted_offline"`，但仍走审计日志。

**改造成本**：闸口本体 S（约 1 人日，正则版）；下沉 `apply_row_level_filter` 并清理上层校验 M；换 AST 解析 M（含方言验证）。停机窗口下可一次性完成，无需灰度。

---

## 7. 重构路线图

按依赖排序。所有波次都利用「内部试用、可停机」窗口——不做双写、不做平滑迁移、不保留兼容分支。

### W0：先修不需要动结构的（0.5 周，全部 S 成本）

| # | 动作 | 解决 | 停机窗口用法 |
|---|---|---|---|
| 0.1 | 产出 `backend/data/dataset_dimension_profiles.json`，并在 `load_dataset_profiles` 加启动期存在性自检（缺失即启动失败，不再静默返回 `{}`） | **A-02** | 无需停机，但需重跑 90 题基线确认路由行为变化 |
| 0.2 | 删除 `:8071-8074` 的 `time.sleep(random.uniform(2.0,3.0))` | A-05 | 直接删 |
| 0.3 | 请求级 memo：`_agent1_resolve_org_subject` 在单次 `ask()` 内按 `question` 缓存，消除 `:8656` 重复调用 | A-04 | 直接改 |
| 0.4 | `_select_sql_strategy:1380` 改惰性求值，仅在分支真正需要时才跑规则引擎 | A-07 | 直接改 |
| 0.5 | 删 `controllers/bookshelf.py:1169` 旁路，改走 `ask_flow_controller` | A-17 | 直接改 |
| 0.6 | 抽 `permission_defaults.py` 解 `feature_flags ↔ rbac_store` 循环 | A-14 | 直接改 |
| 0.7 | `SYYB_BASE_SQL` 从 `dataset_copilot` 移到 `sql_templates/syyb.py` | A-20 | 直接改 |
| 0.8 | 统一 `ask_flow` 代码默认值与 `config/ask_flow.json`（`fallbackToBasicOnError`） | A-16 半条 | 直接改 |
| 0.9 | 补 C1/C2/C3 规则引擎的 characterization 快照测试与对拍脚本 | 拆分前置 | 纯新增 |

W0 结束时应可观测到：单次问数减少 1 次 LLM 往返（0.3）+ 减少 0-3s 睡眠（0.2），且路由质量因 0.1 而变化——**0.1 必须配合 90 题回归**，因为它会激活 31 个此前恒为 None 的调用点，行为变化面很大。这是 W0 唯一有风险的动作，建议单独一个 commit、单独回归。

### W1：安全闸口（0.5 周）

| # | 动作 | 解决 |
|---|---|---|
| 1.1 | 在 `datasource_router.execute_sql_for_source` 建唯一闸口（正则版校验 + LIMIT + statement_timeout + 审计日志） | A-01 |
| 1.2 | `apply_row_level_filter` 从 4 个调用点下沉进闸口 | A-01 / A-08 |
| 1.3 | 删除上层全部分支式校验（`:7407` `:7425` `:7441` `:8238` `:8296`，bookshelf `:1068` `:1280` `:1343`） | A-08 |
| 1.4 | 删除 Agent3 的 LLM 复核，降级为确定性校验；`_agent3_review` 保留 policy 分支中的字段校验部分 | A-10 + 6.1(4) |
| 1.5 | `build_dataset_node_index.py:248` 走 `trusted_offline` 显式旁路 | 兼容性 |

W1 结束时：物理执行点有强制护栏，且单次问数再少 1 次 LLM 往返（约 7s）。

### W2：并发正确性与部署解锁（1 周）

| # | 动作 | 解决 | 依赖 |
|---|---|---|---|
| 2.1 | LLM 配置请求级化：`model_id` 不再写共享单例，改为随调用链传递或 `contextvars` | **A-03** | 无 |
| 2.2 | 会话态 `_pending_confirmations` 外置到 DB 表 | A-15 | 无 |
| 2.3 | 数据集循环并行化：`_run_pipeline:7872` 改 `ThreadPoolExecutor`（先删 `golden_hit_delay_applied`，已由 0.2 完成） | A-06 | 0.2 / 2.1 |

2.1 与 2.2 完成后，服务才真正无状态，才具备切 WSGI + 多 worker 的前提（该项归 DevOps 域，本报告只标注前置关系，不给部署方案）。

### W3：数据形态与规则引擎收敛（2 周）

| # | 动作 | 解决 | 依赖 |
|---|---|---|---|
| 3.1 | 建 `v_angel_business` / `v_consumer_business` 视图，与 `v_feishu_tbldianshang` 同构 | A-09 前置 | 停机建视图 |
| 3.2 | syyb / 消费者引擎改查视图，删除 13 个内联 CTE 与 16 处 jsonb 抽取 | A-09 | 3.1 + 0.9 对拍 |
| 3.3 | 合并 `dataset_dimension_profiles.json` + 新增 SQL spec 为单一 `dataset_specs.json` | A-02 / A-09 | 0.1 |
| 3.4 | 三引擎塌缩为 `sql/builder.py` 单装配器 + 声明式 spec | A-09 | 3.2 / 3.3 |

W3 结束时 2112 行规则代码降到约 300 行，新增数据集的边际成本从数百行 Python 变成一段 JSON。这是达成 70% 通过率目标的结构前提。

### W4：数据层归位（1.5 周）

| # | 动作 | 解决 |
|---|---|---|
| 4.1 | 建 `migrations/` 承接全部 DDL，删除 `controllers/bookshelf.py:526` 与 `runtime_migration.py:616` 两份重复 `_ensure_optional_tables` | A-12 |
| 4.2 | `_connect()` 转 public `connection()`，20 个调用点统一；引入连接池 | A-13 |
| 4.3 | 报告历史 / 查询历史入库；`config/` 拆为 `config/`（静态入 git）+ `state/`（运行态）+ `secrets/`（凭据） | A-18 |
| 4.4 | `runtime_migration.py` 退化为「DB dump + git checkout」，主体删除 | A-18 衍生 |

### W5：上帝文件拆分（3 周）

严格按第 4.4 节的 S1-S8 执行。前置 W1（S1 已并入）、W2（S6 依赖）、W4（S7 依赖）、0.9（对拍）。

### W6：收尾（0.5 周）

| # | 动作 | 解决 |
|---|---|---|
| 6.1 | advanced 引擎裁决执行：下线到独立分支，主干仅保留 `smartask_advanced/registry.py` 供 UI 展示能力清单 | A-16 |
| 6.2 | 删除 `smartask_basic` 薄壳，`ask_flow` 直接持有引擎 | 拓扑简化 |
| 6.3 | 删除全部 `sys.path.insert`，backend 声明为单一 package | A-19 |
| 6.4 | 加 import 方向门禁测试，锁死单向 DAG | 防回归 |

### 路线图的两个判断

**第一，W0 + W1 加起来只有 1 周，却解决 3 个 P0 中的 2 个，并且直接砍掉 2 次 LLM 往返（约 14s，占当前端到端 15.30s 的绝大部分）。** 这一周的投入产出比高于后面所有波次之和。如果只能做一件事，做 W0.1（补那个缺失的 JSON 文件）——它是全项目唯一一处「补一个文件就激活 31 个已写好的调用点」的机会。

**第二，不要先拆上帝文件。** W5 排在最后不是因为它不重要，而是因为它的三个最大簇（C4 路由 / C5 编排 / C7 确认）分别卡在 A-13、A-03、A-15 上。这三个前置不解决，硬拆的结果就是把 god state 复制成 N 份，比现在更糟。`docs/架构优化方案.md` 迭代到 v4、`_resolve_query_intent` 已成功抽出（现 `:342-347` 仅 6 行）而文件仍是 9063 行，就是顺序错误的实证。

---

## 附录 A：本次审计中已运行时验证（非静态推断）的结论

1. `dataset_dimension_profiles.PROFILE_PATH` 指向 `backend/data/dataset_dimension_profiles.json`，`os.path.exists()` 返回 `False`；`load_dataset_profiles()` 返回 `{}`；`get_dataset_profile('angel_business_2026_phase1','商用事业部开单金额')` 返回 `None`。`backend/data/` 目录存在但为空目录。
2. `config/dataset_node_index.json` 中 `datasets` 数组长度为 3，分别是 id=2 `consumer_business_standard_v1`、id=3 `angel_business_2026_phase1`、id=62 `feishu_tbldianshang`。
3. `four_agent_ask.py` AST 解析：单类 156 方法，方法体合计 8766 行，13 个方法超 100 行合计 5522 行。
4. `report_spec_builder.py` AST 解析：`build_report_spec` 单函数 `:731-1755`，1025 行。
5. 全后端非测试代码中 `ThreadPoolExecutor` / `concurrent.futures` / `asyncio` / `multiprocessing` 出现 0 次。
6. `bookshelf_repository.py` 中 `CREATE TABLE` 出现 0 次。

## 附录 B：本报告明确未做的判定（归属其他审计席位）

- Flask 内置服务器、WSGI 选型、容器与部署形态：归 DevOps。本报告仅在 A-15 / W2 标注架构前置关系。
- SSE 队列无界、具体性能数字、慢查询定位：归后端实现质量席位。本报告仅引用总监提供的实测口径（单次 LLM p50 = 7.15s、SQL 0.86s、最省路径 15.30s、LLM 占 94.4%）。
- 测试覆盖率、具体缺陷复现：归 QA。本报告在 4.4 S0 与 W0.9 提出拆分前置的测试要求，不给覆盖率结论。
- 前端 XSS 与渲染：归前端席位。
