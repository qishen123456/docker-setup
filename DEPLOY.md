# SmartAsk 智能问数系统 — 一键部署手册（Docker 版）

> 目标：让任何一台**全新 Windows 机器**，在满足以下三个前提下，**一条命令** 就能跑起来与作者本机完全一致的项目。

## ✅ 用户机前提

1. 已安装并启动 **Docker Desktop**（建议 4.30+，并启用 WSL2 后端）。
2. 已安装 **Git**（任何版本均可）。
3. 项目管理员已经把 **`.env` 文件**单独发给你（**不要从 Git 获取**）。

> 说明：`.env` 中含 `AI_API_KEY`、数据库密码、飞书 AppSecret 等敏感信息，按规范不进 Git 仓库。

---

## 🚀 一键部署（用户操作仅 3 步）

```powershell
# 1) 克隆代码（任选一条）
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask

# 2) 把项目管理员发的 .env 文件，放进项目根目录（与 deploy.bat 同级）

# 3) 双击运行 deploy.bat   或   在 PowerShell 中执行：
.\deploy.ps1
```

完成后浏览器访问：

- 前端：http://localhost:8080
- 后端健康检查：http://localhost:5002/api/health

> 端口可在 `.env` 中通过 `SMARTASK_FRONTEND_PORT` / `SMARTASK_BACKEND_PORT` / `SMARTASK_DOCKER_PG_PORT` 自定义。

---

## 🧠 部署流程做了什么（无需手动操作）

后端容器内置了 `bootstrap.py`，**容器每次启动都会自动**：

1. 等待 PostgreSQL 容器健康。
2. 应用 `backend/migrations/*.sql` 中的所有 schema 迁移（幂等）。
3. **首次启动**（`bs_datasets` 为空）时自动导入：
   - `backend/imports/bookshelf_bundle.json` —— 数据集元数据（LLD、字典、Schema、提示词、黄金 SQL 等）
   - `backend/imports/angel_group_data_bundle.json` —— 飞书同步过来的业务数据快照
4. 启动 Flask 主程序 `app.py`。

> 不会丢用户数据：再次执行 `deploy.ps1` 不会覆盖已有 `bs_datasets`。如确需重置元数据/业务数据，使用 `.\deploy.ps1 -ForceImport`。

---

## 🔄 后续更新

```powershell
.\update.ps1
```
等价于：`git pull` → `docker compose up -d --build` → 健康检查。

---

## 🛠️ 常用排错

| 现象 | 解决 |
| --- | --- |
| `docker info` 报错 | Docker Desktop 没启动，先打开它，鲸鱼图标变稳定再重试。|
| 端口冲突 | 修改 `.env` 中的端口变量后再 `.\deploy.ps1`。|
| 后端健康检查不过 | `docker compose logs --tail=200 backend` 看异常。|
| 想覆盖式重置元数据 | `.\deploy.ps1 -ForceImport`。|
| 想完全清空（含数据库） | `docker compose down -v`，再次 `.\deploy.ps1` 即从零初始化。|
| 飞书同步未启用 | `.env` 中把 `SMARTASK_FEISHU_IS_ACTIVE=true`，并填好 AppID/AppSecret 等。|

查看初始化进度：

```powershell
docker compose logs backend | Select-String "bootstrap"
```

---

## 📁 仓库布局对部署的关键文件

```
docker-compose.yml           # postgres + backend + frontend 服务编排
.env.example                 # 环境变量模板（真实值由 .env 提供，不进 Git）
deploy.ps1 / deploy.bat      # 一键部署入口
update.ps1 / update.bat      # 增量更新入口
backend/Dockerfile           # 后端镜像（CMD: python bootstrap.py）
backend/bootstrap.py         # 容器启动引导：迁移 + 首次数据导入
backend/migrations/*.sql     # PostgreSQL schema 迁移
backend/imports/*.json       # 元数据 / 业务数据快照（首次导入）
frontend/Dockerfile          # 前端镜像（npm build → nginx 静态托管）
frontend/nginx.conf          # /api 反代到 backend:5002
docker/postgres/init/*.sql   # postgres 容器**首次创建卷**时执行（兜底）
```

---

## ❓还原不出来？

请把以下三段日志发给项目管理员：

```powershell
docker compose ps
docker compose logs --tail=200 backend > backend.log
docker compose logs --tail=200 postgres > postgres.log
```

附上 `backend.log` / `postgres.log`，可以快速定位问题。
