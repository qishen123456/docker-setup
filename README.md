# SmartAsk 智能问数系统

> Flask + Vue 3 + PostgreSQL + Vanna(Chroma) + 通义千问/DeepSeek 等多模型，按 **数据集隔离 + 4-Agent 协作** 范式生成可执行 SQL。

## 一键部署（推荐：Docker 全家桶）

完整步骤见 [DEPLOY.md](DEPLOY.md)。最简版：

```powershell
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
# 把项目管理员发的 .env 放到项目根目录
.\deploy.ps1
```

打开浏览器访问 http://localhost:8080 即可。

后端容器启动时会**自动**完成：
- PostgreSQL 健康等待
- schema 迁移（`backend/migrations/*.sql`）
- 首次启动自动导入 `backend/imports/bookshelf_bundle.json` 与 `angel_group_data_bundle.json`

---

## 主要目录

| 目录/文件 | 说明 |
| --- | --- |
| `backend/` | Flask 主服务、4-Agent 协作流水线、配置/数据源/AI/飞书同步管理 |
| `backend/bootstrap.py` | 容器启动引导：等 DB → 迁移 → 首次导入 → 启动 Flask |
| `backend/migrations/` | PostgreSQL DDL/升级脚本 |
| `backend/imports/` | 元数据 + 业务数据 bundle（首次导入用） |
| `frontend/` | Vue 3 + Element Plus 前端，nginx 容器静态托管，`/api` 反代到后端 |
| `docker-compose.yml` | postgres + backend + frontend 三服务编排 |
| `deploy.ps1` / `update.ps1` | 一键部署 / 一键更新（PowerShell） |
| `deploy.bat` / `update.bat` | 等价的 Windows 双击启动入口 |
| `.env.example` | 环境变量模板（真实 `.env` 由管理员单独下发） |

---

## 文档索引

- 🚀 **[DEPLOY.md](DEPLOY.md)** — 给业务用户/同事的部署手册（你现在最需要的那份）
- 📚 [README_WINDOWS.md](README_WINDOWS.md) — 本地非 Docker 开发模式（仅老开发参考）
- 📑 [GIT_GUIDE.md](GIT_GUIDE.md) — Git 工作流速查
- 📋 [task.md](task.md) / [implementation_plan.md](implementation_plan.md) — 历史规划

---

## 常见命令速查

```powershell
.\deploy.ps1                         # 全量部署（构建 + 起容器 + 自动初始化）
.\deploy.ps1 -ForceImport            # 强制重新导入元数据/业务数据
.\update.ps1                         # git pull + 重新构建 + 起容器
docker compose logs -f backend       # 看后端实时日志
docker compose logs backend | Select-String bootstrap  # 看初始化引导日志
docker compose down                  # 停容器（保留数据卷）
docker compose down -v               # 停容器并清空数据卷（彻底重来）
```

---

## 安全规范

- `.env`、`config/*.local.json`、`*.db`、`chroma_db/` 等敏感文件**不进 Git**。
- 数据库密码、API Key 经 Base64 混淆存储于 `config/*.json`，加上 `.env` 双层防护。
- 任何由 AI agent 创建的提交，commit subject 必须以 `[#AI] ` 开头（已在 `.gitignore` 同级文档约定）。
