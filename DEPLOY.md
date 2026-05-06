# SmartAsk 智能问数系统 — 一键部署手册（Docker 版）

> 目标：让任何一台**全新 Windows 机器**，在满足以下三个前提下，**一条命令** 就能跑起来与作者本机完全一致的项目。  
> **状态**: ✅ 100% 可复刻 (v2.4, 2026-05-01 验证目标，含 ReportSpec v2、路由可信度、低相似确认、一键容器测试)

## ✅ 用户机前提

1. 已安装并启动 **Docker Desktop**（建议 4.30+，并启用 WSL2 后端）。
2. 已安装 **Git**（任何版本均可）。
3. 准备好配置来源：要么使用仓库里的 `.env.example` 复制出 `.env` 并手工填写，要么由项目管理员直接提供可用的 `.env`。

> 说明：`.env` 中含 `AI_API_KEY`、数据库密码、飞书 AppSecret 等敏感信息，按规范不进 Git 仓库。

---

## 🚀 一键部署（用户操作仅 3 步）

```powershell
# 1) 克隆代码
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask

# 2) 复制模板并填写真实密钥
Copy-Item .env.example .env
# 然后编辑 .env，至少填这些：
# - SMARTASK_SECRET_KEY
# - SMARTASK_AI_API_KEY
# - SMARTASK_AI_MODEL
# - SMARTASK_AI_BASE_URL
# - 如启用飞书，同步填写 SMARTASK_FEISHU_* 相关配置

# 3) 一键部署并附带集成测试
.\deploy.ps1 -RunTests
```

`deploy.ps1` 会检查 `.env` 是否仍在使用模板占位值。如果 `SMARTASK_SECRET_KEY` 或 `SMARTASK_AI_API_KEY` 未填写真实值，脚本会停止并提示先补配置，避免用户机启动出一个“看似成功但不能问数”的环境。

如果项目管理员已经单独发给你可用的 `.env`，也可以直接放到项目根目录后执行：

```powershell
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
.\deploy.ps1 -RunTests
```

完成后浏览器访问：

- 前端：http://localhost:8080
- 后端健康检查：http://localhost:5002/api/health

> 端口可在 `.env` 中通过 `SMARTASK_FRONTEND_PORT` / `SMARTASK_BACKEND_PORT` / `SMARTASK_DOCKER_PG_PORT` 自定义。

---

## 🧠 部署流程做了什么（无需手动操作）

后端容器内置了 `bootstrap.py`，**容器每次启动都会自动**：

1. 等待 PostgreSQL 容器健康。
2. 初始化 `config/` 下默认 JSON 配置，并在存在 `runtime_config_bundle.json` 时按幂等策略回写运行时配置。
3. 应用 `backend/bootstrap.py` 迁移清单中的 schema 迁移（幂等），当前包括：
   - `20260330_bookshelf_schema.sql`
   - `20260330_bookshelf_agent1_prompt_upgrade.sql`
   - `20260430_report_config.sql`
4. **首次启动**（`bs_datasets` 为空）时自动导入：
   - `backend/imports/bookshelf_bundle.json` —— 数据集元数据（LLD、字典、Schema、提示词、黄金 SQL 等）
   - `backend/imports/runtime_config_bundle.json` —— 数据源、AI、飞书、应用配置、查询历史
   - `backend/imports/angel_group_data_bundle.json` —— 飞书同步过来的业务数据快照
5. 启动 Flask 主程序 `app.py`。

> 不会丢用户数据：再次执行 `deploy.ps1` 不会覆盖已有 `bs_datasets`，也不会默认覆盖 `config/*.json`。如确需重置元数据/业务数据，使用 `.\deploy.ps1 -ForceImport`；如需覆盖配置，使用 `.\deploy.ps1 -ForceConfig`。

---

## 🔄 后续更新

```powershell
.\update.ps1
.\update.ps1 -RunTests
.\update.ps1 -RunTests -RunStreamTests
.\update.ps1 -NoBuild
.\update.ps1 -NoPull -RunTests
```

默认等价于：更新前备份 → `git pull --ff-only` → `docker compose config` → `docker compose up -d --build` → 健康检查。加 `-RunTests` 会在 backend 容器内运行 `scripts/integration_test.py`，即使用户机没有安装 Python 也可以测试。

说明：

- `-RunStreamTests` 会额外测试 AI 流式问数链路，依赖真实模型 Key 和网络。
- `-NoPull` 适合离线更新包场景，不从 Gitee 拉代码。
- `-NoBuild` 只重启已有镜像，不重新构建。
- 更新脚本默认会先调用 `backup.ps1` 备份，保护用户机已有数据。

---

## 🧰 运维脚本

### 备份

```powershell
.\backup.ps1
```

备份内容通常包括：

- `config/`
- `.env.example`
- `bundles/`
- `postgres.sql`

备份输出到 `backups/时间戳/`，该目录已加入 `.gitignore`。

### 诊断

```powershell
.\doctor.ps1
```

生成诊断包：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

诊断包包含 Docker 状态、服务日志、端口占用、健康检查和脱敏 `.env` 摘要。遇到用户机问题时，优先让用户执行这个脚本并把 zip 发回。

### 重启/重建/清空

```powershell
.\reset.ps1 -Mode Restart
.\reset.ps1 -Mode Rebuild
.\reset.ps1 -Mode Data -ConfirmDataReset
```

含义：

- `Restart`：软重启容器，不重建镜像，不删除数据。
- `Rebuild`：重新构建并启动容器，不删除数据卷。
- `Data`：清空数据库和向量数据卷，从零初始化；必须显式加 `-ConfirmDataReset`，避免误删。

---

## 🛠️ 常用排错

| 现象 | 解决 |
| --- | --- |
| `docker info` 报错 | Docker Desktop 没启动，先打开它，鲸鱼图标变稳定再重试。|
| `docker ps` 连不上 daemon | Docker Desktop 可能未完全启动，先确认 `docker info` 成功，再重跑 `.\deploy.ps1 -RunTests`。 |
| 端口冲突 | 修改 `.env` 中的端口变量后再 `.\deploy.ps1`。|
| 后端健康检查不过 | `docker compose logs --tail=200 backend` 看异常。|
| `SMARTASK_AI_API_KEY` 占位值 | 编辑 `.env`，填入真实模型 Key 后重跑 `.\deploy.ps1 -RunTests`。|
| 想覆盖式重置元数据 | `.\deploy.ps1 -ForceImport`。|
| 想覆盖式重写配置文件 | `.\deploy.ps1 -ForceConfig`。|
| 想完全清空（含数据库） | `.\reset.ps1 -Mode Data -ConfirmDataReset`。|
| 不知道怎么排查 | `.\doctor.ps1`，把生成的 zip 发给项目管理员。|
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
backup.ps1                   # 用户机备份入口
doctor.ps1                   # 用户机诊断包入口
reset.ps1                    # 重启/重建/清空数据入口
backend/Dockerfile           # 后端镜像（CMD: python bootstrap.py，同时复制 scripts/ 供容器内测试）
backend/bootstrap.py         # 容器启动引导：迁移 + 首次数据导入
backend/export_runtime_config.py   # 导出 config/*.json 为 runtime bundle
backend/import_runtime_config.py   # 幂等导入 runtime bundle
backend/migrations/*.sql     # PostgreSQL schema 迁移
backend/imports/*.json       # 元数据 / 业务数据快照（首次导入）
scripts/integration_test.py  # 部署后真实接口集成测试（deploy/update 可在容器内执行）
scripts/backup_all.py        # 一键导出三类 bundle
frontend/Dockerfile          # 前端镜像（npm build → nginx 静态托管）
frontend/nginx.conf          # /api 反代到 backend:5002
docker/postgres/init/*.sql   # postgres 容器**首次创建卷**时执行（兜底）
```

---

## ❓还原不出来？

优先执行：

```powershell
.\doctor.ps1
```

把 `diagnostics\smartask_diagnose_时间戳.zip` 发给项目管理员。

如果诊断脚本也无法运行，再手工执行：

```powershell
docker compose ps
docker compose logs --tail=200 backend > backend.log
docker compose logs --tail=200 postgres > postgres.log
```

---

## 📋 100% 复刻验证清单 (2026-05-01)

| 验证项 | 结果 |
|--------|------|
| PostgreSQL 连接 | ✅ PASS |
| bs_datasets 表有数据 (1条) | ✅ PASS |
| bs_agent_prompt_fragments (4条 Agent 提示词) | ✅ PASS |
| bs_golden_sql_samples (1条) | ✅ PASS |
| angel_group_data (115行业务数据) | ✅ PASS |
| /api/health HTTP 200 | ✅ PASS |
| /api/datasources HTTP 200 | ✅ PASS |
| /api/ai-models HTTP 200 | ✅ PASS |
| AI 模型 CRUD (Create/Update/Delete/Set-default) | ✅ PASS |
| 4-Agent 流水线 (Agent1→确认→Agent2→Agent3→Agent4) | ✅ PASS |
| ReportSpec v2 动态报告配置表 | ✅ PASS |
| 低相似命中需用户确认 | ✅ PASS |
| 路由把握/结果可信说明展示 | ✅ PASS |
| runtime_config_bundle.json 已生成 | ✅ PASS |
| bookshelf_bundle.json 已生成 | ✅ PASS |
| angel_group_data_bundle.json 已生成 | ✅ PASS |

### 包含的数据包 (`backend/imports/`)

| 文件 | 说明 | 大小 |
|------|------|------|
| `bookshelf_bundle.json` | 数据集元数据（LLD、字典、Schema、提示词、黄金SQL） | ~50KB |
| `runtime_config_bundle.json` | 运行时配置（datasources + ai + feishu + app + history） | ~10KB |
| `angel_group_data_bundle.json` | 飞书同步的 115 行业务数据快照 | ~200KB |
