# 踩坑记录

> 非显然 bug + 根因 + 解法。修复后自动追加。
> 格式：[日期] 主题 / 上下文 / 根因 / 解法

[2026-08-03] SSE 多 worker 丢确认会话状态
上下文：controllers/smart_chat.py 的确认会话存进程内存，SSE 是单 worker 线程 + 内存 queue
根因：多 worker 部署时每个 worker 有独立内存空间，confirm-by-boss 分支的确认会话在 worker 间不共享
解法：确认会话外移到 Redis 或共享存储；或限制 SSE 路由单 worker（gunicorn -w 1 --worker-class gevent）
影响范围：controllers/smart_chat.py 的 confirm 会话管理、ask_flow/contracts.py 的 ConfirmRequest 处理

[2026-08-03] four_agent_ask.py 改动牵连面大
上下文：任何问数逻辑改动几乎都在 four_agent_ask.py（~10748 行上帝文件）
根因：四智能体流水线 + 三套硬编码规则 SQL 引擎全在一个文件里，函数间隐式耦合
解法：改动前先全局搜索目标函数/规则的位置，确认所有调用方；改后跑 pytest；不新增大类，尽量外移到 ask_flow/ 或 ask_engine_*.py
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
