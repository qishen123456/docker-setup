# 开发机与用户机更新说明（Gitee + Docker 版）

更新时间：2026-05-06

适用对象：

- 开发机：你的电脑，负责改代码、验证、提交到 Gitee。
- 用户机：业务用户电脑，只负责拉代码、启动 Docker、正常使用系统。

Gitee 仓库：

```text
https://gitee.com/tailin1/volcano-intelligent-questions.git
```

## 1. 一句话原则

不要去用户机上手工改代码。

正确流程是：

1. 开发机改好代码并推送到 Gitee。
2. 用户机执行更新脚本。
3. Docker 自动重建前端、后端和数据库服务。
4. 用户打开浏览器使用系统。

用户机不需要安装 Python、Node、PostgreSQL 开发环境，只需要 Git、Docker Desktop 和项目 `.env`。

## 2. 用户机第一次部署

### 2.1 用户机前置条件

用户机需要先安装：

- Git
- Docker Desktop

部署前确认 Docker Desktop 已启动，并且鲸鱼图标状态稳定。

在 PowerShell 里检查：

```powershell
docker info
docker compose version
```

如果 `docker info` 报错，先打开 Docker Desktop，等 1-3 分钟后再试。

### 2.2 克隆项目

打开 PowerShell，执行：

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
```

如果你指定用户机使用某个稳定分支，例如 `main`：

```powershell
git checkout main
```

如果你发布的是 tag，例如 `v1.0.0`：

```powershell
git fetch --all --tags
git checkout v1.0.0
```

### 2.3 准备 `.env`

`.env` 是用户机运行配置，包含 AI Key、数据库密码、飞书密钥等敏感信息，不提交到 Gitee。

有两种方式：

方式 A：管理员直接给用户一份可用 `.env`

把 `.env` 放到项目根目录：

```text
smartask\.env
```

方式 B：用户从模板复制后填写

```powershell
Copy-Item .env.example .env
notepad .env
```

至少要确认这些值不是占位符：

```text
SMARTASK_SECRET_KEY
SMARTASK_AI_API_KEY
SMARTASK_AI_MODEL
SMARTASK_AI_BASE_URL
```

如果启用飞书同步，还要填写：

```text
SMARTASK_FEISHU_APP_ID
SMARTASK_FEISHU_APP_SECRET
SMARTASK_FEISHU_BASE_ID
SMARTASK_FEISHU_TABLE_ID
SMARTASK_FEISHU_VIEW_ID
SMARTASK_FEISHU_IS_ACTIVE=true
```

### 2.4 一键部署

用户机执行：

```powershell
.\deploy.ps1 -RunTests
```

这个脚本会自动做这些事：

- 检查 Docker 是否可用。
- 检查 Docker Compose 是否可用。
- 检查 `.env` 是否存在。
- 检查关键密钥是否还是占位符。
- 检查端口占用并给出提示。
- 执行 `docker compose config`。
- 构建并启动 PostgreSQL、后端、前端。
- 等待后端健康检查通过。
- 运行接口集成测试。

部署成功后访问：

```text
前端：http://localhost:8080
后端健康：http://localhost:5002/api/health
```

## 3. 用户机日常更新

用户机平时不要手工执行 `git pull` + `docker compose up`，推荐统一用更新脚本：

```powershell
.\update.ps1 -RunTests
```

它会自动做：

- 更新前备份。
- `git pull --ff-only` 拉取 Gitee 最新代码。
- 校验 Docker Compose 配置。
- 重新构建并启动容器。
- 等待后端健康检查。
- 运行集成测试。

如果只是想更新代码和重启，不跑测试：

```powershell
.\update.ps1
```

如果用户机网络临时无法访问 Gitee，但你已经用其他方式把代码放好了：

```powershell
.\update.ps1 -NoPull -RunTests
```

如果这次确认不需要备份：

```powershell
.\update.ps1 -SkipBackup
```

一般不建议用户跳过备份，除非你明确知道自己在做什么。

## 4. 用户机常用操作

### 4.1 软重启

只重启容器，不重建镜像，不删除数据：

```powershell
.\reset.ps1 -Mode Restart
```

### 4.2 重建服务

重新 build 镜像并启动，不删除数据库数据：

```powershell
.\reset.ps1 -Mode Rebuild
```

### 4.3 完全清空重装

这个操作会清空数据库和向量数据卷，谨慎使用。

```powershell
.\reset.ps1 -Mode Data -ConfirmDataReset
```

如果不加 `-ConfirmDataReset`，脚本会拒绝执行，避免误删用户数据。

### 4.4 查看日志

看后端日志：

```powershell
docker compose logs -f backend
```

看全部服务日志：

```powershell
docker compose logs -f
```

看容器状态：

```powershell
docker compose ps
```

## 5. 用户机出问题怎么处理

### 5.1 生成诊断包

用户机遇到问题时，不要让用户截图一堆窗口，直接执行：

```powershell
.\doctor.ps1
```

脚本会生成诊断包：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

把这个 zip 发给开发者即可。

诊断包会包含：

- Docker 版本信息。
- Docker Compose 配置。
- 容器状态。
- backend/frontend/postgres 日志。
- 端口占用。
- 后端健康检查结果。
- 脱敏后的 `.env` 摘要。

敏感字段会脱敏，例如 Key、Secret、Token、Password。

### 5.2 Docker 没启动

现象：

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```

处理：

1. 打开 Docker Desktop。
2. 等待 Docker Desktop 状态稳定。
3. 执行：

```powershell
docker info
```

如果成功，再执行：

```powershell
.\deploy.ps1 -RunTests
```

或：

```powershell
.\update.ps1 -RunTests
```

### 5.3 端口冲突

默认端口：

| 服务 | 宿主机端口 |
| --- | --- |
| 前端 | 8080 |
| 后端 | 5002 |
| PostgreSQL | 5433 |

如果端口冲突，修改 `.env`：

```text
SMARTASK_FRONTEND_PORT=8081
SMARTASK_BACKEND_PORT=5003
SMARTASK_DOCKER_PG_PORT=5434
```

然后重新部署：

```powershell
.\deploy.ps1 -RunTests
```

### 5.4 `.env` 仍是占位符

如果脚本提示 `SMARTASK_AI_API_KEY` 或 `SMARTASK_SECRET_KEY` 仍是占位值：

```powershell
notepad .env
```

填入真实值后重新执行：

```powershell
.\deploy.ps1 -RunTests
```

### 5.5 页面没变化

先强制刷新浏览器：

```text
Ctrl + F5
```

如果仍没变化：

```powershell
.\update.ps1 -NoPull -RunTests
```

## 6. 开发机发布流程

开发机负责改代码、验证、推送。

推荐流程：

```powershell
git pull gitee main
```

改代码后先本地验证：

```powershell
npm run build
python .\scripts\integration_test.py --base-url http://localhost:5002 --frontend-url http://localhost:5173 --no-wait
```

确认没问题后提交：

```powershell
git add .
git commit -m "更新智能问数与Docker部署脚本"
git push gitee main
```

如果要发布稳定版本，打 tag：

```powershell
git tag v1.0.0
git push gitee v1.0.0
```

用户机可以选择跟随 `main`，也可以固定使用某个 tag。

## 7. 用户机按 tag 更新

如果你发布了稳定 tag，例如 `v1.0.0`，用户机执行：

```powershell
git fetch --all --tags
git checkout v1.0.0
.\update.ps1 -NoPull -RunTests
```

以后要升级到 `v1.0.1`：

```powershell
git fetch --all --tags
git checkout v1.0.1
.\update.ps1 -NoPull -RunTests
```

## 8. 用户机回退版本

如果升级后有问题，回退到上一个 tag：

```powershell
git fetch --all --tags
git checkout v1.0.0
.\update.ps1 -NoPull -RunTests
```

如果使用 `main`，想回退到上一个提交：

```powershell
git log --oneline -5
git checkout <上一个稳定commit>
.\update.ps1 -NoPull -RunTests
```

更推荐用 tag，因为 tag 更清晰，不容易选错 commit。

## 9. 备份与数据安全

`update.ps1` 默认会先执行备份。

也可以手工备份：

```powershell
.\backup.ps1
```

备份输出位置：

```text
backups\时间戳\
```

通常包含：

- `config/`
- `.env.example`
- `bundles/`
- `postgres.sql`
- `README.txt`

`backups/` 已加入 `.gitignore`，不会被提交到 Gitee。

## 10. 用户机推荐命令速查

首次部署：

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

日常更新：

```powershell
.\update.ps1 -RunTests
```

只重启：

```powershell
.\reset.ps1 -Mode Restart
```

重建服务：

```powershell
.\reset.ps1 -Mode Rebuild
```

生成诊断包：

```powershell
.\doctor.ps1
```

手动备份：

```powershell
.\backup.ps1
```

查看日志：

```powershell
docker compose logs -f backend
```

清空重装：

```powershell
.\reset.ps1 -Mode Data -ConfirmDataReset
```

## 11. 直接发给用户的命令

第一次部署：

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

这些命令的作用：

- `git clone ... smartask`：从 Gitee 下载项目到本机 `smartask` 文件夹。
- `cd smartask`：进入项目目录。
- `Copy-Item .env.example .env`：复制一份运行配置文件。
- `notepad .env`：打开配置文件，填写 AI Key、密钥、飞书等真实配置。
- `.\deploy.ps1 -RunTests`：一键构建并启动 Docker 服务，完成后自动跑接口测试。

日常更新：

```powershell
cd smartask
.\update.ps1 -RunTests
```

这些命令的作用：

- `cd smartask`：进入已经部署过的项目目录。
- `.\update.ps1 -RunTests`：自动备份、拉取 Gitee 最新代码、重建 Docker 服务，并跑接口测试。

报错时生成诊断包：

```powershell
cd smartask
.\doctor.ps1
```

这些命令的作用：

- `cd smartask`：进入项目目录。
- `.\doctor.ps1`：收集 Docker 状态、服务日志、端口占用、健康检查和脱敏配置，生成诊断包。

生成后把下面目录里的 zip 发给开发者：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

这个 zip 是排查问题用的诊断包，里面的 `.env` 会自动脱敏，不会直接暴露 Key、Secret、Password。
