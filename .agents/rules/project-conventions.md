# SmartAsk 项目 AI 工作准则

> 本文件是 AGENTS.md 的跨 IDE 适配版，`.trae/rules/project-conventions.md` 由本文件同步生成。
> 完整角色 prompt 与 SOP 配置见 `.ai-team/`。

## 核心准则

1. **只读优先** - 理解项目后再动手。不确定时多读代码，少改代码。
2. **最小变更** - 存量项目只改必须改的，禁止顺手重写无关代码。
3. **入乡随俗** - 新代码用项目既有的错误处理、日志格式、命名约定、配置读取方式。
4. **上帝文件慎改** - `backend/four_agent_ask.py` 已 9000+ 行，改前先定位精确位置。
5. **配置优先于代码** - 能用 `config/` 下的配置解决的，不要硬编码。

## 项目速写

SmartAsk 是 NL2SQL 问数系统：Flask 3.0.3 + Vanna[chromadb] + Vue 3.5 + Vite 8。
- 后端入口 `backend/app.py`（端口 5002，18 blueprint）
- 问数主路由 `backend/controllers/smart_chat.py`（同步+SSE）
- 引擎开关 `backend/ask_flow/controller.py`（basic/advanced）
- 上帝文件 `backend/four_agent_ask.py`（9063行，四智能体+规则SQL引擎）

## 任务分流

- 开发代码任务 → 读取 `.ai-team/agents/` 下对应角色的 prompt 文件作为行为规范
- 数据分析任务 → 读取 `.ai-data/agents/` 下对应角色的 prompt 文件
- 完整 SOP 与角色路由见 `.ai-team/team-config.yaml`

无多智能体调度机制的 IDE：所有多角色流程按各 team-lead.md 末尾"跨 IDE 降级模式"串行执行：依次扮演每个角色完成其 Phase 产出，按 L1/L2/L3 规则传递上下文，禁止假装并行、禁止跳过 Phase、禁止主理人代写成员产出。
