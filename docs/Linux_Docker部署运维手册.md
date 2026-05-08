# Linux Docker 部署运维手册

本文档只解决一件事：Linux 服务器如何部署、启动、更新、检查 SmartAsk。

如果你关心“Windows 测试环境改完后，如何发布到 Linux 正式环境，并保护数据源、数据集、提示词不丢”，请看：

```text
docs/迁移发布与运行态配置保护方案.md
```

## 1. 服务器要求

Linux 服务器需要安装：

- Git。
- Docker Engine。
- Docker Compose Plugin。

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

## 2. 拉取正确分支

完整项目目前在 Gitee 的 `docker-setup` 分支。

不要只执行：

```bash
git clone https://gitee.com/tailin1/volcano-intelligent-questions.git
```

这可能只拉到默认分支，导致只看到 README。

应该执行：

```bash
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
```

## 3. 首次部署

### 3.1 准备 .env

```bash
cp .env.example .env
nano .env
```

必须修改：

```text
SMARTASK_SECRET_KEY
SMARTASK_AI_API_KEY
SMARTASK_ADMIN_PASSWORD
```

生产环境不要使用示例密码。

### 3.2 启动

```bash
docker compose up -d --build
```

### 3.3 检查状态

```bash
docker compose ps
curl http://localhost:5002/api/health
```

后端健康检查正常时，应看到类似：

```json
{"status":"running"}
```

### 3.4 访问系统

默认前端地址：

```text
http://服务器IP:8080
```

如果是本机访问：

```text
http://localhost:8080
```

如服务器启用了防火墙，需要开放端口：

```bash
sudo ufw allow 8080/tcp
sudo ufw allow 5002/tcp
```

云服务器还需要在安全组里开放端口。

## 4. 日常启动、停止、重启

### 4.1 启动

```bash
docker compose up -d
```

### 4.2 停止

```bash
docker compose stop
```

### 4.3 重启

```bash
docker compose restart
```

### 4.4 查看日志

```bash
docker compose logs -f backend
```

查看最近 200 行：

```bash
docker compose logs --tail=200 backend
```

## 5. 日常更新代码

进入项目目录：

```bash
cd smartask
```

拉取最新代码：

```bash
git pull --ff-only
```

重建并启动：

```bash
docker compose up -d --build
```

检查：

```bash
docker compose ps
curl http://localhost:5002/api/health
```

如果页面仍显示旧样式，浏览器强制刷新：

```text
Ctrl + F5
```

## 6. 常用端口

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

如需修改端口，改 `.env` 后重新启动：

```bash
docker compose up -d
```

## 7. 数据保存在哪里

Docker 部署时，重要数据不在容器临时文件里，而在 volume 或挂载目录里。

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

环境变量：

```text
项目目录/.env
```

## 8. 禁止误操作

正式环境不要随便执行：

```bash
docker compose down -v
```

原因：

- `down` 会停止并删除容器。
- `-v` 会删除 Docker volume。
- PostgreSQL 数据在 `smartask_pg_data`。
- Chroma 数据在 `smartask_chroma`。

如果执行了 `docker compose down -v`，正式数据库可能被删除。

安全更新代码应使用：

```bash
git pull --ff-only
docker compose up -d --build
```

## 9. 最小备份命令

正式环境更新前，至少执行：

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U postgres -d postgres > backups/smartask_pg_$(date +%Y%m%d_%H%M%S).sql
tar -czf backups/smartask_config_$(date +%Y%m%d_%H%M%S).tar.gz config
git rev-parse HEAD > backups/git_commit_$(date +%Y%m%d_%H%M%S).txt
```

如果 `.env` 中数据库用户名或库名不是 `postgres`，需要替换 `-U postgres -d postgres`。

## 10. 基础恢复命令

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

## 11. 故障排查

### 11.1 后端不健康

```bash
docker compose logs --tail=200 backend
```

### 11.2 数据库不健康

```bash
docker compose logs --tail=200 postgres
docker compose ps
```

### 11.3 前端打不开

```bash
docker compose logs --tail=200 frontend
docker compose ps
```

确认端口：

```bash
ss -lntp | grep 8080
```

### 11.4 页面还是旧版本

```bash
docker compose up -d --build
```

浏览器：

```text
Ctrl + F5
```

## 12. 给服务器管理员的简版命令

### 首次部署

```bash
git clone -b docker-setup https://gitee.com/tailin1/volcano-intelligent-questions.git smartask
cd smartask
cp .env.example .env
nano .env
docker compose up -d --build
docker compose ps
curl http://localhost:5002/api/health
```

### 日常更新

```bash
cd smartask
git pull --ff-only
docker compose up -d --build
docker compose ps
curl http://localhost:5002/api/health
```

### 更新前备份

```bash
cd smartask
mkdir -p backups
docker compose exec -T postgres pg_dump -U postgres -d postgres > backups/smartask_pg_$(date +%Y%m%d_%H%M%S).sql
tar -czf backups/smartask_config_$(date +%Y%m%d_%H%M%S).tar.gz config
```

### 禁止命令

```bash
docker compose down -v
```

除非你明确要删除数据库，否则不要执行。
