# SmartAsk 项目 AI 协作指令

> 本文件被 GitHub Copilot for VSCode 自动读取（VSCode 1.194+）。
> 它是 AGENTS.md 的精简版，完整规范见仓库根目录 `AGENTS.md`。
> 完整专家团角色 prompt 见 `.ai-team/agents/`，机器可读配置见 `.ai-team/team-config.yaml`。

## 工作准则

1. **只读优先** - 理解项目后再动手，不确定时多读代码少改代码
2. **最小变更** - 存量项目只改必须改的，禁止顺手重写无关代码
3. **入乡随俗** - 新代码用项目既有的错误处理、日志、命名、配置读取方式
4. **上帝文件慎改** - `backend/four_agent_ask.py`（~10748行）改前先全局搜索定位
5. **配置优先于代码** - 能用 `config/` 配置解决的不硬编码

## 项目速写

SmartAsk = NL2SQL 问数系统。Flask 3.0.3 + Vanna + Vue 3.5 + Vite 8。

关键模块：
- `backend/app.py` - Flask 入口（端口 5002，18 blueprint）
- `backend/controllers/smart_chat.py` - 问数主路由（同步+SSE）
- `backend/ask_flow/controller.py` - basic/advanced 引擎开关
- `backend/four_agent_ask.py` - 四智能体流水线（~10748行上帝文件）
- `frontend/src/` - Vue3 + Element Plus + ECharts

## 需要专家团能力时

读取 `.ai-team/agents/<角色>.md` 作为参考。9 个角色可用：
PM、设计师、架构师、前端、后端、代码审查、QA、DevOps，由主理人（team-lead）编排。
完整 SOP 与路由表见 `.ai-team/team-config.yaml`。
