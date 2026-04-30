# SmartAsk 智能问数 — 项目迭代手册

> 本文档供开发者在迭代过程中参考，保证本地开发与 Docker 部署始终同步。

---

## 1. 项目结构概览

```
├── backend/              # Flask 后端（Python 3.11）
│   ├── app.py            # Flask 主入口 + 蓝图注册
│   ├── bootstrap.py      # Docker 容器启动入口（schema 迁移 → app.py）
│   ├── controllers/      # 蓝图模块（每个文件一个 Blueprint）
│   ├── config_manager.py # 读取 config/*.json + 环境变量覆盖
│   ├── four_agent_ask.py # 4-Agent 问数编排
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # Vue 3 + Vite 前端
│   ├── src/views/        # 页面视图
│   ├── src/state/        # 状态管理
│   ├── nginx.conf        # Docker 生产环境 nginx 配置
│   └── Dockerfile
├── config/               # 运行时配置（ai_settings.json 等）
├── docker/               # Docker 初始化脚本
│   └── postgres/init/    # PostgreSQL 首次启动 SQL
├── docker-compose.yml    # 编排：postgres + backend + frontend
├── deploy.ps1            # 一键部署脚本
├── .env                  # 环境变量（不入库）
└── .env.example          # 环境变量模板
```

## 2. 本地开发流程

### 2.1 环境准备

```bash
# 后端
cd backend
pip install -r requirements.txt
python app.py                    # 默认 http://localhost:5002

# 前端
cd frontend
npm install
npm run dev                      # 默认 http://localhost:5173，/api 代理到 5002
```

### 2.2 开发规范

| 规则 | 说明 |
|------|------|
| **蓝图注册** | 新增 controller 必须在 `app.py` 的 `register_blueprints()` 中注册，否则 Docker 部署后路由不可用 |
| **前端路由** | 新增页面必须在 `frontend/src/router/index.js` 中添加路由 |
| **配置读取** | 始终通过 `config_manager.py` 读取，不要硬编码路径 |
| **环境变量** | 新增环境变量同步更新 `.env.example` 和 `docker-compose.yml` |
| **数据库迁移** | 新建表/改表结构，在 `docker/postgres/init/` 添加编号 SQL 文件 |

### 2.3 本地验证清单

开发完成后执行以下检查，确保 Docker 部署不会出问题：

- [ ] `python app.py` 启动无报错
- [ ] 浏览器访问 `http://localhost:5002/api/health` 返回 200
- [ ] 前端所有页面可正常打开、API 调用无 404
- [ ] `requirements.txt` 包含所有新增依赖
- [ ] `package.json` 包含所有新增前端依赖

## 3. Docker 部署流程

### 3.1 首次部署

```powershell
# 1. 准备 .env
cp .env.example .env
# 编辑 .env 填入 AI 模型 API Key 等

# 2. 一键部署
.\deploy.bat
# 或
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

### 3.2 更新部署

```powershell
# 拉取最新代码后
.\deploy.bat           # 自动重新构建
# 或仅重启（不重新构建）
.\deploy.ps1 -NoBuild
```

### 3.3 常用命令

```powershell
docker compose logs -f backend    # 查看后端日志
docker compose logs -f frontend   # 查看前端日志
docker compose down               # 停止所有容器
docker compose down -v            # 停止并清除数据（慎用）
docker compose exec backend bash  # 进入后端容器
```

## 4. 迭代 Checklist

每次提交前对照此清单：

- [ ] 代码在本地运行无误（2.3 清单全部通过）
- [ ] `.gitignore` 中不应有运行时或敏感文件
- [ ] 没有引入无用的遗留文件（参考 .gitignore 中 Legacy 部分）
- [ ] commit message 格式：`[#AI] <描述>`（AI 生成）或标准格式（人工）
- [ ] Docker 构建测试：`docker compose build` 无报错

## 5. 端口约定

| 服务 | 本地开发 | Docker 默认 | 环境变量 |
|------|----------|-------------|----------|
| 前端 | 5173 (Vite) | 8080 | `SMARTASK_FRONTEND_PORT` |
| 后端 | 5002 | 5002 | `SMARTASK_BACKEND_PORT` |
| PostgreSQL | 5432 | 5433 (宿主) | `SMARTASK_DOCKER_PG_PORT` |

## 6. 已注册蓝图列表

| 蓝图 | 文件 | URL 前缀 |
|------|------|----------|
| dashboard | controllers/dashboard.py | /api/dashboard |
| datasources | controllers/datasources.py | /api/datasources |
| ai_models | controllers/ai_models.py | /api/ai-models |
| feishu_sync | controllers/feishu_sync.py | /api/feishu-sync |
| smart_chat | controllers/smart_chat.py | /api/smart-chat |
| bookshelf | controllers/bookshelf.py | /api/bookshelf |
| agents | controllers/agents.py | /api/agents |

## 7. 故障排查

| 问题 | 排查步骤 |
|------|----------|
| Docker 后端启动失败 | `docker compose logs backend` 查看日志，常见：依赖缺失、.env 配置错误 |
| 前端 API 404 | 确认 nginx.conf 的 proxy_pass 指向 `backend:5002`，确认蓝图已注册 |
| AI 模型 401 | 检查 `config/ai_settings.json` 中 API Key 是否正确，检查 .env 是否覆盖了默认模型 |
| 数据库连接失败 | Docker 中 DB_HOST 应为 `postgres`（服务名），本地应为 `localhost` |
| SSE 流断开 | 检查 nginx 是否有 buffering（当前配置无 buffering 设置，如需长连接加 `proxy_buffering off`） |
