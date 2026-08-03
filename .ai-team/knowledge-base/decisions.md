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
理由：四智能体流水线各 Agent 间有大量隐式状态传递，拆分成本高且容易引入 bug
被否方案：按 Agent 拆分为 4 个文件 -> Agent 间状态传递需要重新设计接口
影响范围：新增逻辑尽量外移到 ask_flow/ 或 ask_engine_*.py，不在 four_agent_ask.py 新增大类

[2026-08-03] 配置优先于硬编码（项目公约）
理由：数据集策略/功能开关/角色权限需要运维可调，硬编码进代码每次改动需重新部署
被否方案：写进代码常量 -> 改动需发版，运维无法自主调整
影响范围：config/ 下 16 json + 9 md，覆盖 datasetPolicies / feature_flag / advancedRoles
