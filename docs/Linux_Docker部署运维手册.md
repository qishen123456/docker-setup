# Linux Docker 部署运维手册

更新时间：2026-05-11

当前项目真实 Git 信息：

```text
Gitee remote：https://gitee.com/tailin1/volcano-intelligent-questions.git
当前可拉取发布分支：docker-setup
```

注意：Linux/Git 对分支名大小写敏感。已核验当前本地与 Gitee 远端存在的分支是 `docker-setup`；如果后续你在 Gitee 另建大写 `DOCKER-SETUP` 分支，命令里的 `docker-setup` 才需要替换成 `DOCKER-SETUP`。

本文档只解决一件事：Linux 服务器如何部署、启动、更新、备份、回滚和检查 SmartAsk。

本版部署重点：

- 问数语义识别增强：用户说“东西部分公司”等合称时，后端会先通过 Agent1.5 和数据集画像解析为具体组织成员，再进入 SQL 与报告链路。
- 报告场景与模板契约治理：后端新增统一场景识别与报告契约健康检查，部署自检会验证“对比分析”场景和模板契约模块是否随镜像生效。
- 报告模板配置自修复：后端启动时会幂等应用 `backend/migrations`；首次空库导入书架数据后，会补跑报告配置迁移，避免报告模板配置为空。
- 报告风险线更新：商用事业部相关数据集统一使用 10% 风险线、15% 机构标杆线、20% 个人标杆线。

Windows 用户机一键部署请看：

```text
docs/SmartAsk_部署与交付手册.md
```

Windows 测试环境发布到 Linux 正式环境，并保护生产运行态配置，请看：

```text
docs/迁移发布与运行态配置保护方案.md
docs/运行态配置导出导入操作手册.md
```

## 1. 服务器要求

Linux 服务器需要安装：

- Git
- Docker Engine
- Docker Compose Plugin

检查命令：

```bash
git --version
docker --version
docker compose version
docker info
```

如果 `docker info` 报错，通常说明 Docker 没启动。

启动 Docker：

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

## 2. 拉取项目

如果 Gitee 默认分支不是完整代码，直接 `git clone` 可能只看到 README。建议先确认分支：

```bash
git ls-remote --heads https://gitee.com/tailin1/volcano-intelligent-questions.git
```

完整项目当前应从 `docker-setup` 分支拉取：

```bash
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
```

不要只执行裸 `git clone`，否则可能拉到默认分支，只看到 README。如果已经拉错分支，可执行：

```bash
cd smartask
git fetch --all
git branch -a
git checkout docker-setup
```

## 3. 首次部署

### 3.1 准备 `.env`

```bash
cp .env.example .env
nano .env
```

至少修改：

```text
SMARTASK_SECRET_KEY
SMARTASK_AI_API_KEY
SMARTASK_AI_MODEL
SMARTASK_AI_BASE_URL
SMARTASK_ADMIN_USERNAME
SMARTASK_ADMIN_PASSWORD
SMARTASK_ADMIN_DISPLAY_NAME
```

生产环境不要使用示例密码。

Docker Compose 自带 PostgreSQL 时，保持下面口径即可：

```text
SMARTASK_DB_HOST=postgres
SMARTASK_DB_PORT=5432
SMARTASK_DOCKER_PG_PORT=5433
```

说明：`SMARTASK_DB_HOST` / `SMARTASK_DB_PORT` 是容器内后端访问 PostgreSQL 的地址；`SMARTASK_DOCKER_PG_PORT` 才是宿主机对外映射端口。不要把 Docker 内部数据库地址写成 `localhost:5433`，否则容器内会连到自己而不是 PostgreSQL 容器。

Linux 脚本会兼容 Windows 复制过来的 `.env` 换行、引号和空格；但 `.env` 仍建议使用纯文本保存，不要带富文本格式。

APT 说明：`deploy.sh` 默认不会改写宿主机 `/etc/apt` 源，避免影响公司服务器原有软件源。`SMARTASK_APT_MIRROR` 只用于 Docker build 阶段改写 Python 基础镜像内的 Debian 源。只有明确要改宿主机 APT 源时，才在 `.env` 或命令前设置：

```bash
SMARTASK_CONFIGURE_APT_MIRROR=1 bash deploy.sh
```

如果 Docker build 阶段 APT 镜像源访问异常，可以把 `.env` 里的 `SMARTASK_APT_MIRROR` 改成官方源或留空：

```text
SMARTASK_APT_MIRROR=http://deb.debian.org
# 或
SMARTASK_APT_MIRROR=
```

如果启用飞书同步或飞书登录，还要配置：

```text
SMARTASK_FEISHU_APP_ID
SMARTASK_FEISHU_APP_SECRET
SMARTASK_FEISHU_BASE_ID
SMARTASK_FEISHU_TABLE_ID
SMARTASK_FEISHU_VIEW_ID
FEISHU_APP_ID
FEISHU_APP_SECRET
BACKEND_URL
FRONTEND_URL
```

### 3.2 启动

推荐使用 Linux 一键脚本：

```bash
bash deploy.sh
```

如果希望启动后自动跑接口测试：

```bash
bash deploy.sh --run-tests
```

从 2026-05-11 版本开始，`deploy.sh` 在后端健康检查通过后，会默认执行容器内自检：

```bash
docker compose exec -T backend python /app/scripts/verify_deployment.py
```

自检会覆盖 PostgreSQL、关键表、HTTP 接口、报告场景识别和报告模板契约模块。只有你明确要快速启动、稍后再查时，才建议跳过：

```bash
bash deploy.sh --skip-verify
```

也可以手动执行 Docker Compose：

```bash
docker compose up -d --build
```

### 3.3 检查状态

```bash
docker compose ps
curl http://localhost:5002/api/health
```

健康检查正常时，会返回类似：

```json
{"status":"running"}
```

### 3.4 访问系统

默认前端地址：

```text
http://服务器IP:8080
```

如服务器启用了防火墙，需要开放端口：

```bash
sudo ufw allow 8080/tcp
sudo ufw allow 5002/tcp
```

云服务器还需要在安全组里开放端口。

## 4. 登录与权限

系统启用登录拦截，未登录看不到系统内容。

首次登录使用 `.env` 中的超级管理员账号：

```text
SMARTASK_ADMIN_USERNAME
SMARTASK_ADMIN_PASSWORD
```

登录后建议先完成：

1. 进入“员工权限配置”，新增管理员或普通用户。
2. 新员工默认密码是 `12345678`。
3. 员工首次登录后在右上角头像菜单修改密码。
4. 超级管理员可在头像菜单进入“系统控制台”，控制左侧导航和页面按钮开关。

相关运行态配置：

```text
config/employee_permissions.json
config/feature_flags.json
```

这两个文件在 Docker 中通过 `./config:/app/config` 挂载，不会因为重建镜像丢失。

## 5. 日常启动、停止、重启

启动：

```bash
docker compose up -d
```

停止：

```bash
docker compose stop
```

重启：

```bash
docker compose restart
```

查看后端日志：

```bash
docker compose logs -f backend
```

查看最近 200 行：

```bash
docker compose logs --tail=200 backend
```

## 6. 日常更新代码

进入项目目录：

```bash
cd smartask
```

推荐使用 Linux 一键更新脚本：

```bash
cd smartask
bash update.sh
```

脚本会自动执行：

- 更新前备份。
- 切到 `docker-setup` 分支。
- `git pull --ff-only`。
- `docker compose up -d --build`。
- 后端启动时自动应用 `backend/migrations`，包含本次报告阈值与模板配置更新。
- 后端健康检查。
- 容器内自检：PostgreSQL、关键表、HTTP 接口、报告场景识别、报告模板契约。

如需跳过拉代码，只用当前目录重建：

```bash
bash update.sh --no-pull
```

如需更新后自动跑接口测试：

```bash
bash update.sh --run-tests
```

如需只做健康检查、不做容器内自检：

```bash
bash update.sh --skip-verify
```

手动更新流程如下。

更新前先备份：

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U "${SMARTASK_DB_USERNAME:-postgres}" -d "${SMARTASK_DB_DATABASE:-postgres}" > backups/smartask_pg_$(date +%Y%m%d_%H%M%S).sql
tar -czf backups/smartask_config_$(date +%Y%m%d_%H%M%S).tar.gz config .env
git rev-parse HEAD > backups/git_commit_$(date +%Y%m%d_%H%M%S).txt
```

拉取最新代码：

```bash
git checkout docker-setup
git pull --ff-only
```

重建并启动：

```bash
docker compose up -d --build
```

说明：后端容器入口是 `python backend/bootstrap.py`，每次启动都会幂等执行 `backend/migrations`。首次空库会先导入书架与业务数据，再补跑报告配置迁移，确保新库也能写入报告模板配置。本次报告优化新增 `20260509_report_thresholds.sql`，会把商用事业部报告配置更新为“代表处 <10% 风险、10%-15% 中等、>=15% 标杆；业务代表 <10% 风险、10%-20% 中等、>=20% 标杆”。已有生产数据库不需要删除 volume，也不要执行 `docker compose down -v`。

检查：

```bash
docker compose ps
curl http://localhost:5002/api/health
```

检查报告模板配置是否已写入：

```bash
docker compose exec -T postgres psql \
  -U "${SMARTASK_DB_USERNAME:-postgres}" \
  -d "${SMARTASK_DB_DATABASE:-postgres}" \
  -c "SELECT d.dataset_code, d.dataset_name, c.config_json->>'riskThreshold' AS risk_threshold, c.config_json ? 'officeRiskThreshold' AS has_office_threshold FROM bs_datasets d LEFT JOIN bs_dataset_report_config c ON c.dataset_id = d.id WHERE d.dataset_code IN ('angel_business_2026','angel_business_2026_phase1') OR d.dataset_name LIKE '%商用事业部%';"
```

正常结果应至少看到商用事业部数据集，`risk_threshold` 为 `10`，`has_office_threshold` 为 `t`。

如果页面还是旧版本：

```text
Ctrl + F5
```

## 7. 常用端口

默认端口：

```text
前端：8080
后端：5002
PostgreSQL 宿主机映射：5433
```

这些端口来自 `.env`：

```text
SMARTASK_FRONTEND_PORT=8080
SMARTASK_BACKEND_PORT=5002
SMARTASK_DOCKER_PG_PORT=5433
```

如需修改端口，改 `.env` 后重启：

```bash
docker compose up -d
```

## 8. 数据保存位置

PostgreSQL 数据：

```text
Docker volume: smartask_pg_data
```

Chroma 向量库：

```text
Docker volume: smartask_chroma
```

运行配置目录：

```text
项目目录/config
```

后端日志：

```text
项目目录/backend/logs
```

导入导出包：

```text
项目目录/backend/imports
```

备份：

```text
项目目录/backups
```

当前 `docker-compose.yml` 已挂载：

```text
./config:/app/config
./backend/imports:/app/backend/imports
./backups:/app/backups
smartask_pg_data:/var/lib/postgresql/data
smartask_chroma:/app/chroma_db
```

因此 `docker compose up -d --build` 不会删除生产运行态数据。

## 9. 禁止误操作

正式环境不要随便执行：

```bash
docker compose down -v
```

原因：

- `down` 会停止并删除容器。
- `-v` 会删除 Docker volume。
- PostgreSQL 数据在 `smartask_pg_data`。
- Chroma 数据在 `smartask_chroma`。

安全更新代码应使用：

```bash
git checkout docker-setup
git pull --ff-only
docker compose up -d --build
```

## 10. 运行态导出/导入

如果你要把 Windows 测试环境配置同步到 Linux 正式环境，不建议直接覆盖数据库 volume。

推荐做法：

1. 在测试环境进入“迁移发布管理”。
2. 点击“导出运行态包”。
3. 在正式环境进入“迁移发布管理”。
4. 上传运行态包。
5. 先点“预检导入”。
6. 确认影响范围后，再点“确认导入”。

运行态包包含：

- JSON 配置：数据源、模型、飞书同步、员工权限、系统控制台开关等。
- PostgreSQL 书架表：数据集、字段字典、Golden SQL、Agent 提示词、报告模板等。

正式导入前系统会自动生成备份包，误操作后可用备份包回滚。

## 11. 手工备份与恢复

### 11.1 手工备份

推荐：

```bash
cd smartask
bash backup.sh
```

如只想备份配置，不导出数据库：

```bash
bash backup.sh --skip-db-dump
```

手动命令如下：

```bash
cd smartask
mkdir -p backups
docker compose exec -T postgres pg_dump -U "${SMARTASK_DB_USERNAME:-postgres}" -d "${SMARTASK_DB_DATABASE:-postgres}" > backups/smartask_pg_$(date +%Y%m%d_%H%M%S).sql
tar -czf backups/smartask_config_$(date +%Y%m%d_%H%M%S).tar.gz config .env
git rev-parse HEAD > backups/git_commit_$(date +%Y%m%d_%H%M%S).txt
```

如果 shell 没有加载 `.env`，可直接写实际用户名和库名：

```bash
docker compose exec -T postgres pg_dump -U postgres -d postgres > backups/smartask_pg_$(date +%Y%m%d_%H%M%S).sql
```

### 11.2 恢复数据库

推荐使用恢复脚本：

```bash
cd smartask
bash restore.sh --backup-dir backups/时间戳 --confirm
```

默认不会恢复 `.env`，避免覆盖生产密钥。如确实需要恢复 `.env`：

```bash
bash restore.sh --backup-dir backups/时间戳 --confirm --restore-env
```

手动恢复命令如下。

停止后端：

```bash
docker compose stop backend
```

恢复数据库：

```bash
cat backups/smartask_pg_时间戳.sql | docker compose exec -T postgres psql -U postgres -d postgres
```

恢复 `config/`：

```bash
tar -xzf backups/smartask_config_时间戳.tar.gz
```

启动后端：

```bash
docker compose start backend
```

检查：

```bash
curl http://localhost:5002/api/health
```

## 12. 故障排查

### 12.1 一键生成诊断包

如果 Linux 服务器部署失败、页面打不开、接口不健康，优先让服务器管理员在项目目录执行：

```bash
cd smartask
bash doctor.sh
```

脚本会收集：

- 系统版本、时间、磁盘和内存。
- Git 分支、远端、当前 commit 和最近提交。
- Docker / Docker Compose 版本。
- `docker compose config`、容器状态、镜像、volume 和 network。
- `backend`、`frontend`、`postgres` 最近日志。
- 端口监听、后端健康检查、前端 8080 检查。
- 脱敏后的 `.env` 摘要。

生成后，把下面文件发给开发者：

```text
diagnostics/smartask_linux_diagnose_时间戳.zip
```

如果服务器没有安装 `zip`，脚本会自动生成：

```text
diagnostics/smartask_linux_diagnose_时间戳.tar.gz
```

如果怀疑是 Docker 镜像构建失败，需要额外采集构建日志：

```bash
cd smartask
bash doctor.sh --with-build-log
```

说明：诊断包会对 `.env`、compose 配置和日志里的常见 `KEY`、`SECRET`、`TOKEN`、`PASSWORD`、`API_KEY` 做脱敏处理。

### 12.2 发布前检查

开发者推送给 Linux/宝塔服务器前，建议先执行：

```bash
bash check-release.sh
```

检查内容：

- 是否有新源码被 `.gitignore` 误伤。
- 是否有重要新文件没有 `git add`。
- 前端 `npm run build`。
- `docker compose config`。
- Linux shell 脚本是否为 LF 行尾。
- 后端与 `scripts/` 下全部 Python 文件语法。
- 报告场景识别与模板契约烟雾测试。

### 12.3 手动排查命令

后端不健康：

```bash
docker compose logs --tail=200 backend
```

数据库不健康：

```bash
docker compose logs --tail=200 postgres
docker compose ps
```

前端打不开：

```bash
docker compose logs --tail=200 frontend
docker compose ps
ss -lntp | grep 8080
```

系统控制台保存失败：

```bash
docker compose logs --tail=200 backend
curl http://localhost:5002/api/health
ls -ld config
```

常见原因：

- 当前登录账号不是超级管理员。
- 后端仍是旧镜像，需要 `docker compose up -d --build`。
- 报告模板配置为空时，先确认后端已重启；bootstrap 会在导入数据后补跑 `20260430_report_config.sql` 和 `20260509_report_thresholds.sql`。
- `config/` 目录没有写权限。
- 浏览器缓存旧前端，按 `Ctrl + F5`。

问数语义识别未生效，例如“东西部分公司业绩如何”仍只返回一个分公司：

```bash
docker compose logs --tail=200 backend
docker compose up -d --build backend frontend
curl http://localhost:5002/api/health
```

常见原因：

- 后端镜像没有重建，仍在运行旧代码。
- 浏览器页面仍使用旧前端缓存，需要 `Ctrl + F5`。
- AI 模型配置不可用时，系统会使用数据集画像兜底解析；如果数据集画像缺失，请先确认书架数据已经导入。

## 13. 给服务器管理员的简版命令

首次部署：

```bash
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
cp .env.example .env
nano .env
bash deploy.sh
docker compose ps
curl http://localhost:5002/api/health
```

日常更新：

```bash
cd smartask
bash update.sh
docker compose ps
curl http://localhost:5002/api/health
```

禁止命令：

```bash
docker compose down -v
```

除非你明确要删除数据库和向量库，否则不要执行。
