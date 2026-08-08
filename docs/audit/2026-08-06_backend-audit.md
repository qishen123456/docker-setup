# 后端审计报告（只读）

> 审计人：贝洛奇 | 日期：2026-08-06 | 仓库：`/Users/ltl123/smartask/sa1.0/smartask` | 分支：docker-setup | HEAD：8858bef
>
> 基线：`backend/` 136 个 .py 文件 / 43415 行，其中 33 个文件超过 300 行门禁。
>
> 审计方式：全程只读（Read / Grep / Glob / 只读 Bash）。未修改 `backend/` `frontend/` `config/` 下任何文件，未执行任何写库、写配置、启动服务的操作。
>
> 实测数据来源有两类，均非估算：
> 1. `backend/logs/smartask_trace.jsonl` —— 仓库自带的真实生产埋点，79 条记录（type 分布：event 75 / controller_probe 3 / summary 1）。
> 2. 本机纯 CPU/磁盘基准 —— 仅对 `config/*.json` 做 `json.load` 与 `deepcopy` 计时，无任何副作用。
>
> Docker 环境在审计期间不可用（`docker ps` 返回空），无法做容器内压测。凡涉及运行时行为（TLS 握手成本、建连开销、DDL 锁等待、并发竞态实际触发）的判断，均已标注「（推断，未实证）」。

---

## 1. verdict

verdict: fail

判定依据分三类，任一类单独成立即不可交付：

1. **正确性**：存在 3 条「不报错但算错」的沉默逻辑错误（B-1 跨请求模型覆盖、B-25 负缓存永久钉死、B-27 非确定性路由），其中 B-27 已由生产 trace 实证复现。
2. **安全**：只读护栏在 Agent3 的 LLM 改写路径后不复检（B-2），且 SQL 执行点完全无护栏（B-3），纵深防御为零。
3. **部署完整性**：3 张生产表不在任何迁移文件中，唯一定义处是 HTTP 请求处理器的内联 DDL（B-23），干净环境部署后缺表，而健康检查给出假阳性。

问题总数 27 条：P0 9 条 / P1 12 条 / P2 6 条。

**与既有基线最大的分歧**：性能瓶颈不在数据库、不在配置读盘，而是高度集中在**一个 stage** 上。详见第 3 节。

---

## 2. findings 总表

### 2.1 P0（9 条）

| ID | 类别 | 问题 | 证据(file:line) | 影响 | 修复方向 | 成本 |
|---|---|---|---|---|---|---|
| B-1 | 并发/正确性 | 单例服务的模型选择是共享可变状态，跨请求互相覆盖 | `backend/four_agent_ask.py:9063` `four_agent_ask_service = FourAgentAskService()`；`:8487` `self._preferred_model_id = model_id`；`:147-149` setter 实际写 `self._llm_component()._preferred_model_id`；`:127-149` `_llm_client`/`_llm_model` 同为共享属性；`backend/llm_client.py:46-51` `_activate_llm` 直接改 `self._llm_model` 与 `self._llm_client` | A 用户选 GLM-5.1、B 用户选 DeepSeek，B 的 `_activate_llm` 会在 A 的 Agent 串行链中途改掉共享态。结果是「答案出来了但用的不是你选的模型」，不报错、不进日志。沉默逻辑错误 | 模型配置改为按请求传参（`_chat(..., config=cfg)`），不落实例属性；或 LLM 组件按请求实例化 | 中 |
| B-2 | 安全 | 只读护栏在 Agent3 正常 LLM 路径改写 SQL 后不复检 | `backend/four_agent_ask.py:7407` 与 `:7425` 两条路径调用 `_is_read_only_sql`；`:7678-7682` 正常 LLM 路径拿到 `final_sql` 后只做 `_dataset_field_validation`，未复检只读 | Agent3 本身是 LLM，可将 SELECT 改写为任意语句。护栏在改写之前生效、改写之后失效 | `_agent3_review` 返回前对 `final_sql` 无条件复检 | 低 |
| B-3 | 安全 | SQL 执行点无护栏，纵深防御缺失 | `backend/four_agent_ask.py:7685-7694` `_execute_sql` 直接调 `datasource_router.execute_sql_for_source(...)`，无 `_is_read_only_sql` | 任何绕过 Agent3 的路径（规则引擎、`:8280-8332` 修复重试、未来新增调用方）都能直达数据库 | 只读校验下沉到 `execute_sql_for_source` 入口作为最后一道闸 | 低 |
| B-4 | 性能 | LLM 客户端每次调用重建，丢弃连接池并重做 TLS | `backend/llm_client.py:112-113` 每次 `_chat` 都 `_load_llm()` + `_candidate_llm_configs()`；`:118-119` 候选循环内 `self._activate_llm(config)`；`:46-51` `self._llm_client = self._openai_factory(api_key=..., base_url=...)` | 每次调用新建 OpenAI 客户端，底层 httpx 连接池作废，重新 DNS + TCP + TLS 握手（推断，未实证：握手成本量级未在容器内实测） | 按 `(base_url, api_key)` 缓存 client 实例，`_activate_llm` 只切 model 字段 | 低 |
| B-5 | 性能/稳定性 | 数据源连接无 connect_timeout、无 statement_timeout、结果集无上限 | `backend/datasource_router.py:156-162` `psycopg2.connect(...)` 与 `:166-173` `pymysql.connect(...)` 均无 `connect_timeout`（对比 `backend/bookshelf_repository.py:41-58` 有 `connect_timeout=8`）；`:199` `pd.read_sql_query(sql, conn)` 全量载入 DataFrame | 数据源抖动时线程无限期挂起，SSE 线程不回收；LLM 生成的无 LIMIT 查询会把整表拉进内存 | 补 `connect_timeout=8`；PG 加 `options='-c statement_timeout=30000'`；`read_sql_query` 加 `chunksize` 或强制注入 LIMIT | 低 |
| B-6 | 数据访问 | N+1：整个 catalog 循环内每个数据集打 7 条 SELECT | `backend/four_agent_ask.py:3953` `for dataset in catalog:` 内调 `self.repository.get_dataset_context(dataset["id"], question, top_k_samples=5)`；`backend/bookshelf_repository.py:131-246` 单次调用顺序执行 7 条 SELECT，每条都 `with self._connect()` 新建连接 | N 个数据集 = 7N 条查询 + 7N 次建连（推断，未实证：建连开销未实测） | `get_dataset_context` 改批量 `WHERE dataset_id = ANY(%s)` 后内存分组；连接复用 | 中 |
| B-16 | 数据访问/部署 | DDL 写在请求路径上，每次请求执行 4 条建表/改表语句 | `backend/controllers/bookshelf.py:526-576` `_ensure_optional_tables(cur)` 执行 3 条 `CREATE TABLE IF NOT EXISTS` + 1 条 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`；调用点 5 处：`:668` `:891` `:1445` `:1796` `:1876` | 原定性为性能开销，经 B-23 证据后重新定性：这些 DDL **承担了本该由迁移承担的职责**，删除前必须先补迁移，否则新环境缺表。性能只是副作用 | 迁移进 `backend/migrations/`，请求路径不碰 DDL | 中 |
| B-23 | 数据访问/部署 | 三张生产表不在任何迁移文件中，唯一定义处是请求处理器内联 DDL | 逐表核对 `backend/migrations/` 全部 7 个 .sql：`bs_common_questions` 无、`bs_dataset_external_configs` 无、`bs_regression_cases` 无。三者唯一定义在 `backend/controllers/bookshelf.py:526-570`。另 `:571-576` 的 `ALTER TABLE bs_schema_definitions ADD COLUMN IF NOT EXISTS source_id` 同样不在迁移中（迁移里的 `source_id` 是 `bs_datasets` 上的列，见 `backend/migrations/20260330_bookshelf_schema.sql:11`） | 走正规 bootstrap 部署一套新环境，这三张表根本不存在，必须等用户碰巧访问 5 个端点之一才被建出。而健康检查 `backend/controllers/bookshelf.py:579-585` 经 `repo.is_ready()`（`backend/bookshelf_repository.py:91-106`）只探测 `bs_datasets`，给出假阳性 ready=true | 把 `:526-576` 的 DDL 搬进新迁移 .sql，加进 `backend/bootstrap.py:49-57` MIGRATIONS 列表 | 低 |
| B-24 | 数据访问 | 三套建表机制并存互相打架 | A 正规迁移：`backend/bootstrap.py:49-57` MIGRATIONS 列 7 个 .sql，`main()` `:420-425` 启动期全跑；B 半吊子：`backend/bookshelf_repository.py:60-89 ensure_schema()` 只跑 `20260330_bookshelf_schema.sql` 一个（路径硬编码 `:61-65`），且 `:71-74` 探测到 `bs_datasets` 存在即 early return；C 请求路径内联：`backend/controllers/bookshelf.py:526` 与 `backend/runtime_migration.py:616` 两份重复实现 | 后加的 6 个迁移永远不会被 B 应用；C 是为绕过 B 的缺陷而长出的补丁。`bs_dataset_report_config` 已在 `backend/migrations/20260430_report_config.sql` 定义，`backend/runtime_migration.py:616` 又内联建一遍——同一函数里「缺失」与「冗余」两种病并存 | 废掉 B 和 C 统一到 A；`ensure_schema()` 改为遍历 MIGRATIONS 或直接删除 | 中 |
| B-27 | 正确性/性能 | 组织主体识别零缓存导致同输入重复 LLM 调用，且因 temperature 非零产生非确定性路由 | 定义 `backend/four_agent_ask.py:7069-7159`，`:7121` 直接 `_chat_json`，函数体内无任何缓存；调用点 `:8493`（条件 `:8492`）、`:8656`（条件 `:8655`）同属 `ask()`（定义于 `:8472`）；第三处 `:8981`（条件 `:8980`）属 `confirm_by_boss`（定义于 `:8848`）。`backend/llm_client.py:142` `temperature=0.1` 非 0 | 见第 4 节完整分析。已由 trace 实证：同一输入两次调用返回不同结果，导致 `:8662` 分支走向不同，同一用户问同一问题可能走不同数据集选择路径 | `:8656-8660` 复用 `:8491` 已有的 `org_subject_resolution`；`:8981` 补 `trace=trace` | 低 |

### 2.2 P1（12 条）

| ID | 类别 | 问题 | 证据(file:line) | 影响 | 修复方向 | 成本 |
|---|---|---|---|---|---|---|
| B-7 | 并发 | `_pending_confirmations` 无锁，遍历与写入竞态 | `backend/four_agent_ask.py:55` 裸 dict 定义；`:7837` 列表推导遍历 `.items()`；`:7839` `.pop()`；`:7849` 写入；`:8878` `.get()`；`:9058` `.pop()` | `:7837` 遍历期间另一线程在 `:7849` 写入，触发 RuntimeError: dictionary changed size during iteration。SSE 为裸线程（`backend/controllers/smart_chat.py:769`），竞态真实可达 | 加 `threading.RLock` 包住 `:7837-7839` 与 `:7849`；长期迁 Redis | 低 |
| B-8 | 错误处理 | `_chat_json` 吞掉所有异常返回 fallback，无日志无重抛 | `backend/llm_client.py:251` `except Exception:`；`:261` `return fallback` | LLM 挂了、JSON 解析失败、超时全部表现为「返回了一个空 fallback」。Agent1 路由拿到空 fallback 会静默走错分支 | 至少 `_append_trace(..., "error", ...)` 落埋点；区分可降级与必须报错两类 | 低 |
| B-9 | 错误处理 | 流式解析静默吞异常 | `backend/llm_client.py:189` `except Exception: delta = ""` | 解析失败被当成空片段，最终答案缺内容而用户无感知 | 计数加埋点，连续失败 N 次中断流并报错 | 低 |
| B-10 | 并发 | SSE 裸线程 + 无界队列 + 无总超时 | `backend/controllers/smart_chat.py:705` `queue.Queue()` 无 maxsize；`:769` `threading.Thread(target=run_ask, daemon=True)` 无线程池无上限；`:773-778` 心跳循环无总时长上限；`:1042` confirm_by_boss 同样模式 | 每个 SSE 请求裸起线程无上限；生产者快于消费者时队列无限增长。配合 B-5 的无超时连接，线程可能永不退出 | `ThreadPoolExecutor(max_workers=N)`；`Queue(maxsize=200)`；加总超时强制结束 | 中 |
| B-11 | 性能 | golden SQL 路径固定随机 sleep 2 至 3 秒 | `backend/four_agent_ask.py:8072-8074` `time.sleep(random.uniform(2.0, 3.0))` | 给命中 golden 的请求（本该最快路径）凭空加 2 至 3 秒 | 删除，或改为可配置且默认 0 | 低 |
| B-12 | 日志 | 生产热路径打 DEBUG print | `backend/controllers/smart_chat.py:743` `print(f"[DEBUG] stream result ...")` 位于 ask 流式主循环 | 每次提问往 stdout 打完整 result，噪声 + 序列化开销 + 可能泄漏业务数据 | 删除或降级为 trace 埋点 | 低 |
| B-13 | 日志 | trace 双写同一文件，两个写入器互不知情，均无 rotation | `backend/four_agent_ask.py:61-62` `TraceLogger(os.path.join(CURRENT_DIR,"logs","smartask_trace.jsonl"))`；`:159` `logging.FileHandler(os.path.join(log_dir,"smartask_trace.jsonl"))` 同一路径；`backend/trace_logger.py:38` 每事件 `open(path,"a")`；`:40-41` `except Exception: pass` | 一个是持久 fd 带缓冲的 FileHandler，一个是每次 open/append 的裸写，并发追加可能撕行。磁盘写满时静默吞掉，日志无声消失。无 rotation | 统一到一个 writer；换 `RotatingFileHandler`；写失败计数上报 | 中 |
| B-14 | 可诊断性 | 75 条事件里 60 条缺 trace_id，链路断裂 | 实测 `backend/logs/smartask_trace.jsonl` 共 79 行，其中 60 条 event 记录缺 `trace_id` 字段。`backend/trace_logger.py:25` 只在 `_new_trace` 生成一次 trace_id，逐事件写出时未强制透传 | 审计中亲身撞到：一组累计 137.4 秒的 LLM 调用（17 次 `agent1.org_subject` response）无法归并到具体请求。线上表现为「看得到慢、找不到是哪次请求慢」 | `_append_trace` 强制注入 trace_id；Flask 层用 `g` 或 contextvars 承载 | 中 |
| B-15 | 日志 | 182 处 print，全仓仅 2 个文件用 logging | 实测 `backend/*.py` + `backend/controllers/*.py` 共 182 处 `print(`。Top：`backend/regenerate_dataset_from_doc.py` 22、`backend/feishu_sync_service.py` 21、`backend/app.py` 21、`backend/vanna_core.py` 12。`import logging` / `getLogger` 仅出现在 `backend/dataset_report_config.py:10,23` 与 `backend/four_agent_ask.py:2,152` | print 无级别、无时间戳、无 trace_id、不可采集、不可降噪，容器化后全部混进 stdout | 统一 logging + JSON formatter；print 保留在 scripts 类文件，服务代码清零 | 中 |
| B-17 | 性能 | 无数据库连接池，每次查询新建连接 | `backend/bookshelf_repository.py:41-58` `_connect()` 每次 `psycopg2.connect(...)`；配合 B-6 被放大 | 建连成本被 N+1 放大（推断，未实证） | `psycopg2.pool.ThreadedConnectionPool` 或 SQLAlchemy engine pool | 中 |
| B-25 | 错误处理 | 负缓存永久钉死，一次瞬时读失败导致组织路由整进程失效 | `backend/organization_route_resolver.py:104-113`：`if self._node_index_cache is not None: return self._node_index_cache`；`except Exception: self._node_index_cache = {}` | 磁盘抖动或文件正被写入时读失败，`{}` 被永久缓存（`{}` is not None 成立），该进程生命周期内组织路由全部返回空，且静默无日志。沉默逻辑错误 | 失败不写缓存，或缓存带 TTL；失败必须落埋点 | 低 |
| B-26 | 配置/运维 | 315KB 索引加载一次永不失效，改配置必须重启进程 | `backend/four_agent_ask.py:60` 构造期加载；`:9063` 模块级单例；`:1691-1694` `:1731-1734` `:1760-1763` `:1805-1808` 等处守卫为 `if not isinstance(node_index, dict)`，而 `:84-93` 失败时也 `return {"datasets": [], "flat_alias_index": []}`（仍是 dict），该分支永不进入，是死代码 | `config/dataset_node_index.json` 任何修改都不生效，必须重启进程。运维改配置后「看起来没反应」，易误判为改错位置 | 加 mtime 检查；或明确文档化为「改配置需重启」 | 低 |

### 2.3 P2（6 条）

| ID | 类别 | 问题 | 证据(file:line) | 影响 | 修复方向 | 成本 |
|---|---|---|---|---|---|---|
| B-18 | 安全 | 只读护栏的注释剥离不完整 | `backend/ask_engine_sql.py:50-67` `_is_read_only_sql` 只 `re.sub` 剥 `/* */`（re.S）与 `--`（re.M）；未处理 MySQL 的 `#` 行注释；未按 `;` 拆分多语句；判定依赖 startswith(select/with) 加关键字黑名单 | 黑名单目前能兜住主流写操作关键字，非立即可利用。但「剥注释不全 + 关键字黑名单」是脆弱组合，漏一个词即穿透 | 改白名单：解析首个语句要求 SELECT/WITH，其余拒绝；用 sqlparse 替代正则 | 中 |
| B-19 | 安全 | 规则引擎 f-string 拼 SQL，部分片段未走转义 | `backend/four_agent_ask.py:5929` `sql = f"SELECT {select_cols} FROM v_feishu_tbldianshang WHERE {where_clause} ORDER BY {order_by} {limit_clause};"`；`:5903` `:5905` `:5907` `:5909` 用了 `quote()`（定义 `:5592-5593`，做 `'` 加倍转义），但 `:5912` `:5919` 是裸插值 `f"层级级别 = '{actual_level}'"`；另见 `:4681` `:4836`，以及 `backend/ask_engine_sql.py:36-47` | 已核实 `actual_level` 来自 `backend/four_agent_ask.py:5716` `level_cfg["actual"]`（内部配置枚举），非用户直控，**当前不可注入**。风险在于「部分转义部分裸拼」的风格，后续维护者易把用户输入接到裸拼分支 | 统一走 `quote()` 或参数化；裸拼分支加白名单断言 | 低 |
| B-20 | 性能/存储 | trace 事件内存累积 + 流式增量全量落盘 | `backend/trace_logger.py` `_append_trace` 持续 append 到 `trace["events"]`，`_flush_trace` 再把全量 summary 写一遍。实测唯一一条 summary 记录 94201 字节 / 67 个事件，其中 49 个是 delta 流式增量事件；`backend/controllers/smart_chat.py:710` `trace_events` 另存最多 500 条 | 单次请求 trace 内存驻留近 100KB，同一批事件写两遍。长回答场景 delta 线性膨胀 | delta 不入 summary；summary 只留聚合指标 | 低 |
| B-21 | 可维护性 | 核心文件 9063 行，33 个文件超 300 行门禁 | `backend/four_agent_ask.py` 9063 行；`backend/controllers/bookshelf.py` 2214 行；`backend/feature_flags.py` 1565 行；`backend/controllers/smart_chat.py` 1069 行。全 backend 136 个 .py / 43415 行，其中 33 个超 300 行 | 单文件承载路由分发、四个 Agent 的 prompt、三套规则 SQL 引擎、会话管理、trace。改一处要在 9000 行里定位，review 不可能覆盖 | 按 Agent 拆包、规则引擎拆包、会话管理独立 | 高 |
| B-22 | 性能 | 配置文件每次调用重读磁盘 + deepcopy | `backend/config_manager.py:124` `read_json` 无 mtime 缓存；`backend/feature_flags.py:1455-1459` `load_feature_flags()` = `read_json` + `deepcopy(DEFAULT_FEATURE_FLAGS)`；`backend/data_permission_store.py:102`；`backend/config_manager.py:621` `:725` | 实测后降级到 P2。基准见第 3.4 节：合计 2.38ms，相对 LLM p50 7150ms 占 0.03% | 加 mtime 缓存（成本低顺手做），但不作为性能优化项 | 低 |
| B-28 | 规范 | 日志文案含 emoji，违反团队 P0 规则 | `backend/bootstrap.py:408` `log("⚠️ PostgreSQL 不可达，跳过迁移与首次导入；后端仍将启动以便排错。")` | 违反「错误消息中不使用 emoji」。全仓仅此一处，其余日志文案干净 | 改纯文本 | 低 |

---

## 3. perf_hotpath

### 3.1 实测：单次 LLM 调用耗时分布

解析 `backend/logs/smartask_trace.jsonl` 中 `status == "response"` 的事件，按 `duration_seconds` 统计。已按 trace_id 去重，排除 summary 记录与逐行事件的重复计数。

| stage | 样本数 | min | p50 | p90 | max | 累计 |
|---|---|---|---|---|---|---|
| `agent1.org_subject` | 19 次 LLM 往返 | 3.50s | 7.15s | 11.88s | 16.74s | **151.84s** |
| `datasource.execute_sql` | 1 | 0.86s | 0.86s | 0.86s | 0.86s | 0.86s |

**`agent1.org_subject` 一个 stage 占全部实测耗时的 99.44%**（151.84 / 152.70）。

`agent2` / `agent3` / `agent4` 在这批样本中各只出现 1 次，且埋点分别为 `agent2.sql_generate.rule_based`、`agent3.sql_review.trusted_passthrough`、`agent4.analysis.rule_based` —— **全部走规则引擎，零 LLM 调用**。

### 3.2 实测：完整链路拆解（trace_id 99eab3f2，问题「东部表现怎么样」）

| 环节 | 埋点 stage | 实测耗时 | 占比 |
|---|---|---|---|
| Agent1 组织主体第 1 次 | `agent1.org_subject` | 10.18s | 66.5% |
| Agent1 组织主体第 2 次 | `agent1.org_subject` | 4.26s | 27.8% |
| SQL 执行 | `datasource.execute_sql` | 0.86s | 5.6% |
| **合计（有埋点部分）** | | **15.30s** | **100%** |

关键：这条 trace 走的是**最省路径**（Agent2/3/4 全部命中规则引擎），仍需 15.3 秒，其中 LLM 占 94.4%、数据库占 5.6%。而这 14.44 秒的 LLM 时间里，**4.26 秒是同输入重复调用**（见第 4 节），占端到端 27.8%。

### 3.3 LLM 调用链的代码定位

| 顺序 | Agent | 调用点 | 是否必经 |
|---|---|---|---|
| 1 | Agent1 路由 | `backend/four_agent_ask.py:3646` `_chat_json(... stage="agent1.route")` | 是 |
| 2 | Agent1 组织主体 | `backend/four_agent_ask.py:7121`，由 `:8493` 与 `:8656` 两处触发 | 条件触发，实证会重复 |
| 3 | Agent1.5 实体消解 | `backend/four_agent_ask.py:2711`，`_run_pipeline` `:7933` 调用 | 是 |
| 4 | Agent2 生成 SQL | `backend/four_agent_ask.py:6709` `:6750`，`_run_pipeline` `:8107` 调用 | 规则引擎未命中时 |
| 5 | Agent3 复核 | `backend/four_agent_ask.py:7395` `:7633` `:7663`，`_run_pipeline` `:8178` 调用 | 是 |
| 5b | Agent3 修复重试 | `backend/four_agent_ask.py:8280-8332`（再一轮 Agent3 加 execute） | SQL 执行失败时 |
| 6 | Agent4 分析 | `backend/four_agent_ask.py:7817` `self._chat(... stage="agent4.analysis")`，`_run_pipeline` `:8377` 调用 | 是 |

LLM SQL 路径（规则引擎未命中）= 5 至 7 次串行调用。按实测 p50 7.15s 估算，纯 LLM 等待 35.8 至 50.1 秒（**推断，未实证**：p50 取自 `agent1.org_subject`，其余 Agent 的 prompt 更长、max_tokens 更大——Agent4 为 1600，见 `backend/four_agent_ask.py:7820`——实际只会更慢。这些 stage 我没有实测样本）。

### 3.4 实测：配置读盘基准（本机纯 CPU/磁盘）

| 操作 | 耗时 | 相对 LLM p50 7150ms |
|---|---|---|
| `json.load` `config/feature_flags.json`（63KB） | 0.984 ms | 0.014% |
| `deepcopy` feature_flags dict | 1.396 ms | 0.020% |
| `json.load` `config/dataset_node_index.json`（316KB） | 3.803 ms | 0.053% |
| `json.load` `config/ai_settings.json`（3.3KB） | 0.109 ms | 0.002% |
| `json.load` `config/datasources.json`（1.3KB） | 0.076 ms | 0.001% |

结论：配置读盘不构成性能问题。把它列入性能优化清单是错配优先级。

### 3.5 优化优先级（按实测收益排序）

1. **消除 `agent1.org_subject` 重复调用（B-27）** —— 实测省 4.26s / 15.30s = 27.8%，成本 S，且顺带修正确性问题。**收益最高、风险最低。**
2. **减少 LLM 调用总次数** —— 合并 Agent1 与 Agent1.5、扩大规则引擎覆盖，每减一次省 p50 7.15s。
3. **LLM 调用并行化** —— Agent1 路由与 Agent1 组织主体若无数据依赖可并发（推断，未实证：依赖关系需架构师确认）。
4. **删除 `time.sleep(random.uniform(2.0, 3.0))`（B-11）** —— 零成本。
5. **复用 HTTP client（B-4）** —— 省每次调用的 TLS 握手。
6. **数据库侧（B-6 / B-17）** —— 实测 DB 仅占 5.6%，收益上限有限。但 B-5 的超时缺失属稳定性问题，必须补。
7. **配置读盘缓存（B-22）** —— 占比 0.03%，不作为优化项。

---

## 4. B-27 专项：组织主体识别的重复调用与非确定性路由

这是本次审计中唯一**由生产 trace 完整实证**的缺陷，且同时具备性能与正确性两重影响。

### 4.1 根因

`_agent1_resolve_org_subject`（`backend/four_agent_ask.py:7069-7159`）函数体内无任何缓存，`:7121` 每次直接调 `_chat_json` 打一次 LLM。

### 4.2 三个调用点

| 调用点 | 所属方法 | 条件 | 入参 | 是否带 trace |
|---|---|---|---|---|
| `backend/four_agent_ask.py:8493` | `ask()`（定义 `:8472`） | `:8492` `self._looks_like_org_subject_question(question)` | `question` / `conversation_context=memory_history` / `trace=trace` | 是 |
| `backend/four_agent_ask.py:8656` | `ask()` | `:8655` `preferred_dataset_ids and self._looks_like_org_subject_question(question)` | `question` / `conversation_context=memory_history` / `trace=trace` | 是 |
| `backend/four_agent_ask.py:8981` | `confirm_by_boss()`（定义 `:8848`） | `:8980` `if not original_subject_name` | `question` / `conversation_context=[]` | **否** |

### 4.3 冗余性证明（逐条已复核）

**命题一：`:8493` 与 `:8656` 入参完全相同。**

已核实 `question` 与 `memory_history` 在 `:8493` 至 `:8656` 区间内没有任何重新赋值。区间内唯一形如 `question=` 的出现是 `:8550` 的关键字实参 `question=question`，非赋值语句。成立。

**命题二：`:8655` 的条件是 `:8492` 的严格子集。**

两者共用 `self._looks_like_org_subject_question(question)`，`:8655` 额外要求 `preferred_dataset_ids` 为真。该判定函数定义在 `backend/ask_engine_entity.py:71-112`，经完整阅读确认为**纯函数**：函数体只对入参 `question` 做 `re.sub` 与 `re.search`，不读任何实例状态、不读全局、不做 IO。因此 `question` 不变则返回值不变。

结论：`:8656` 触发时，`:8491` 定义的 `org_subject_resolution` 必然已在 `:8493` 被赋值。

**命题三：`org_subject_resolution` 在两次调用之间未被改写。**

全量触点为 `:8491`（初始化 None）、`:8493`（赋值）、`:8498` `:8507` `:8508` `:8509` `:8521` `:8533`（均为只读），下一次赋值发生在 `:8981`（属另一方法）。区间内仅有 3 处早返回（`:8565` `:8573` `:8583`），触发即不会走到 `:8656`。成立。

三条命题均成立，故 `:8656` 的调用是**纯冗余**，复用 `:8491` 的结果零风险。

### 4.4 trace 实证

`backend/logs/smartask_trace.jsonl`，trace_id `99eab3f2`，事件时序：

```
15:47:41  agent1.org_subject  request -> response 10.18s  subject_name="东部"
15:47:51  agent1.org_subject_resolved   rewritten_question="东部的表现"
15:47:51  request.received
15:47:51  agent1.org_subject  request -> response  4.26s  subject_name=""
15:47:55  agent1.preferred_dataset_bypass
```

该时序与代码行号顺序**逐一对应**，可确认两次调用就是 `:8493` 与 `:8656`：

| trace 事件 | 埋点代码位置 |
|---|---|
| 第 1 次 `agent1.org_subject` | `backend/four_agent_ask.py:8493` |
| `agent1.org_subject_resolved` | `backend/four_agent_ask.py:8503` |
| `request.received` | `backend/four_agent_ask.py:8548` |
| 第 2 次 `agent1.org_subject` | `backend/four_agent_ask.py:8656` |
| `agent1.preferred_dataset_bypass` | `backend/four_agent_ask.py:8726` |

### 4.5 这不只是性能问题

`backend/llm_client.py:142` 的 `temperature=0.1` 不是 0。相同 prompt 的两次调用返回了不同结果：第一次 `subject_name="东部"`，第二次 `subject_name=""`。

后果链：`:8661` 取 `subject_name` 为空字符串 → `:8662` `if subject_name:` 判假 → `:8663-8676` 的 node_index 歧义释放检查**整段被跳过** → `preferred_dataset_ids` 不被清空 → 数据集选择走向与第一次结果不一致。

即：**同一用户问同一问题，两次运行可能选中不同数据集**。这是非确定性路由，属沉默逻辑错误类别。

### 4.6 可观测性缺口

`:8981` 的调用不传 `trace`，该次 LLM 调用在埋点中完全隐形。所有基于 trace 的耗时统计（包括本报告第 3 节）都**少算了这一次**。真实 LLM 耗时高于 151.84s。

### 4.7 修复

1. `:8656-8660` 改为复用 `:8491` 的 `org_subject_resolution`。由 4.3 三条命题保证安全。
2. `:8981` 至少补 `trace=trace`。注意它传 `conversation_context=[]`，语义与前两处不同（不带历史），不能简单合并。
3. 长期：`temperature` 改 0，或对结构化抽取类调用单独设 0。

预期收益：trace 99eab3f2 场景端到端从 15.30s 降至约 11.04s，省 27.8%。成本 S。

---

## 5. B-16 专项：LLM 候选重试机制的三个独立缺陷

`backend/llm_client.py:53-85` `_candidate_llm_configs` 把所有 `is_active` 配置塞进候选列表；`:118` 循环；`:159` `retryable = index < len(candidate_configs) and self._should_retry(exc)`；`:171-172` 不可重试才 raise，否则继续下一个候选。

`self._should_retry` 由构造注入（`backend/llm_client.py:29`），实参为 `ask_engine_utils._should_retry_with_another_model`（注入点 `backend/four_agent_ask.py:113`），真实定义在 `backend/ask_engine_core.py:31-39`，命中即换模型的异常清单：

```
AuthenticationError / PermissionDeniedError / APITimeoutError
APIConnectionError / InternalServerError / RateLimitError
```

`RateLimitError` 与 `APITimeoutError` 是日常事件，不是异常事件。

### 5.1 三条缺陷

- **B16-a 模型配置确定性接管（并发触发）**：`backend/llm_client.py:113` 每次 `_chat` 重读 `_preferred_model_id`，而 `ask()` `:8487` 每请求只写一次。B 请求进来后，A 请求剩余的所有 Agent 调用全部读到 B 的值。**必然发生，非概率事件。** 即 B-1。
- **B16-b 客户端与模型名撕裂配对（真竞态）**：`backend/llm_client.py:136` 读 `self._llm_client`、`:137` 读 `self._llm_model`，两次独立读；而 `_activate_llm`（`:46-51`）两次写之间夹着 `_openai_factory(...)` 的构造开销。窗口宽于普通 TOCTOU，可能出现「A 的 client 配 B 的 model 名」。
- **B16-c 失败自动改投其他配置（单请求即触发，与并发无关）**：一旦命中限流或超时，A 用户的完整 prompt（`:132-133` 实证含 system_prompt 截断上限 12000 字、user_prompt 截断上限 16000 字，内容为组织架构与销售数据）自动重发到下一个候选配置。

### 5.2 对 B16-c 严重度的修正

团队负责人将 B16-c 定性为「自动跨服务商外发」并列为审计清单第一条。**这个定性以当前配置不成立，需要修正。**

实测 `config/ai_settings.json`：7 个配置，4 个 `is_active`。

| id | model | base_url | api_key 指纹 | is_default |
|---|---|---|---|---|
| 4 | MiniMax-M2.5 | `https://api.edgefn.net/v1` | 6fab8353 | false |
| 9 | GLM-5.1 | `https://api.edgefn.net/v1` | 6fab8353 | false |
| 10 | MiniMax-M2.5 | `https://api.edgefn.net/v1` | 6fab8353 | false |
| 11 | DeepSeek-V4-Pro | `https://api.edgefn.net/v1` | 94ad41d7 | **true** |

**去重后不同 base_url 只有一个：`https://api.edgefn.net/v1`。**

所以当前重试的实际行为是：同一服务商端点、换 model 参数、可能换 api_key（两个不同密钥指纹）。这是**跨模型、跨计费账号**，不是跨服务商。数据不会流向第二家厂商。

顺带精确解释了 trace 中的 `candidate_count: 3`：`_config_signature`（`backend/llm_client.py:87-93`）以 `(model, base_url, api_key)` 三元组去重，id=4 与 id=10 三元组完全相同被合并，故 4 个激活配置产生 3 个候选。数值完全吻合。

**修正后的定性**：B16-c 是一个真实存在的**潜在**数据外发通道——机制上代码会把完整 prompt 发往任何被配置的 `base_url`，且触发条件（限流、超时）是日常事件。但当前配置下所有候选同源，**尚未构成跨厂商外发**。风险在于：任何管理员在 AI 模型管理页新增一个不同厂商的激活配置，该通道即刻打开，且无任何提示或审批。

建议定级 P1（潜在外发通道 + 无管控），而非清单第一条。清单第一条应为 B-27（已实证的非确定性路由）或 B-23（已实证的部署缺表）。

### 5.3 事故不可追溯

`backend/llm_client.py:127-128` 的 trace 埋点记录 `model=self._llm_model` 与 `endpoint=self._llm_client.base_url`，**这两个字段读的也是共享态**。真发生 B16-a/b 类串用事故时，日志里记录的 model 与 endpoint 未必是实际发出去的那个。这条我认同团队负责人的判断，且它会让 B-1 的排查难度进一步上升。

---

## 6. baseline_review

| baseline 结论 | 出处 | 复核 | 依据 |
|---|---|---|---|
| R1 Flask dev server 单进程 | `docs/2026-08-06_调优体检报告.md` | 属实 | 未见 gunicorn / uvicorn 配置 |
| R2 前半 SSE 裸线程 + 无界队列 | 同上 | 属实 | `backend/controllers/smart_chat.py:705` 无 maxsize、`:769` 裸 Thread。补充：还缺总超时（`:773-778`） |
| R2 后半 `feishu_sync.py:214/267` 缺 daemon=True | 同上 | **错误** | `backend/controllers/feishu_sync.py:214-215` 与 `:267-268` 两处**都写了** `thread.daemon = True`。误报，修复清单应删除 |
| R3 `_pending_confirmations` 无锁 | 同上 | 属实 | 补全触点：`:55` `:7837` `:7839` `:7849` `:8878` `:9058`。严重度定 P1 而非 P0——它会显式抛 RuntimeError，不是静默算错；真正的 P0 是 B-1 那类静默算错 |
| H-3 / H-9 N+1 查询 | `deliverables/code-review-2026-07-31.md` | 属实 | 补精确定位：`backend/four_agent_ask.py:3953` 是整 catalog 循环；`backend/bookshelf_repository.py:131-246` 单次 7 条 SELECT，倍数是 7N 不是 N |
| H-7 / H-11 LLM 客户端重建 | 同上 | 属实且更严重 | 不只每次重建：`backend/llm_client.py:118-119` 在候选循环内重建，最坏一次 `_chat` 重建 3 个 client |
| H-8 golden 路径 sleep | 同上 | 属实 | `backend/four_agent_ask.py:8072-8074` 确认 |
| H-10 模型状态污染 | 同上 | 属实且定性需升级 | 不是「污染」而是**跨请求覆盖**。`:9063` 单例 + `:147-149` setter 写共享组件 + `:8487` 每请求写入 = 并发下必然互踩。应提到 P0 |
| H-15 缺 connect_timeout | 同上 | 属实 | `backend/datasource_router.py:156-162` `:166-173` 确认无；`backend/bookshelf_repository.py:41-58` 有 `connect_timeout=8`，两处不一致 |
| M-18 trace 静默吞异常 | 同上 | 属实且有新发现 | `backend/trace_logger.py:40-41` 确认。新增：`backend/four_agent_ask.py:61` 与 `:159` 两个写入器写同一文件，baseline 未提 |
| 「全仓搜不到 threading.Lock/RLock」 | 任务描述 | 不准确 | 仓库有 RLock：`backend/memory/short_term_memory.py:14`、`backend/smartask_report_history_store.py:23`。准确表述是「`_pending_confirmations` 这一处共享状态没有锁」 |
| 「158 处 print」 | 任务描述 | 偏低 | 实测 `backend/*.py` + `backend/controllers/*.py` 共 **182** 处 |
| 「14 处 f-string SQL」 | 任务描述 | 量级正确但风险需分层 | 实测约 35 处。多数为运维脚本表名插值（`backend/runtime_migration.py:189` `:718` `:845` `:917` `:980` `:1100` `:1204`、`backend/import_bookshelf_bundle.py`、`backend/export_bookshelf_bundle.py`），表名来自内部常量；`backend/system_log_store.py:301` `:340` `:539` 的 where 片段内部拼、值走 params 绑定。请求路径上的只有 `backend/four_agent_ask.py:5929` `:4681` `:4836` 与 `backend/ask_engine_sql.py:36-47`，关键变量来自内部枚举，当前不可注入。按「14 处高危注入」上报会失真 |
| 「配置重复读盘是性能问题」 | 多份 baseline 隐含 | 需降级 | 实测 2.38ms，占 LLM p50 的 0.03%。见 3.4 |
| 架构师：`repo._connect()` 外泄 20 处 | 架构审计 | 偏低 | 实测 **34 处（外部）/ 38 处（含 repo 自身 4 处）**。分布：`backend/controllers/bookshelf.py` 12、`backend/dataset_transform_service.py` 9（原报告遗漏，第二大户）、`backend/runtime_migration.py` 4、`backend/system_log_store.py` / `backend/regenerate_dataset_from_doc.py` / `backend/import_bookshelf_bundle.py` / `backend/import_angel_group_data.py` / `backend/export_bookshelf_bundle.py` / `backend/export_angel_group_data.py` / `backend/create_consumer_standard_dataset.py` / `backend/controllers/rbac.py` / `backend/controllers/data_permissions.py` 各 1 |
| 架构师：DDL 散落 bookshelf.py 15 处、system_log_store.py 7 处 | 架构审计 | 数字偏高 | 原报告用 `grep -c` 只数匹配行不数出现次数。精确计数（`grep -oE`）：`backend/controllers/bookshelf.py` 5、`backend/runtime_migration.py` 5、`backend/system_log_store.py` 5、`backend/import_bookshelf_bundle.py` 5、`backend/feishu_sync_service.py` 5、`backend/create_consumer_standard_dataset.py` 6、`backend/bookshelf_repository.py` 0。量级结论一致 |
| 架构师：dataset_node_index「6 处懒重载，miss 即重读 315KB」 | 架构审计 | **结论相反** | 那 6 处是死代码，永不重读。守卫为 `if not isinstance(node_index, dict)`，而 `backend/four_agent_ask.py:84-93` 失败时也返回 dict。真实问题是「永不失效」（B-26）。另实测 3.803ms，占比 0.05%，不应进性能议题 |
| 团队负责人：`agent1.org_subject` 三个调用点同在一次 `ask()` 内 | B-27 定位 | 需修正 | `:8493` 与 `:8656` 在 `ask()`（`:8472`）内；`:8981` 在 `confirm_by_boss()`（`:8848`）内，属独立入口的第二次 HTTP 请求。单次 `ask()` 内最多 2 次，不是 3 次 |
| 团队负责人：B16-c「自动跨服务商外发」 | B16 拆分 | 需修正 | 当前 4 个激活配置的 base_url 全部相同（`https://api.edgefn.net/v1`），是跨模型跨账号而非跨服务商。见 5.2 |

---

## 7. blind_spots

以下为本轮**未能验证**的部分，明确标注以免被当作已排查。

1. **Docker 不可用**。`docker ps` 返回空，无法容器内压测、无法测 TLS 握手成本、无法测建连开销、无法验证 B-16 的 DDL 锁等待。所有涉及实际耗时的推断均已标注。

2. **trace 样本稀疏且偏斜**。79 条记录仅 1 条完整 summary，且集中在 `agent1.org_subject`。Agent1.5 / Agent2 / Agent3 / Agent4 的真实耗时**无任何实测数据**，端到端 p50 为外推。建议在真实环境跑 20 次 LLM SQL 路径（非规则命中）的提问后重新统计。

3. **ChromaDB / Vanna 检索链路未审计**。`backend/vanna_core.py` 仅做了 print 计数（12 处），未读检索实现，无向量检索耗时埋点。若 Agent2 依赖向量召回，此处可能藏第二个瓶颈。

4. **并发缺陷未做实证复现**。B-1、B-7、B16-a、B16-b 均为代码结构推导，本次为只读审计未写测试。已移交 QA，建议用两个并发 SSE 请求指定不同模型验证 B-1，断言点为 trace 中同一 trace_id 下的 `model` 字段是否出现两个值（注意 B-14 的 trace_id 缺失会干扰归并）。

5. **认证鉴权与 RBAC 未纳入范围**。本轮只审实现质量与性能。越权访问、数据行级权限 `load_data_permissions` 的实际生效范围需单独一轮。

6. **`_execute_sql` 之后的行级安全未审**。trace 中可见 `pipeline.row_security_applied` 埋点，说明存在行级过滤，但未审其实现是否可绕过。与 B-2 / B-3 同属一条安全链，建议合并为专项。

7. **`agent1.org_subject` 那组 17 次调用（累计 137.4s）的归属未确认**。因 B-14 的 trace_id 缺失，无法确认是否属于同一次提问。若属同一次，则 B-27 的重复调用远不止 2 次，收益估算需上修。建议先修 B-14 再重新度量。

---

## 8. 修复顺序建议

按「阻塞性 + 实测收益 + 风险」排序，与架构师的「`_connect` 改 public 优先」存在一处分歧，理由随附。

| 序 | 动作 | 对应 ID | 成本 | 理由 |
|---|---|---|---|---|
| 1 | 三张表补进迁移文件 | B-23 | 低 | 唯一一条「不做就会在新环境炸」的。不改任何调用点，零风险 |
| 2 | 消除组织主体重复调用 | B-27 | 低 | 实测省 27.8% 端到端，且同时修非确定性路由。冗余性已由三条命题证明，零风险 |
| 3 | 只读护栏复检 + 下沉执行点 | B-2 / B-3 | 低 | 安全闸门，改动局部 |
| 4 | 删除请求路径内联 DDL | B-16 / B-24 | 中 | 依赖第 1 步完成 |
| 5 | 模型配置改按请求传参 | B-1 / B16-a / B16-b | 中 | 修沉默逻辑错误，需改调用约定 |
| 6 | 补 connect_timeout 与 statement_timeout | B-5 | 低 | 稳定性，非性能 |
| 7 | `_connect` 改 public | 架构师提出 | 低 | 34 处机械替换。它本身不修复任何缺陷，只是让后续治理成为可能，故排在实质修复之后 |
| 8 | 连接池 | B-17 | 中 | 依赖第 7 步。实测 DB 仅占 5.6%，收益上限有限 |
| 9 | 日志体系统一 | B-13 / B-14 / B-15 | 中 | 修 B-14 是重新度量 blind_spot 7 的前置 |
| 10 | 拆包 | B-21 | 高 | 需与架构师方案对齐；拆包时必须一并把请求级状态从实例属性剥离，否则拆完仍错 |
