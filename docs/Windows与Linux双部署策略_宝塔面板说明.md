# Windows 与 Linux 双部署策略：宝塔面板场景说明

更新时间：2026-05-08

本文档回答三个问题：

- 当前一键 Docker 部署到底是 Windows 还是 Linux？
- 阿里云宝塔面板上部署后“前端按钮全部点击失效”可能是什么原因？
- 如果 Windows 用户机和 Linux/宝塔服务器都要保留，后续应该怎么设计部署体系？

## 1. 结论

当前项目的 Docker 编排文件 `docker-compose.yml` 是跨平台的，Windows 和 Linux 都能使用。

但现有一键脚本分两类：

- Windows 用户机：主要使用 `deploy.ps1`、`update.ps1`、`doctor.ps1`、`backup.ps1`。
- Linux / 宝塔服务器：目前推荐直接使用 `docker compose` 命令，已新增 `doctor.sh` 用于诊断；后续应补齐 `deploy.sh`、`update.sh`、`backup.sh`、`restore.sh`。

所以不是“之前 Docker 只能 Windows”，而是“之前一键脚本主要服务 Windows；Linux 现在需要独立脚本和独立手册”。

## 2. 端口与访问方式

Docker 正式部署后，前端默认访问：

```text
http://服务器IP:8080
```

开发机本地 Vite 才使用：

```text
http://localhost:5173
```

当前 `docker-compose.yml` 中前端容器映射为：

```yaml
frontend:
  ports:
    - "${SMARTASK_FRONTEND_PORT:-8080}:80"
```

也就是说：

- 容器内 Nginx 监听 `80`。
- 宿主机默认暴露 `8080`。
- 如果 `.env` 里设置 `SMARTASK_FRONTEND_PORT=5173`，也可以改成 `5173`，但不建议生产/用户机这么做。

## 3. 宝塔面板不是根因，但可能影响访问链路

宝塔面板本身一般不会让前端按钮全部失效。

“所有按钮点击都失效”更常见于以下几类原因：

### 3.1 前端 JS 没有正确加载

表现：

- 页面样式出来了。
- 按钮看得见，但点击没反应。
- 浏览器控制台出现 `Failed to load module script`、`404 assets/*.js`、`MIME type`、`Unexpected token <` 等错误。

常见原因：

- 宝塔站点反向代理配置错了。
- 静态资源路径被宝塔/Nginx 改写。
- 访问的不是 Docker 前端容器，而是宝塔站点目录里的旧静态文件。
- 浏览器缓存了旧版本前端。

排查：

```bash
curl -I http://127.0.0.1:8080
curl -I http://127.0.0.1:8080/assets/
docker compose logs --tail=200 frontend
```

浏览器按 `F12`，查看 Console 和 Network。

### 3.2 `/api` 反向代理没有打到后端

当前前端代码使用相对路径：

```js
baseURL: '/api'
```

Docker 前端 Nginx 已配置：

```nginx
location /api/ {
  proxy_pass http://backend:5002/api/;
}
```

如果用户直接访问 Docker 前端 `http://服务器IP:8080`，这条链路是正常的。

如果用户通过宝塔新建站点或域名反向代理访问，例如：

```text
https://ask.example.com
```

宝塔 Nginx 必须把请求完整转发到 Docker 前端：

```text
ask.example.com -> 127.0.0.1:8080
```

不要把 `/api` 单独代理到错误端口，也不要把站点根目录指向旧 `dist`。

排查：

```bash
curl http://127.0.0.1:5002/api/health
curl http://127.0.0.1:8080/api/health
curl http://你的域名/api/health
```

三个都应该能返回健康状态。

### 3.3 宝塔安全、防火墙或反向代理拦截了 SSE

智能问数过程使用流式接口：

```text
/api/smart-chat/stream
/api/smart-chat/confirm-by-boss/stream
```

如果普通按钮可点，但问数过程卡住、实时输出不动，可能是 SSE 被代理缓冲。

Docker 前端 Nginx 已设置：

```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
```

如果外层还有宝塔反向代理，也需要确保不要对这些流式接口启用缓冲。

## 4. 宝塔面板推荐部署方式

### 4.1 推荐架构

宝塔只做入口管理和 SSL：

```text
用户浏览器
  -> 宝塔 Nginx / 域名 / SSL
  -> 127.0.0.1:8080
  -> Docker frontend nginx
  -> /api 代理到 Docker backend
  -> Docker postgres
```

不要让宝塔直接托管 `frontend/dist`，除非你明确维护一套非 Docker 静态部署方案。

### 4.2 宝塔反向代理目标

在宝塔网站中配置反向代理：

```text
目标 URL：http://127.0.0.1:8080
```

然后访问：

```text
https://你的域名
```

不要代理到：

```text
http://127.0.0.1:5173
```

因为 `5173` 是开发服务，不是 Docker 正式前端。

## 5. 两套部署同时保留的设计

建议明确分成三层：

### 5.1 公共 Docker 编排层

保留一份核心：

```text
docker-compose.yml
frontend/Dockerfile
backend/Dockerfile
frontend/nginx.conf
.env.example
```

这部分必须跨平台，Windows 和 Linux 共用。

### 5.2 Windows 用户机脚本层

保留：

```text
deploy.ps1
update.ps1
backup.ps1
doctor.ps1
reset.ps1
```

用途：

- 给不懂命令行的 Windows 用户机一键部署。
- 使用 Docker Desktop。
- 默认访问 `http://localhost:8080`。

### 5.3 Linux / 宝塔服务器脚本层

后续新增：

```text
deploy.sh
update.sh
backup.sh
restore.sh
doctor.sh
```

用途：

- 给阿里云、宝塔、Ubuntu、Debian、CentOS 服务器使用。
- 使用 Docker Engine + Docker Compose Plugin。
- 支持自动检查 Docker、Git、端口、防火墙提示、健康检查和诊断包。

目前已经新增：

```text
doctor.sh
deploy.sh
update.sh
backup.sh
restore.sh
check-release.sh
```

对应用途：

```text
deploy.sh         Linux 首次部署
update.sh         Linux 日常更新
backup.sh         Linux 备份 PG、config、.env、commit
restore.sh        Linux 按备份恢复，必须 --confirm
doctor.sh         Linux 诊断包
check-release.sh  发布前检查
```

## 6. 建议的目录与文档结构

建议后续文档拆成：

```text
docs/SmartAsk_部署与交付手册.md
docs/Windows_Docker用户机部署手册.md
docs/Linux_Docker部署运维手册.md
docs/宝塔面板部署说明.md
docs/迁移发布与运行态配置保护方案.md
```

其中：

- `SmartAsk_部署与交付手册.md`：总入口。
- `Windows_Docker用户机部署手册.md`：只讲 PowerShell。
- `Linux_Docker部署运维手册.md`：只讲 Linux 命令。
- `宝塔面板部署说明.md`：只讲宝塔反向代理、SSL、防火墙和诊断。
- `迁移发布与运行态配置保护方案.md`：只讲数据源、数据集、提示词、权限配置如何迁移和回滚。

## 7. 宝塔现场排查清单

让用户先执行：

```bash
cd smartask
bash doctor.sh
```

如果怀疑构建失败：

```bash
cd smartask
bash doctor.sh --with-build-log
```

然后让用户提供：

- `diagnostics/smartask_linux_diagnose_时间戳.zip`
- 浏览器 Console 截图。
- 浏览器 Network 中失败请求截图。
- 宝塔反向代理配置截图。

手动快速检查：

```bash
cd smartask
git branch -vv
git rev-parse HEAD
docker compose ps
docker compose logs --tail=200 frontend
docker compose logs --tail=200 backend
curl http://127.0.0.1:5002/api/health
curl http://127.0.0.1:8080/api/health
curl -I http://127.0.0.1:8080
```

如果用了域名：

```bash
curl -I https://你的域名
curl https://你的域名/api/health
```

## 8. 对“按钮全部失效”的初步判断

在没有诊断包和浏览器控制台前，不建议直接改代码。

优先怀疑：

1. 用户访问了错误入口，例如访问宝塔静态站点而不是 Docker 前端 `8080`。
2. 静态资源 JS 加载失败。
3. 宝塔反向代理没有完整转发到 `127.0.0.1:8080`。
4. `/api` 被宝塔代理到了错误位置。
5. 用户机拉到的代码不是 `docker-setup` 分支最新提交。
6. 前端构建时漏文件，例如之前的 `TypewriterLine.vue` 没进 Git。

应先收集诊断包和控制台错误，再决定是否改代码。

## 9. 后续改造计划

第一阶段：不改业务代码，只增强 Linux 可观测性。

- 已新增 `doctor.sh`。
- 文档补充宝塔排查路径。
- 明确用户访问 `8080`，开发访问 `5173`。

第二阶段：补齐 Linux 一键脚本。

- 已新增 `deploy.sh`：首次部署。
- 已新增 `update.sh`：备份、拉代码、重建、健康检查。
- 已新增 `backup.sh`：备份 PG、config、.env、当前 commit。
- 已新增 `restore.sh`：按备份恢复，必须显式 `--confirm`。

第三阶段：宝塔专项文档。

- 宝塔 Docker 部署方式。
- 宝塔反向代理方式。
- SSL 配置。
- 防火墙和安全组端口。
- SSE 流式接口代理设置。

第四阶段：CI/发布检查。

- 已新增 `check-release.sh`：检查新文件是否被 `.gitignore` 误伤。
- 已新增 `check-release.sh`：检查重要新文件是否未 `git add`。
- 已新增 `check-release.sh`：检查前端 `npm run build`。
- 已新增 `check-release.sh`：检查 `docker compose config`。
- 已新增 `check-release.sh`：检查 Linux shell 脚本 LF 行尾。
