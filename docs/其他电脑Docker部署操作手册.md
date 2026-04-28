# 智能问数项目其他电脑 Docker 部署操作手册

## 1. 这份手册是干什么的

这份文档是给“用户电脑”用的。

你可以把电脑分成两类：

- 开发机：你自己改代码、调样式、修后端的电脑
- 用户机：别人拿来运行系统的电脑

以后推荐的方式是：

1. 你在开发机改代码
2. 代码推到 Gitee
3. 用户机拉最新代码
4. 用户机用 Docker 启动

这样用户机不用再单独装 Python、Node、本地 PostgreSQL 运行环境。

---

## 2. 当前部署方案说明

当前项目的 Docker 方案是三段式：

- `frontend`：前端页面，容器里用 `nginx` 提供访问
- `backend`：后端 Flask 服务
- `postgres`：项目自己的 PostgreSQL 数据库

默认端口如下：

- 前端访问地址：`http://localhost:8080`
- 后端接口地址：`http://localhost:5002`
- PostgreSQL 映射端口：`5433`

说明：

- 用户平时只需要打开 `http://localhost:8080`
- 后端和数据库一般不用手动点开
- 项目的敏感信息放在 `.env` 文件里，**不要提交到 Git**

另外还有一个很关键的文件：

- `backend/imports/bookshelf_bundle.json`

这个文件是“书架元数据打包文件”，里面放的是：

- 数据集基本信息
- 同义词
- LLD
- 数据字典
- Golden SQL
- Agent Prompt
- 常见问题
- 回归题

如果这个文件存在，部署脚本会自动导入它。  
如果这个文件不存在，部署脚本只会自动灌一套默认“商用事业部模板”。

另外还支持一份业务数据快照文件：

- `backend/imports/angel_group_data_bundle.json`

这个文件里放的是 `angel_group_data` 的真实业务数据快照。  
如果这个文件存在，部署脚本会自动把它导入数据库。

---

## 3. 用户机第一次部署前，需要准备什么

### 3.1 必装软件

用户机至少安装这两个：

1. `Git`
2. `Docker Desktop`

建议：

- Windows 10 / Windows 11
- Docker Desktop 启动正常
- 磁盘至少预留 `20GB+`

---

### 3.2 需要从你这里拿到什么

用户机第一次部署，需要你提供两样东西：

1. Gitee 仓库地址  
   例如：

```text
https://gitee.com/tailin1/volcano-intelligent-questions.git
```

2. `.env` 文件  
   这个文件里有：

- AI Key
- 数据库配置
- 飞书配置
- 端口配置

注意：

- `.env` 不要放到 Gitee
- `.env` 单独发给用户
- 用户只需要把它放到项目根目录

---

## 4. 如果用户机在国内网络环境，建议先配 Docker 加速

如果用户机拉镜像很慢，先做这一步。

### 4.1 配 Docker 代理

如果用户机本机有代理，比如：

```text
http://127.0.0.1:7890
```

在 Docker Desktop 里这样配置：

1. 打开 `Docker Desktop`
2. 点右上角 `Settings`
3. 打开 `Resources`
4. 打开 `Proxies`
5. 选择 `Manual proxy configuration`
6. `HTTP Proxy` 填：

```text
http://127.0.0.1:7890
```

7. `HTTPS Proxy` 也填：

```text
http://127.0.0.1:7890
```

8. 点 `Apply & Restart`

---

### 4.2 配 Docker 镜像加速

在 Docker Desktop 里继续设置：

1. 打开 `Settings`
2. 打开 `Docker Engine`
3. 在 JSON 里加入：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.1ms.run"
  ]
}
```

4. 点 `Apply & Restart`

说明：

- 如果原来 JSON 里已经有别的配置，不要全删
- 只要把 `registry-mirrors` 这一段补进去就行

---

## 5. 用户机第一次部署，完整步骤

以下步骤默认：

- 用户机已经安装了 `Git`
- 用户机已经安装并打开了 `Docker Desktop`
- 你已经把 `.env` 发给用户

---

### 5.1 拉项目代码

打开 PowerShell，进入你想放项目的目录，例如：

```powershell
cd D:\
mkdir projects
cd .\projects
```

拉代码：

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git
cd .\volcano-intelligent-questions
```

如果当前 Docker 版本还在专门分支上，就切到对应分支：

```powershell
git checkout docker-setup
```

如果以后 Docker 方案已经合并到主分支，就不需要这一步。

---

### 5.2 放 `.env`

把你提供的 `.env` 文件放到项目根目录。

放好以后，项目根目录里应该能看到：

```text
docker-compose.yml
.env
backend
frontend
docs
```

---

### 5.3 第一次启动

你现在有两种方式。

#### 方式 A：直接运行一键脚本

项目根目录已经提供了：

- `deploy.ps1`
- `deploy.bat`

最简单的是直接双击：

```text
deploy.bat
```

或者在 PowerShell 执行：

```powershell
.\deploy.ps1
```

脚本会自动做这些事：

1. 检查 Docker Desktop
2. 检查 `.env`
3. 启动 `frontend/backend/postgres`
4. 如果存在 `backend/imports/bookshelf_bundle.json`，自动导入完整书架元数据
5. 如果没有 bundle，就自动灌入默认“商用事业部”模板
6. 如果存在 `backend/imports/angel_group_data_bundle.json`，自动导入真实业务数据快照

#### 方式 B：手动执行 Docker 命令

在项目根目录执行：

```powershell
docker compose up -d --build
```

说明：

- `--build`：第一次要构建镜像
- `-d`：后台运行

第一次通常会比较慢，因为要下载：

- Python 基础镜像
- Node 基础镜像
- Nginx 基础镜像
- PostgreSQL 基础镜像

---

### 5.4 检查是否启动成功

执行：

```powershell
docker compose ps
```

正常情况下应该能看到 3 个服务：

- `smartask-frontend`
- `smartask-backend`
- `smartask-postgres`

如果状态正常，再打开浏览器访问：

```text
http://localhost:8080
```

---

## 6. 用户机日常怎么启动、停止、重启

### 6.1 启动

在项目根目录执行：

```powershell
docker compose up -d
```

---

### 6.2 停止

```powershell
docker compose down
```

---

### 6.3 重启

```powershell
docker compose restart
```

---

### 6.4 看运行状态

```powershell
docker compose ps
```

---

### 6.5 看日志

看全部日志：

```powershell
docker compose logs -f
```

只看后端日志：

```powershell
docker compose logs -f backend
```

只看前端日志：

```powershell
docker compose logs -f frontend
```

只看数据库日志：

```powershell
docker compose logs -f postgres
```

---

## 7. 用户机以后怎么更新版本

以后更新很简单，用户机不改代码，只做同步。

### 7.1 一键更新

项目根目录已经提供了：

- `update.ps1`
- `update.bat`

最简单的是直接双击：

```text
update.bat
```

或者在 PowerShell 执行：

```powershell
.\update.ps1
```

如果仓库里存在 `backend/imports/bookshelf_bundle.json`，更新脚本会同步把这个 bundle 重新导入一次。  
这意味着用户机上的书架内容会和仓库里的 bundle 保持一致。

如果仓库里存在 `backend/imports/angel_group_data_bundle.json`，更新脚本也会同步导入这份业务数据快照。

### 7.2 手动更新

在项目根目录执行：

```powershell
git pull
docker compose up -d --build
```

意思是：

- `git pull`：拉你最新代码
- `docker compose up -d --build`：按新代码重新构建并启动

如果你是按分支发布，比如一直用 `docker-setup`：

```powershell
git checkout docker-setup
git pull
docker compose up -d --build
```

---

## 8. 如果你在开发机更新项目，推荐怎么发给用户机

开发机的推荐流程：

```powershell
git add .
git commit -m "这次改动说明"
git push gitee docker-setup
```

如果以后稳定了，可以改成推主分支：

```powershell
git push gitee main
```

用户机再执行：

```powershell
git pull
docker compose up -d --build
```

如果你不仅改了代码，还改了数据集书架内容，推荐你在开发机先执行一次 bundle 导出，再提交 Gitee。

导出命令：

```powershell
py -3.11 .\backend\export_bookshelf_bundle.py
```

导出后会生成：

```text
backend\imports\bookshelf_bundle.json
```

然后把这个文件一起提交到 Gitee。  
这样用户机更新时，才能拿到和你开发机一致的数据集元数据。

如果你还想让用户机第一次部署就带上当前业务数据，再执行：

```powershell
python .\backend\export_angel_group_data.py
```

导出后会生成：

```text
backend\imports\angel_group_data_bundle.json
```

然后把这个文件也一起提交到 Gitee。

---

## 9. `.env` 文件怎么处理

### 9.1 原则

`.env` 只在本地保存，不上传到 Gitee。

### 9.2 你该怎么发给用户

推荐方式：

- 单独发一个 `.env`
- 或者压缩包里单独附带

不要：

- 发截图
- 直接贴到公开群里
- 提交到仓库

### 9.3 用户机放哪

必须放在项目根目录，也就是和 `docker-compose.yml` 同级。

---

## 10. 如果用户机端口冲突怎么办

当前默认端口是：

- 前端：`8080`
- 后端：`5002`
- 数据库：`5433`

如果用户机已经占用了这些端口，就改 `.env` 里的：

```env
SMARTASK_BACKEND_PORT=5002
SMARTASK_FRONTEND_PORT=8080
SMARTASK_DOCKER_PG_PORT=5433
```

例如改成：

```env
SMARTASK_BACKEND_PORT=5102
SMARTASK_FRONTEND_PORT=8180
SMARTASK_DOCKER_PG_PORT=5543
```

改完以后重新执行：

```powershell
docker compose down
docker compose up -d --build
```

---

## 11. 常见问题排查

### 11.1 `docker pull` 很慢

先检查：

1. Docker Desktop 是否已经启动
2. Docker 代理是否配置
3. `registry-mirrors` 是否配置

如果还是慢，先单独拉基础镜像：

```powershell
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:1.27-alpine
docker pull postgres:16-alpine
```

然后再执行：

```powershell
docker compose up -d --build
```

---

### 11.2 页面打不开

先检查容器状态：

```powershell
docker compose ps
```

再看前端日志：

```powershell
docker compose logs -f frontend
```

最后确认浏览器访问的是：

```text
http://localhost:8080
```

---

### 11.3 页面打开了，但接口报错

看后端日志：

```powershell
docker compose logs -f backend
```

重点看：

- AI Key 是否有效
- 数据库是否连上
- 飞书配置是否正确

---

### 11.4 数据库连接失败

先确认：

- `postgres` 容器是不是启动了
- `.env` 里的数据库用户名密码是否正确

查看数据库容器：

```powershell
docker compose logs -f postgres
```

---

### 11.5 更新后异常

先完整重建：

```powershell
docker compose down
docker compose up -d --build
```

如果还是不行，再考虑切回旧分支或旧版本。

---

## 12. 如果要彻底清掉容器和数据

普通停止不会删数据：

```powershell
docker compose down
```

如果要连卷也一起删掉：

```powershell
docker compose down -v
```

注意：

- `-v` 会删除 PostgreSQL 持久化数据
- 只在你确认不要数据时才用

---

## 13. 最推荐你的实际工作流

### 开发机

你负责：

- 改代码
- 调试
- 推 Gitee

### 用户机

用户负责：

- 拉代码
- 放 `.env`
- 启动 Docker

### 最常用的三条命令

第一次部署：

```powershell
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git
cd .\volcano-intelligent-questions
git checkout docker-setup
docker compose up -d --build
```

平时启动：

```powershell
docker compose up -d
```

平时更新：

```powershell
git pull
docker compose up -d --build
```

---

## 14. 你现在最应该怎么用这份手册

建议顺序：

1. 先在你的开发机维护好数据集书架和业务数据
2. 执行：

```powershell
python .\backend\export_bookshelf_bundle.py
```

3. 再执行：

```powershell
python .\backend\export_angel_group_data.py
```

4. 把生成的：

- `backend/imports/bookshelf_bundle.json`
- `backend/imports/angel_group_data_bundle.json`

一起提交到 Gitee
5. 再让用户机执行 `deploy.bat` 或 `deploy.ps1`

如果现在 Docker 方案还在 `docker-setup` 分支，就先按这个分支部署。  
等你验证稳定后，再合并到主分支，后面用户机就更省事了。
