# 踩坑记录

> 非显然 bug + 根因 + 解法。修复后自动追加。
> 格式：[日期] 主题 / 上下文 / 根因 / 解法

[2026-08-03] SSE 多 worker 丢确认会话状态
上下文：controllers/smart_chat.py 的确认会话存进程内存，SSE 是单 worker 线程 + 内存 queue
根因：多 worker 部署时每个 worker 有独立内存空间，confirm-by-boss 分支的确认会话在 worker 间不共享
解法：确认会话外移到 Redis 或共享存储；或限制 SSE 路由单 worker（gunicorn -w 1 --worker-class gevent）
影响范围：controllers/smart_chat.py 的 confirm 会话管理、ask_flow/contracts.py 的 ConfirmRequest 处理

[2026-08-03] four_agent_ask.py 改动牵连面大
上下文：任何问数逻辑改动几乎都在 four_agent_ask.py（9063 行，旧文档称 ~10748 行已过时）
根因：四智能体流水线 + 三套硬编码规则 SQL 引擎全在一个文件里，函数间隐式耦合。但 AST 实测 58% 的方法（35个/5215行）零实例状态依赖，三套规则引擎 2112 行实例属性引用=0，拆分成本远低于直觉
解法：改动前先全局搜索目标函数/规则的位置，确认所有调用方；改后跑 pytest；不新增大类，尽量外移到 ask_flow/ 或 ask_engine_*.py。零状态纯函数可机械外提
影响范围：整个问数主链路

[2026-08-03] advanced 引擎通过率低导致默认关闭
上下文：ask_flow/controller.py 的 decide() 优先级判断，advanced 需 feature_flag + role 权限
根因：advanced 引擎商用通过率 18% / 消费者 7.5%，远低于 70% 目标，全量开启风险高
解法：默认 advanced 关闭，流量全走 basic 引擎；升级路线见 nl2sql_improvement_plan.md（五层改造）
影响范围：ask_flow/controller.py 的 decide() 默认走 basic

[2026-08-03] Vanna chromadb 版本敏感
上下文：Vanna[chromadb] 0.7.9 与 chromadb 版本强绑定
根因：chromadb 版本升级后向量存储 API 可能 breaking change，导致训练数据丢失
解法：锁定 vanna[chromadb]==0.7.9，升级前在隔离环境验证；训练数据定期导出备份
影响范围：backend/requirements.txt、Vanna 训练流程

[2026-08-06] agent1.org_subject 零缓存重复调用致非确定性路由（B-27）
上下文：_agent1_resolve_org_subject（four_agent_ask.py:7069-7159）零缓存，:7121 每次直接 _chat_json 打 LLM
根因：单次 ask() 内 :8493 与 :8656 两个调用点入参完全相同且 :8655 条件是 :8492 的严格子集，第二次纯冗余。temperature=0.1 非零致同输入不同输出（trace 实证："东部" vs ""），第二次返回空导致 :8662 分支跳过 → 同一用户问同一问题可能选不同数据集
解法：:8656 改为复用 :8491 的 org_subject_resolution 结果（三条命题已证明安全）；:8981 补 trace=trace；长期 temperature 改 0
影响范围：全部 LLM 耗时的 99.4% 集中在此 stage，删一处调用即可砍 27.8% 端到端

[2026-08-06] 否决态被伪造为成功态（SD-6）
上下文：four_agent_ask.py:8217-8223 无条件写 status="success"，写在 :8225 判断 approved 之前
根因：步骤态在判断 approved 之前就被写死，Agent3 返回 approved=False 时步骤条仍显示绿色成功。前端唯一读 approved 的地方（SmartAsk.vue:1672）只扣分且在 else 分支可能不执行
解法：status 按 approved 落（approved=False → status="rejected"）；approved=False 必须阻断执行走 review_rejected 降级分支
影响范围：所有 Agent3 判否的请求，用户拿到不可信数字做决策

[2026-08-06] 行级权限默认 fail-open（B3）
上下因：data_permission_store.py:475 无规则时 return sql 原样放行
根因：config/data_permissions.json 仅 3 条规则覆盖 2 个数据集，其余数据集零行级过滤
解法：改默认 deny——无规则时返回 1=0 或显式报错，public 数据集白名单化
影响范围：除数据集 2/3/62 外的全部数据集

[2026-08-06] 行级权限外层包裹对排名 SQL 无效（B4）
上下文：data_permission_store.py:514 把原 SQL 包进 SELECT * FROM (...) WHERE 权限条件
根因：排名 SQL（ask_engine_sql.py:36-47）在全域计算 ROW_NUMBER 后截取 TopN，再按权限过滤。排名序号本身跨域泄露；TopN 语义塌缩为"全公司前10 ∩ 可见范围"而非"可见范围内前10"
解法：权限谓词下推到最内层事实表扫描的 WHERE 内，使排名在授权子集上计算
影响范围：所有含排名/TopN/窗口函数的 SQL，行级权限对聚合查询也不成立

[2026-08-06] LLM 失败自动跨候选重发——潜在外发通道（L-04/B16-c）
上下文：llm_client.py:74-83 候选链无归属域过滤，:157-172 retryable 循环把同一份 prompt 发给下一个候选
根因：ask_engine_core.py:31-39 可重试集合含 RateLimitError/APITimeoutError（日常事件）和 AuthenticationError（配置问题）。当前 config/ai_settings.json 4 个激活配置 base_url 全部相同（同一家服务商），尚未跨厂商，但管理员新增不同厂商配置即打开通道
解法：候选链按归属域切分；AuthenticationError/PermissionDeniedError 移出重试集合直接失败+告警；retry 埋点补记实际外发 endpoint
影响范围：每次限流/超时/凭据失效都会重发 prompt（含组织架构与销售数据）

[2026-08-06] angel_group_data 表单点建表，重建环境即丢（L-01）
上下文：docker/postgres/init/002_angel_group_data.sql 是唯一建表途径，docker-entrypoint-initdb.d 仅首次执行
根因：bootstrap.py:45-57 MIGRATIONS 无对应项，已有数据卷环境升级不会建此表
解法：DDL 补进 backend/migrations/ 并登记到 bootstrap MIGRATIONS
影响范围：非全新数据卷环境必然缺表

[2026-08-06] 三张生产表不在任何迁移文件中（L-02/B-23）
上下文：bs_common_questions / bs_dataset_external_configs / bs_regression_cases 唯一定义在 controllers/bookshelf.py:526-570 内联 DDL
根因：5 份 _ensure_optional_tables 副本 md5 全不同已分叉，走业务流量的那份恰好缺 bs_dataset_report_config
解法：三张表 DDL 收敛到 backend/migrations/，5 份 _ensure_optional_tables 全部删除
影响范围：干净环境部署后缺表，健康检查给假阳性

[2026-08-06] 安全护栏方向反置（A-01）
上下文：four_agent_ask.py:8225-8263，approved=True 直落执行无校验，approved=False 才过 _is_read_only_sql
根因：护栏按策略分支逐个补，不在唯一出口设闸。datasource_router.py:192-199 物理执行点零护栏
解法：在 datasource_router.execute_sql_for_source 设唯一强制闸口（语句校验+表白名单+行级权限+LIMIT+statement_timeout+审计日志），上层全部分支式校验删除
影响范围：LLM 改写的 SQL 直达数据库，纵深防御为零

[2026-08-06] 语义画像层静默空转（A-02）
上下文：backend/data/dataset_dimension_profiles.json 不存在，dataset_dimension_profiles.py:30-32 缺失时静默 return {}
根因：31 个调用点（four_agent_ask.py 23 处 + disambiguation/llm_arbiter.py 4 处）全部拿到 None，路由层级判定和实体消解全部退化，无任何日志告警
解法：产出 dataset_dimension_profiles.json 激活 31 个已写好的调用点。注意：补的文件只含同义词映射和集合口径增强，不含节点层级关系定义（节点关系以 dataset_node_index.json 为唯一事实源）
影响范围：全项目投入产出比最高的单点动作——补一个文件激活 294 行已实现的语义匹配代码

[2026-08-17] 测试工具自身三坑：文档造假 / 哑 FAIL / 结构性恒 FAIL
上下文：smartask-qa-regression 技能首版，SKILL.md 宣称"preflight 四道闸"实际只实现两道；B5 用例 `row_count gte 0` 被判"恒真"实为"哑 FAIL"；B14 对弹确认问题直接断言 query_intent
根因：① 文档先行实现未跟上，契约偏离无人核对；② `_matches` 对 None 返回 False，异常被 ask() 吞成 {"error":...} 而 runner 不检查 error 键，失败只剩一片 None FAIL 无根因文本；③ 弹确认时 ask() 提前返回、结果无 dataset_results 键，直查断言必然全 FAIL，且与同问题的 confirm 用例自相矛盾（套件永远不可能全绿）
解法：runner 加 error 字段特判（记 EXC 带错误文本并跳过该 turn 其余断言）；弹确认用例一律走 confirm 走完格式；SKILL.md 与实现逐条对齐纳入复审清单；"看起来恒真"的断言要区分"成功时恒过"与"失败时哑 FAIL"两种形态
影响范围：.agents/skills/smartask-qa-regression/，后续所有测试工具/技能的文档-实现对账

[2026-08-17] 容器内回归必须先对齐代码漂移再判 FAIL
上下文：QA 首轮 baseline 28 个 FAIL 聚集为消费者 ranking 意图全线 unknown，险些全判成源码缺陷
根因：宿主机 5 个意图识别修复 commit（8ace601~1de4311，6 文件）未同步进容器，容器跑的是 08-13 旧代码；runner 是容器内即时 import，测的其实是旧码
解法：报告头打印关键文件 md5+mtime（four_agent_ask.py md5 99dd vs 宿主机 6da5 当场现形）；漂移 FAIL 先 docker cp 对齐再重跑复核，复核不过的才路由 Engineer-BE
影响范围：qa_runner.py 报告头、所有容器内测试流程的 FAIL 判读顺序

[2026-08-17] bug#3 根节点整体 overview 丢业务部层级行
上下文：「商用事业部的整体业绩」基线 7-8 行（事业部+分公司+业务部三层），08-15 意图修复链后回退到 4 行；QA 回归 A1 用例当场抓到（旧码 8 行 vs 新码 4 行）
根因：`_build_rule_based_sql` ranking 兜底分支里，根节点名（"商用事业部"）被当中间层级过滤词处理，WHERE 层级='商用事业部' 匹配不到任何行，只剩兜底行。另有半成品修复误删 `verified_level` 赋值行导致 NameError 隐患
解法：`_is_root_overview` 判定（target_level 命中 analysisDimensions 根节点名 + level_overview 触发词或"整体/总体/总览/汇总/全部"词）→ WHERE 层级 IN ('事业部','分公司','业务部') 三层返回；verified_level 赋值行原样补回。硬编码三层仅作用于商用 phase1 分支（消费者/电商已提前 return），误判面收敛在"根节点名+整体类词"窄交集
影响范围：four_agent_ask.py:5142-5162；验收用例 qa_cases/baseline.json A1（已实测 PASS，row_count=8）
