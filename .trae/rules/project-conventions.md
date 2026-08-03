---
# Trae 项目规则 - 全局工作准则
# 生效方式：Always Apply（项目内所有 AI 对话自动加载）
alwaysApply: true
---

# SmartAsk 项目 AI 工作准则

> 本文件是 AGENTS.md 的 Trae 适配版，被 Trae 自动加载。
> 完整角色 prompt 与 SOP 配置见 `.ai-team/`。

## 核心准则

1. **只读优先** - 理解项目后再动手。不确定时多读代码，少改代码。
2. **最小变更** - 存量项目只改必须改的，禁止顺手重写无关代码。
3. **入乡随俗** - 新代码用项目既有的错误处理、日志格式、命名约定、配置读取方式。
4. **上帝文件慎改** - `backend/four_agent_ask.py` 已 1 万+行，改前先定位精确位置。
5. **配置优先于代码** - 能用 `config/` 下的配置解决的，不要硬编码。

## 项目速写

SmartAsk 是 NL2SQL 问数系统：Flask 3.0.3 + Vanna[chromadb] + Vue 3.5 + Vite 8。
- 后端入口 `backend/app.py`（端口 5002，18 blueprint）
- 问数主路由 `backend/controllers/smart_chat.py`（同步+SSE）
- 引擎开关 `backend/ask_flow/controller.py`（basic/advanced）
- 上帝文件 `backend/four_agent_ask.py`（~10748行，四智能体+规则SQL引擎）

## 需要专家团能力时

读取 `.ai-team/agents/<角色>.md` 作为参考。完整 SOP 与角色路由见 `.ai-team/team-config.yaml`。
