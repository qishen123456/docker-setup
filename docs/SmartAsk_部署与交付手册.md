# SmartAsk 部署与交付手册

更新时间：2026-05-08

当前项目真实 Git 信息：

```text
Gitee remote：https://gitee.com/tailin1/volcano-intelligent-questions.git
当前可拉取发布分支：docker-setup
```

注意：Linux/Git 对分支名大小写敏感。已核验当前本地与 Gitee 远端存在的分支是 `docker-setup`；如果后续你在 Gitee 另建大写 `DOCKER-SETUP` 分支，命令里的 `docker-setup` 才需要替换成 `DOCKER-SETUP`。

本文档是 SmartAsk 给用户机交付、Windows 一键 Docker 部署、日常更新、权限控制和运行态配置保护的统一入口。Linux 服务器部署请另看：

```text
docs/Linux_Docker部署运维手册.md
```

如果你要从 Windows 测试环境发布到 Linux 正式环境，并保护生产数据源、数据集、提示词、模型配置和权限配置，请同时阅读：

```text
docs/迁移发布与运行态配置保护方案.md
docs/运行态配置导出导入操作手册.md
```

## 1. 当前交付能力

当前项目支持：

- Docker 一键部署前端、后端、PostgreSQL、Chroma 向量库。
- 未登录拦截，用户不登录看不到系统内容。
- 超级管理员、管理员、普通用户三类身份。
- 员工账号密码登录，员工默认密码 `12345678`，员工可前端改密。
- 超级管理员可在“员工权限配置”新增员工、修改角色、重置密码、维护飞书 UnionID。
- 超级管理员可从头像菜单进入“系统控制台”，按身份控制左侧导航和页面按钮显示。
- 运行态配置导出/导入，保护数据源、数据集、提示词、模型配置、报告模板、员工权限和系统控制台开关。
- 更新前备份、诊断包、Docker 重建和健康检查。

## 2. 用户机前置条件

用户机只需要安装：

- Git
- Docker Desktop

用户机不需要安装 Python、Node、PostgreSQL 开发环境。

部署前先打开 Docker Desktop，等待状态稳定，再检查：

```powershell
docker info
docker compose version
```

如果 `docker info` 报 `dockerDesktopLinuxEngine` pipe 不存在，说明 Docker Desktop 没启动或 daemon 未就绪。先打开 Docker Desktop，等待 1-3 分钟后再执行部署命令。

## 3. 第一次部署

下面这段可以直接发给用户机执行。

```powershell
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

命令解释：

- `git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask`：从 Gitee 下载 `docker-setup` 分支，并把目录命名为 `smartask`。
- `cd smartask`：进入项目目录，后续命令都在这里执行。
- `Copy-Item .env.example .env`：复制一份真实运行配置文件。
- `notepad .env`：打开配置文件，填写 AI Key、系统密钥、超管密码、飞书配置等真实值。
- `.\deploy.ps1 -RunTests`：一键构建并启动 Docker 服务，启动后自动跑接口测试。

部署成功后访问：

```text
前端：http://localhost:8080
后端健康：http://localhost:5002/api/health
```

## 4. `.env` 必填项

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

生产环境必须修改：

```text
SMARTASK_ADMIN_PASSWORD=请改成强密码
```

如果启用飞书同步或飞书登录，还要填写：

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

`.env` 不提交到 Git / Gitee。

## 5. 登录与权限

系统启用登录拦截：未登录只能看到登录页，看不到工作台内容。

角色说明：

- 超级管理员：由 `.env` 的 `SMARTASK_ADMIN_USERNAME` / `SMARTASK_ADMIN_PASSWORD` 控制，可访问全部功能。
- 管理员：由“员工权限配置”维护，可访问业务配置功能，但默认不能维护员工权限和系统控制台。
- 普通用户：由“员工权限配置”维护，默认只访问“智能分析工作台”。

员工账号规则：

- 新增员工时填写“员工名称、登录账号、飞书 UnionID、角色、状态”。
- 新员工默认密码是 `12345678`。
- 忘记密码时，超级管理员在“员工权限配置”点击“重置密码”，再点击“保存配置”，员工密码会重置为 `12345678`。
- 员工登录后可在右上角头像菜单点击“修改密码”。
- 系统不展示员工明文密码，只保存 `password_salt` 和 `password_hash`。

员工权限文件：

```text
config/employee_permissions.json
```

## 6. 系统控制台

超级管理员点击右上角头像，选择“系统控制台”，可以进入权限矩阵页面。

系统控制台现在按两层控制：

- 左侧导航栏：控制“智能分析工作台、数据资产管理、模型服务配置、迁移发布管理”等入口是否显示。
- 页面按钮：控制每个页面内部的重要交互按钮，例如发送问题、停止执行、SQL 复制、报告下载、数据集保存、数据源编辑、运行态导入、员工重置密码等。

保存后立即生效。若点击“保存配置”没有成功提示，请按以下顺序检查：

```powershell
docker compose logs --tail=200 backend
docker compose ps
curl http://localhost:5002/api/health
```

常见原因：

- 当前账号不是超级管理员，后端会返回 403。
- 后端没有重启，仍在跑旧代码。
- `config/feature_flags.json` 所在目录没有写入权限。
- 浏览器还缓存旧前端，按 `Ctrl + F5` 强制刷新。

系统控制台配置文件：

```text
config/feature_flags.json
```

该文件属于运行态配置，会随运行态导出/导入一起迁移。

## 7. 日常更新

```powershell
cd smartask
.\update.ps1 -RunTests
```

命令解释：

- `cd smartask`：进入已经部署过的项目目录。
- `.\update.ps1 -RunTests`：自动备份、拉取 Gitee 最新代码、重建 Docker 服务，并跑接口测试。

可选参数：

- `-NoPull`：不执行 `git pull`，适合离线更新包。
- `-NoBuild`：不重新 build，只重启已有镜像。
- `-SkipBackup`：跳过更新前备份，不推荐生产/用户机使用。
- `-RunStreamTests`：额外测试 AI 流式问数链路，需要真实模型 Key 和网络。

如果页面仍显示旧样式或旧按钮：

```text
Ctrl + F5
```

不要使用 `-NoBuild`，除非你明确只想重启旧镜像。

如果用户机之前拉错了默认分支，只看到 README，按下面方式修正：

```powershell
cd smartask
git fetch --all
git checkout docker-setup
git pull --ff-only
.\deploy.ps1 -RunTests
```

## 8. 运行态配置保护

代码更新不应该覆盖用户机运行态配置。当前重要运行态资源包括：

- `config/datasources.json`
- `config/ai_settings.json`
- `config/feishu_sync.json`
- `config/app_config.json`
- `config/employee_permissions.json`
- `config/feature_flags.json`
- PostgreSQL 中的数据集、字段字典、Golden SQL、Agent 提示词、报告模板等书架表。

推荐发布流程：

1. 测试环境改代码并验证。
2. 正式环境更新代码前先备份。
3. 如需迁移配置，从测试环境导出运行态包。
4. 在正式环境“迁移发布管理”先预检导入。
5. 确认无误后再正式导入。
6. 导入前系统会自动备份当前正式环境运行态资源。

手动备份：

```powershell
.\backup.ps1
```

运行态导出/导入页面：

```text
迁移发布管理
```

## 9. 常用运维命令

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

生成诊断包：

```powershell
.\doctor.ps1
```

查看后端日志：

```powershell
docker compose logs -f backend
```

查看容器状态：

```powershell
docker compose ps
```

## 10. 诊断包

报错时执行：

```powershell
cd smartask
.\doctor.ps1
```

生成后，把下面目录里的 zip 发给开发者：

```text
diagnostics\smartask_diagnose_时间戳.zip
```

诊断包包含 Docker 状态、服务日志、端口占用、健康检查和脱敏 `.env` 摘要。Key、Secret、Token、Password 会自动脱敏。

## 11. Docker 数据保存位置

PostgreSQL 数据：

```text
Docker volume: smartask_pg_data
```

Chroma 向量库：

```text
Docker volume: smartask_chroma
```

运行配置：

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

正式环境不要执行：

```powershell
docker compose down -v
```

`-v` 会删除 Docker volume，可能导致 PostgreSQL 和 Chroma 数据丢失。

## 12. 开发机发布前验证

开发机改完代码后建议执行：

```powershell
cd frontend
npm run build
cd ..
python .\scripts\integration_test.py --base-url http://localhost:5002 --frontend-url http://localhost:5173 --no-wait
```

如果只验证后端语法，可执行：

```powershell
python -m py_compile backend\app.py
```

如果 Windows 上 `__pycache__` 被占用，可改用源码编译检查：

```powershell
python -c "compile(open('backend/app.py', encoding='utf-8').read(), 'backend/app.py', 'exec'); print('OK')"
```

## 13. 用户机最短命令

第一次部署：

```powershell
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
Copy-Item .env.example .env
notepad .env
.\deploy.ps1 -RunTests
```

日常更新：

```powershell
cd smartask
.\update.ps1 -RunTests
```

报错生成诊断包：

```powershell
cd smartask
.\doctor.ps1
```
