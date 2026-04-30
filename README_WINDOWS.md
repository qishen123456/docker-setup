# SmartAsk 智能问数 — Windows 本地开发手册

> **生产部署请用 Docker**，参考 [DEPLOY.md](DEPLOY.md)。本文档仅供本地开发调试。

---

## 环境要求

- **Python 3.11+**（推荐 Conda 或系统安装）
- **Node.js 20+**（npm 自带）
- **PostgreSQL 16+** 运行中（默认 localhost:5432）
- **Git**

---

## 快速启动

```powershell
# 后端
cd backend
pip install -r requirements.txt
python app.py
# → http://localhost:5002

# 前端（新终端）
cd frontend
npm install
npm run dev
# → http://localhost:5173（/api 代理到 5002）
```

或使用一键脚本：
- `start_all.bat` — 同时启动后端+前端
- `stop_all.bat` — 停止所有服务

---

## 初始化配置

首次启动后按以下顺序配置：

1. **AI 模型配置**：进入【AI模型配置】页面，添加 LLM API Key，点【测试】确认连通。
2. **数据源管理**：添加 PostgreSQL 数据库连接。
3. **智能问数**：输入自然语言问题，系统通过 4-Agent 流水线生成 SQL、执行并分析结果。

---

## 配置文件

所有运行时配置在 `config/` 目录下（后端自动生成）：

| 文件 | 内容 |
|------|------|
| `ai_settings.json` | AI 模型地址及 Key |
| `datasources.json` | 数据库连接（密码 Base64） |
| `app_config.json` | 系统运行参数 |
| `feishu_config.json` | 飞书同步配置 |

---

## 端口约定

| 服务 | 端口 |
|------|------|
| 后端 API | 5002 |
| 前端 Vite | 5173 |
| PostgreSQL | 5432 |

---

## 故障排除

| 问题 | 解决 |
|------|------|
| 后端启动失败 | 确认 PostgreSQL 运行中，`pip install -r requirements.txt` |
| 前端 API 404 | 确认后端在 5002 运行，检查 `vite.config.ts` 代理配置 |
| AI 模型 401 | 检查 `config/ai_settings.json` 的 API Key 是否有效 |
| 端口被占用 | `netstat -ano | findstr :5002` 找到并 kill 进程 |
