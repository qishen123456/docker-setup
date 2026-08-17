# 设计决策记录

> 有取舍的技术决策 + 理由 + 被否方案。
> 格式：[日期] 决策 / 理由 / 被否方案 / 影响范围

[2026-08-03] advanced 引擎默认关闭
理由：通过率商用 18% / 消费者 7.5%，未达 70% 目标，全量开启风险高
被否方案：全量开启 advanced + fallback -> 可能大面积问不出，用户体验差
影响范围：ask_flow/controller.py 的 decide() 默认走 basic

[2026-08-03] SSE 用单 worker 线程 + 内存 queue 而非异步任务队列
理由：MVP 阶段快速验证，SSE 本质同步，引入 Celery/RabbitMQ 增加运维复杂度
被否方案：Celery + Redis -> 需要 worker 进程和 broker，MVP 阶段过重
影响范围：controllers/smart_chat.py 的 SSE 实现；多 worker 部署时需限制 -w 1 或外移确认会话

[2026-08-03] 问数主逻辑集中在 four_agent_ask.py 而非拆分
状态：**已推翻（2026-08-06 审计）**
理由（原）：四智能体流水线各 Agent 间有大量隐式状态传递，拆分成本高且容易引入 bug
推翻依据：AST 实测 9063 行中 9009 行属于单个 class，但 58% 的方法（35个/5215行）零实例状态依赖。三套规则 SQL 引擎合计 2112 行实例属性引用=0——是被误写成方法的纯函数，外提是机械操作。__init__ 仅 11 个实例属性，最高引用热度 13 个方法。拆分成本远低于"上帝文件"直觉判断
被否方案：按 Agent 拆分为 4 个文件 -> Agent 间状态传递需要重新设计接口
新方案：按零状态纯函数优先外提（5215 行机械操作），有状态的少数方法（11 个属性周边）做真正的架构解耦。详见 docs/audit/2026-08-06_architecture-audit.md §4
影响范围：新增逻辑尽量外移到 ask_flow/ 或 ask_engine_*.py，不在 four_agent_ask.py 新增大类

[2026-08-03] 配置优先于硬编码（项目公约）
理由：数据集策略/功能开关/角色权限需要运维可调，硬编码进代码每次改动需重新部署
被否方案：写进代码常量 -> 改动需发版，运维无法自主调整
影响范围：config/ 下 16 json + 9 md，覆盖 datasetPolicies / feature_flag / advancedRoles

[2026-08-06] 安全护栏应在 datasource_router.execute_sql_for_source 设唯一闸口
理由：当前护栏按策略分支逐个补，导致"可信路径校验严、不可信路径校验松、执行点零护栏"的倒挂。approved=True 的 LLM 改写 SQL 直达数据库，approved=False 的反而过安检
被否方案：在每条改写路径后补一次校验 -> 每加一条改写路径就要记得补，不可持续
影响范围：datasource_router.py:192-199 物理执行点；four_agent_ask.py:7407/7425/7441/8238/8296 上层分支式校验全部删除

[2026-08-06] Agent3 LLM 复核应删除，降级为确定性校验器
理由：Agent3 否决不阻断执行（:8225-8249），在可信路径上不工作（:7424-7487 passthrough），在唯一真正运行的 normal 路径上反而放大风险（:7676-7683 LLM 改写的 SQL 无校验直达执行）。花约 7s 买了个装饰品
被否方案：保留 Agent3 但增强其阻断能力 -> 当前就是不阻断，"增强"是不确定的承诺
影响范围：_agent3_review 保留字段校验部分，删除 LLM 调用；省一次 LLM 往返约 7s（占端到端约 46%）

[2026-08-06] LLM 候选链跨域过滤——当前配置同源不跨厂商
理由：config/ai_settings.json 4 个激活配置 base_url 全部相同（https://api.edgefn.net/v1），当前是跨模型跨计费账号，不是跨服务商。但机制上无防护，新增不同厂商配置即打开外发通道
被否方案：不做任何过滤 -> 管理员新增配置即无感打开数据外发通道
影响范围：llm_client.py:74-83 候选链构造 + ask_engine_core.py:31-39 重试集合

[2026-08-06] 迁移体系单一化——backend/migrations/ 为唯一真相源
理由：两套迁移体系已分叉（docker init 6 个 vs migrations 7 个，各有独有内容），5 份 _ensure_optional_tables 副本 md5 全不同已分叉，表结构取决于环境历史上先跑过哪个脚本
被否方案：保留两套并行 -> CREATE TABLE IF NOT EXISTS 让先跑者定义结构，后者静默跳过，不可预测
影响范围：docker/postgres/init/ 只保留数据库/用户初始化；bootstrap 迁移失败必须阻断启动

[2026-08-17] preflight 环境自检做"报告项"而非"阻断闸"（md5 第三解）
理由：宿主机侧脚本（docker inspect + md5sum 比对 + 进程 mtime）在 Windows + Docker Desktop + Git Bash 下跨平台维护贵；纯文档降级又等于放弃。容器内自给自足打印关键文件 md5+mtime 到报告头 + SKILL.md 配一行宿主机 md5sum 供肉眼比对，首次实战即立功（当场抓住容器代码漂移）
被否方案：A 宿主机四道闸脚本（维护贵）；B 文档降级为两道闸（放弃防护）
影响范围：qa_runner.py print_drift_header、SKILL.md 报告头 md5 自检小节

[2026-08-17] 行数断言 eq vs range 按"语义是否负载"切分，不全量改
理由：`eq 69`（B15/R1/O1）是截断检测器——抓"无数量排名被 LIMIT 20 截断"回归，放松成 range 会降低敏感度；`eq 3/13/4`（D5/B2/R2-confirm）是层级节点数，飞书同步一抖就误报，改 range。切分标准是"这个数值是不是该用例要抓的回归信号本身"
被否方案：全量改 range ±15%（截断检测器失灵）；全量保 eq（数据漂移误报）
影响范围：cases/*.json 行数断言规范

[2026-08-17] 多数据集结果断言按 dataset_id 匹配，不按数组索引
理由：对比场景 dataset_results 顺序不保证固定（可能按 dataset_id 排序或路由顺序），`dataset_results.1` 会看岔；元素自带 dataset_id 字段（four_agent_ask.py:1220），选择器 `dataset_results[ds=62]` 稳定
被否方案：按索引取第二个（顺序敏感）
影响范围：qa_runner.py get_path 选择器语法、B5 等跨数据集用例
