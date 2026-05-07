# SmartAsk 部署与交付手册

更新时间：2026-05-07

本文档整合原 Docker 部署、换电脑迁移、用户机更新、发布前验证等文档，作为用户机交付和开发机发布的唯一入口。

## 1. 用户机前置条件

用户机只需要安装：

- Git
- Docker Desktop

用户机不需要安装 Python、Node、PostgreSQL 开发环境。

部署前先打开 Docker Desktop，等待状态稳定，再检查：

```powershell
docker info
docker compose version
```

如果 `docker info` 报 `dockerDesktopLinuxEngine` pipe 不存在，说明 Docker Desktop 没启动或 daemon 未就绪，先打开 Docker Desktop 等 1-3 分钟。

## 2. 第一次部署

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

命令说明：

- `git clone ... smartask`：从 Gitee 下载项目到本机 `smartask` 文件夹。
- `cd smartask`：进入项目目录。
- `Copy-Item .env.example .env`：复制运行配置模板。
- `notepad .env`：填写真实 AI Key、系统密钥、数据库和飞书配置。
- `.\deploy.ps1 -RunTests`：一键构建并启动 Docker 服务，完成后自动跑接口测试。

部署成功后访问：

```text
前端：http://localhost:8080
后端健康：http://localhost:5002/api/health
```

## 3. `.env` 必填项

至少确认这些配置不是占位符：

```text
SMARTASK_SECRET_KEY
SMARTASK_AI_API_KEY
SMARTASK_AI_MODEL
SMARTASK_AI_BASE_URL
SMARTASK_ADMIN_USERNAME
SMARTASK_ADMIN_PASSWORD
SMARTASK_ADMIN_DISPLAY_NAME
```

`SMARTASK_ADMIN_PASSWORD` 是超级管理员登录密码，用户机必须改成强密码，不能使用模板值。首次登录后，超级管理员可在“员工权限配置”中维护员工账号。

如果启用飞书同步，还要填写：

```text
SMARTASK_FEISHU_APP_ID
SMARTASK_FEISHU_APP_SECRET
SMARTASK_FEISHU_BASE_ID
SMARTASK_FEISHU_TABLE_ID
SMARTASK_FEISHU_VIEW_ID
SMARTASK_FEISHU_IS_ACTIVE=true
```

`.env` 不提交到 Git / Gitee。

## 4. 登录与员工权限

系统现在启用登录拦截：未登录只能看到登录页，看不到工作台内容。

角色说明：

- 超级管理员：由 `.env` 中 `SMARTASK_ADMIN_USERNAME` / `SMARTASK_ADMIN_PASSWORD` 控制，可访问全部功能，包括“员工权限配置”。
- 管理员：由“员工权限配置”维护，可访问除“员工权限配置”外的管理功能。
- 普通用户：由“员工权限配置”维护，只能访问“智能分析工作台”。

员工账号规则：

- 新增员工时填写“员工名称、登录账号、飞书 UnionID、角色、状态”。
- 新员工默认密码为 `12345678`。
- 忘记密码时，超级管理员在“员工权限配置”里点击“重置密码”，再点击“保存配置”，该员工密码会重置为 `12345678`。
- 员工登录后可在右上角点击“改密”修改自己的密码。
- 出于安全考虑，系统不展示员工明文密码，只保存 `password_salt` 和 `password_hash`。

运行态权限文件：

```text
config/employee_permissions.json
```

该文件由系统运行时生成并挂载到 Docker 后端容器，属于用户机本地数据，已加入 `.gitignore`，不会提交到 Git。

## 5. 日常更新

```powershell
cd smartask
.\update.ps1 -RunTests
```

命令说明：

- `cd smartask`：进入已经部署过的项目目录。
- `.\update.ps1 -RunTests`：更新前备份、拉取 Gitee 最新代码、重建 Docker 服务，并跑接口测试。

可选参数：

- `-NoPull`：不执行 `git pull`，适合离线更新包。
- `-NoBuild`：不重新 build，只重启已有镜像。
- `-SkipBackup`：跳过更新前备份，不推荐普通用户使用。
- `-RunStreamTests`：额外测试 AI 流式问数链路，依赖真实模型 Key 和网络。

## 6. 常用运维命令

软重启，不重建镜像，不删除数据：

```powershell
.\reset.ps1 -Mode Restart
```

重建服务，不删除数据卷：

```powershell
.\reset.ps1 -Mode Rebuild
```

完全清空重装，会删除数据库和向量数据卷：

```powershell
.\reset.ps1 -Mode Data -ConfirmDataReset
```

手工备份：

```powershell
.\backup.ps1
```

生成诊断包：

```powershell
.\doctor.ps1
```

查看后端日志：

```powershell
docker compose logs -f backend
```

## 7. 诊断包

报错时执行：

```powershell
cd smartask
.\doctor.ps1
```

生成后把这个 zip 发给开发者：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

诊断包包含 Docker 状态、服务日志、端口占用、健康检查和脱敏 `.env` 摘要。Key、Secret、Token、Password 会自动脱敏。

## 8. 备份策略

`update.ps1` 默认会先执行备份。

手工备份：

```powershell
.\backup.ps1
```

备份输出：

```text
backups\时间戳\
```

通常包含：

- `config/`
- `.env.example`
- `bundles/`
- `postgres.sql`
- `README.txt`

`backups/` 已加入 `.gitignore`。

## 9. 开发机发布流程

开发机改完代码后先验证：

```powershell
npm run build
python .\scripts\integration_test.py --base-url http://localhost:5002 --frontend-url http://localhost:5173 --no-wait
```

提交并推送：

```powershell
git add .
git commit -m "更新说明"
git push gitee docker-setup
```

如果发布稳定版本：

```powershell
git tag v1.0.0
git push gitee v1.0.0
```

## 10. 用户机按 tag 更新或回退

切到指定 tag：

```powershell
git fetch --all --tags
git checkout v1.0.0
.\update.ps1 -NoPull -RunTests
```

升级到新 tag：

```powershell
git fetch --all --tags
git checkout v1.0.1
.\update.ps1 -NoPull -RunTests
```

回退到旧 tag：

```powershell
git fetch --all --tags
git checkout v1.0.0
.\update.ps1 -NoPull -RunTests
```

## 10. Docker 自动初始化机制

后端容器启动时会执行 `backend/bootstrap.py`：

1. 等待 PostgreSQL 容器健康。
2. 初始化 `config/` 默认 JSON 配置。
3. 导入 `runtime_config_bundle.json` 中的运行时配置。
4. 应用 `backend/migrations/*.sql` schema 迁移。
5. 首次空库时导入 `bookshelf_bundle.json` 和 `angel_group_data_bundle.json`。
6. 启动 Flask 主程序。

再次启动不会默认覆盖用户数据。如需覆盖式重导入：

```powershell
.\deploy.ps1 -ForceImport
```

如需覆盖式重写配置：

```powershell
.\deploy.ps1 -ForceConfig
```

## 11. 当前验证基线

2026-05-06 本地验证结果：

- PowerShell 脚本解析通过。
- 后端 Python AST 检查通过。
- 前端 `npm run build` 通过。
- 本地集成测试 `16 PASS / 0 FAIL / 0 SKIP`。
- `docker compose config` 通过。

备注：完整 `docker compose up` 需要 Docker Desktop daemon 处于 running 状态。

## 12. 直接发给用户机的命令

下面这段可以直接发给用户。

### 12.1 第一次部署

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

命令解释：

- `git clone https://gitee.com/tailin1/volcano-intelligent-questions.git smartask`：从 Gitee 下载项目，并把文件夹命名为 `smartask`。
- `cd smartask`：进入项目目录，后续命令都要在这个目录执行。
- `Copy-Item .env.example .env`：复制一份运行配置文件，真实配置都写到 `.env`。
- `notepad .env`：打开 `.env`，填写 AI Key、系统密钥、飞书配置等真实值；必须把 `SMARTASK_ADMIN_PASSWORD` 改成强密码。
- `.\deploy.ps1 -RunTests`：一键构建并启动 Docker 服务，启动后自动跑接口测试。默认会构建前端镜像和后端镜像。

部署成功后访问：

```text
http://localhost:8080
```

首次登录使用 `.env` 中配置的超级管理员账号：

```text
账号：SMARTASK_ADMIN_USERNAME 的值，默认 admin
密码：SMARTASK_ADMIN_PASSWORD 的值
```

登录后进入“员工权限配置”，可以新增管理员或普通用户。新增员工默认密码为 `12345678`；忘记密码时，超级管理员可点击“重置密码”，再点“保存配置”，把该员工密码重置回 `12345678`。

历史分析记录按登录账号隔离：同一台电脑上，不同账号登录后只能看到自己的历史分析。历史记录保存在浏览器本地存储中，切换浏览器或清理浏览器缓存后，本地历史不会自动同步。

### 12.2 日常更新

```powershell
cd smartask
.\update.ps1 -RunTests
```

命令解释：

- `cd smartask`：进入已经部署过的项目目录。
- `.\update.ps1 -RunTests`：自动备份、拉取 Gitee 最新代码、重建 Docker 服务，并跑接口测试。默认会执行 `docker compose up -d --build`，因此会重建前端静态资源。

更新完成后访问：

```text
http://localhost:8080
```

如果页面仍显示旧样式或旧按钮，按 `Ctrl + F5` 强制刷新浏览器缓存。不要加 `-NoBuild`，除非只想重启旧镜像。

更新后的历史分析记录仍按登录账号隔离，不同员工不会互相看到历史会话。

### 12.3 报错时生成诊断包

```powershell
cd smartask
.\doctor.ps1
```

命令解释：

- `cd smartask`：进入项目目录。
- `.\doctor.ps1`：收集 Docker 状态、服务日志、端口占用、健康检查和脱敏配置，生成诊断包。

生成后，把下面目录里的 zip 发给开发者：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

说明：诊断包里的 `.env` 会自动脱敏，不会直接暴露 Key、Secret、Password。
