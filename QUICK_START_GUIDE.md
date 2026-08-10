# 🚀 SmartAsk 服务器运维 - 小白完全手册

> **适用人群：** 不熟悉Linux命令的新手 / 偶尔需要维护服务器的非运维人员
>
> **使用场景：** 日常更新代码、重启服务、查看日志、修改配置、故障排查
>
> **预计阅读时间：** 10分钟（建议收藏，用的时候随时查阅）

---

## 📖 本文档包含什么？

| 章节 | 内容 | 适用场景 |
|------|------|----------|
| **[三步快速更新](#-三步快速更新最常用的操作)** | 最常用的更新命令 | 每次有新代码发布时 |
| **[五种常见操作](#-五种常见操作按需选用)** | 重启/查看日志/备份等 | 日常维护 |
| **[修改配置指南](#-修改配置指南env数据库ai模型)** | 改密码/换AI模型/调参数 | 需要调整系统配置时 |
| **[故障排查速查](#-故障排查速查表30秒定位问题)** | 各种报错的解决方案 | 出问题时紧急救火 |
| **[完整命令参考](#-完整命令参考表收藏这个)** | 所有命令的速查表 | 忘记命令时查询 |

**建议：先看「三步快速更新」，其他章节用到时再查。**

---

## ✅ 三步快速更新（最常用的操作）

这是你**最常用**的操作，每次开发人员说"新代码已推送"时就用这个。

### 📋 操作流程图

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐
│  第1步：登录  │ → │  第2步：执行命令   │ → │  第3步：验证   │
│  SSH连接服务器 │    │  一行命令搞定     │    │  浏览器打开测试 │
└─────────────┘    └─────────────────┘    └──────────────┘
     (30秒)            (2-5分钟)              (10秒)
```

---

### 第1️⃣ 步：SSH 登录服务器（30秒）

#### 如果你用的是图形化工具（推荐新手使用）

**推荐工具（任选一个）：**
- [XShell](https://www.netsarang.com/en/xshell/) （Windows，免费版够用）
- [FinalShell](http://www.hostbuf.com/) （国产，中文界面）
- [MobaXterm](https://mobaxterm.mobatek.net/) （功能强大）

**操作步骤：**
1. 打开 SSH 工具
2. 点击「新建连接」或「Session」
3. 填写信息：
   ```
   主机(Host)：BISubApp01 或你的服务器IP地址
   端口(Port)：22
   用户名(User)：root
   密码(Password)：你的服务器root密码
   ```
4. 点击「确定」或「Connect」连接

#### 如果你用的是命令行（Mac/Linux用户）

```bash
ssh root@BISubApp01
# 或者
ssh root@你的服务器IP
```

**输入密码后回车（输入时不会显示字符，这是正常的）**

#### ✅ 连接成功的标志

你会看到类似这样的提示符：
```
[root@BISubApp01 ~]#
```
**看到这个 `#` 符号就说明已经成功登录！可以继续下一步了。**

---

### 第2️⃣ 步：执行更新命令（2-5分钟）

**复制下面这整行命令，粘贴到终端里，然后按回车键：**

```bash
cd /opta/smartask && bash update.sh
```

**就这么简单！一行命令搞定所有事情！**

#### 🔍 你会看到的输出（正常情况）

脚本会自动执行以下步骤，**你只需要耐心等待**：

```
============================================================
  SmartAsk 自动更新脚本 v2.0
  时间: 2026-08-10 12:00:00
  分支: docker-setup
============================================================

✅ [1/5] 备份配置文件...
   [OK] 检测到密文主密钥文件
   ==> 更新前备份
   备份完成: /opta/smartask/backups/20260810_120000
   ✓ 已备份: config/*.json, .env, employee_permissions.json

⏳ [2/5] 拉取最新代码...
   ==> 拉取最新代码 (分支: docker-setup)
   Git pull: origin docker-setup
   From https://github.com/qishen123456/docker-setup
    * branch              docker-setup -> FETCH_HEAD
   Updating abc1234..def5678
   Fast-forward
    backend/app.py                    |   10 +-
    frontend/src/views/Login.vue      |   20 ++
    ...
   16 files changed, 3061 insertions(+), 713 deletions(-)

🐳 [3/5] 重建 Docker 容器...
   ==> 使用外部代理模式启动
   Building backend
   Step 1/15 : FROM python:3.11-slim
    ---> abc123def456
   ...
   Successfully built xyz789abc012
   Creating smartask-postgres ... done
   Creating smartask-backend  ... done
   Creating smartask-frontend ... done

✅ [4/5] 健康检查...
   ==> 等待后端就绪... (最多等待60秒)
   [OK] 后端健康检查通过 (耗时3秒)

🎉 [5/5] 全部完成！

============================================================
  更新结果汇总
============================================================
  ✅ 配置文件已备份到: backups/20260810_120000
  ✅ 代码已更新到最新版本 (commit: def5678)
  ✅ Docker 容器已重建并启动
  ✅ 后端健康检查通过

  用户访问地址: https://bifine.angelgroup.com.cn:10899/smart-ask/
  更新时间: 2026-08-10 12:05:30

  💡 提示：如果遇到问题，可以从备份目录恢复配置文件
============================================================
```

**看到最后一行"全部完成"和访问地址，就说明成功了！**

---

### 第3️⃣ 步：验证是否成功（10秒）

**在你的电脑浏览器中打开：**

```
https://bifine.angelgroup.com.cn:10899/smart-ask/
```

**判断标准：**
- ✅ **成功：** 能看到登录页面（显示用户名/密码输入框或飞书登录按钮）
- ❌ **失败：** 显示 502/504 错误、白屏、或者无法访问

**如果能看到登录页面，恭喜你！更新完成！🎉 可以收工了！**

---

## ⚙️ 五种常见操作（按需选用）

除了更新代码，你可能还需要这些操作。

### 操作1️⃣：只重启不更新代码（改了配置时用）

**场景：** 你修改了 `.env` 文件中的配置（比如换了AI模型的API Key），想让新配置生效，但不需要更新代码。

**命令：**
```bash
cd /opta/smartask && bash update.sh --no-pull
```

**效果：**
- 跳过 Git 拉取代码
- 直接重建 Docker 容器
- 让新的配置生效

**适用场景举例：**
- 换了 DeepSeek 的 API Key
- 修改了管理员密码
- 调整了飞书应用的 App Secret
- 修改了数据库密码（不推荐频繁改）

---

### 操作2️⃣：查看实时日志（排查问题时用）

**场景：** 系统出问题了（比如提问报错、登录失败），想看看后端发生了什么。

**命令：**
```bash
docker logs -f smartask-backend
```

**效果：**
- 实时显示后端的运行日志
- 新的日志会不断滚动显示在屏幕上
- 按 `Ctrl + C` 可以退出

**常用参数：**
```bash
# 只看最后50行（不看实时滚动）
docker logs smartask-backend --tail 50

# 看最后100行，并持续跟踪新日志
docker logs -f smartask-backend --tail 100

# 查看前端的日志
docker logs -f smartask-frontend

# 查看某个时间点之后的日志（比如最近1小时）
docker logs --since 1h smartask-backend
```

**日志里的关键信息：**
```
# 正常的请求日志
[INFO] 2026-08-10 12:00:00 - POST /api/chat - 200 OK - 2.3s

# 报错日志（重点关注 ERROR 字样）
[ERROR] 2026-08-10 12:01:00 - AI model API error: Invalid API Key
[ERROR] 2026-08-10 12:02:00 - Database connection failed
```

---

### 操作3️⃣：查看服务状态（日常巡检用）

**场景：** 想确认系统是否正常运行，所有容器是否健康。

**命令：**
```bash
cd /opta/smartask && docker-compose ps
```

**效果示例：**
```
NAME                STATUS                      PORTS
smartask-backend    Up (healthy)                 5002/tcp        ← ✅ 正常
smartask-frontend   Up (healthy)                 80/tcp, 8888/tcp ← ✅ 正常
smartask-postgres   Up (healthy)                 5432/tcp, 5433/tcp ← ✅ 正常
```

**状态说明：**
| 状态 | 含义 | 是否正常 |
|------|------|----------|
| `Up (healthy)` | 运行中且健康检查通过 | ✅ 正常 |
| `Up` | 运行中（还没做健康检查或没配置） | ⚠️ 一般正常 |
| `Exit (0)` | 正常退出 | ⚠️ 可能是配置问题 |
| `Exit (1)` | 异常退出（报错退出） | ❌ 有问题 |
| `Restarting` | 反复重启 | ❌ 肯定有问题 |

**如果看到 `Restarting` 或 `Exit (1)`，立即查看日志：**
```bash
docker logs smartask-backend --tail 50
```

---

### 操作4️⃣：备份数据库（定期备份用）

**场景：** 担心数据丢失，想定期备份数据库（建议每周至少一次）。

**命令：**
```bash
cd /opta/smartask && docker exec smartask-postgres pg_dump -U smartask_user smartask_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

**效果：**
- 在当前目录生成一个 SQL 文件，例如：`backup_20260810_120000.sql`
- 这个文件包含了完整的数据库数据

**恢复备份的方法（如果真的需要恢复）：**
```bash
# 先停止服务
docker-compose down

# 清空并导入备份
docker exec -i smartask-postgres psql -U smartask_user smartask_db < backup_20260810_120000.sql

# 重新启动
docker-compose up -d
```

**自动备份脚本（可选）：**
如果想每天自动备份，可以设置 crontab：
```bash
# 编辑定时任务
crontab -e

# 添加这一行（每天凌晨3点自动备份）
0 3 * * * cd /opta/smartask && docker exec smartask-postgres pg_dump -U smartask_user smartask_db > backups/db_backup_$(date +\%Y\%m\%d).sql
```

---

### 操作5️⃣：停止/启动服务（维护时用）

**场景：** 需要停机维护、升级服务器、或者释放资源。

**停止所有服务：**
```bash
cd /opta/smartask && docker-compose down
```

**启动所有服务：**
```bash
cd /opta/smartask && docker-compose up -d
```

**只重启某个服务（比如只重启后端）：**
```bash
cd /opta/smartask && docker-compose restart backend
```

**⚠️ 注意：**
- 停止服务期间，用户将无法访问系统
- 建议提前通知用户（如果有的话）
- 启动后记得验证服务是否正常（浏览器打开测试一下）

---

## 🔧 修改配置指南（.env/数据库/AI模型）

有时候你需要修改系统的配置。这里教你如何安全地修改。

### 场景1️⃣：更换 AI 模型或 API Key

**什么时候需要：**
- API Key 泄露或过期
- 想换个更便宜的 AI 服务商
- 想试试不同的模型（比如从 gpt-4o 换成 deepseek-chat）

**操作步骤：**

1. **编辑 .env 文件**
   ```bash
   cd /opta/smartask
   vi .env
   ```

2. **找到这部分配置（大约在第50-55行）**
   ```ini
   # ====== AI模型配置 ======
   SMARTASK_AI_API_KEY=sk-your-old-api-key          # ← 改这里
   SMARTASK_AI_BASE_URL=https://api.old-provider.com/v1/  # ← 改这里
   SMARTASK_AI_MODEL=old-model-name                  # ← 改这里
   ```

3. **修改为新的值（以 DeepSeek 为例）**
   ```ini
   SMARTASK_AI_API_KEY=sk-new-deepseek-key-xxxxx
   SMARTASK_AI_BASE_URL=https://api.deepseek.com/v1/
   SMARTASK_AI_MODEL=deepseek-chat
   ```

4. **保存退出**（vi 编辑器：按 `Esc`，输入 `:wq`，回车）

5. **重启服务使配置生效**
   ```bash
   bash update.sh --no-pull
   ```

6. **测试新模型是否工作**
   - 登录系统
   - 提一个问题
   - 看是否能正常返回答案

---

### 场景2️⃣：修改管理员密码

**什么时候需要：**
- 首次部署后必须修改默认密码
- 密码泄露或忘记密码
- 定期更换密码（安全最佳实践）

**操作步骤：**

1. **编辑 .env 文件**
   ```bash
   vi .env
   ```

2. **找到这部分（大约第38行）**
   ```ini
   SMARTASK_ADMIN_PASSWORD=YourAdminPasswordHere_ChangeImmediately
   ```

3. **改成强密码**
   ```ini
   SMARTASK_ADMIN_PASSWORD=MyNewSecure@Password2026!
   ```

4. **保存并重启**
   ```bash
   :wq  # 保存退出 vi
   bash update.sh --no-pull  # 重启生效
   ```

5. **用新密码登录测试**

**密码强度要求：**
- 至少12位（推荐20位以上）
- 包含大小写字母
- 包含数字
- 包含特殊字符（!@#$%^&*）
- 不要用生日、手机号、姓名等容易猜到的信息

---

### 场景3️⃣：修改数据库密码

**⚠️ 高危操作！除非必要不要轻易修改！**

**什么时候需要：**
- 首次部署时设置强密码
- 发现密码泄露
- 安全审计要求定期更换

**操作步骤：**

1. **先备份数据库（重要！）**
   ```bash
   docker exec smartask-postgres pg_dump -U smartask_user smartask_db > before_password_change.sql
   ```

2. **编辑 .env，修改这两个地方**
   ```bash
   vi .env
   ```
   ```ini
   SMARTASK_DB_PASSWORD=NewStrongPasswordHere1234567890
   SMARTASK_POSTGRES_PASSWORD=NewStrongPasswordHere1234567890
   ```

3. **保存并完全重建容器**
   ```bash
   :wq
   docker-compose down                          # 停止所有容器
   docker volume rm smartask-new_smartask_pg_data  # 删除旧的数据库卷（⚠️ 数据会丢失！）
   docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build  # 重新创建
   ```

4. **恢复数据（如果有备份的话）**
   ```bash
   # 等待PostgreSQL容器完全启动（约10秒）
   sleep 10

   # 导入备份
   docker exec -i smartask-postgres psql -U smartask_user smartask_db < before_password_change.sql
   ```

5. **测试系统能否正常运行**

**⚠️ 警告：** 如果没有备份且删除了数据库卷，数据将无法恢复！

---

### 场景4️⃣：修改飞书应用配置

**什么时候需要：**
- 更换飞书应用
- App Secret 过期或泄露
- 修改回调URL

**操作步骤：**

1. **编辑 .env**
   ```bash
   vi .env
   ```

2. **修改飞书相关配置（大约在第75-80行）**
   ```ini
   SMARTASK_FEISHU_APP_ID=cli_new_app_id_here
   SMARTASK_FEISHU_APP_SECRET=new_app_secret_here
   FEISHU_REDIRECT_URI=https://your-domain:port/smart-ask/api/auth/feishu/callback
   FEISHU_FRONTEND_CALLBACK_URL=https://your-domain:port/smart-ask
   ```

3. **保存并重启**
   ```bash
   :wq
   bash update.sh --no-pull
   ```

4. **重要：同步更新飞书开放平台！**
   - 登录 https://open.feishu.cn/app
   - 选择你的应用
   - 进入「安全设置」
   - 修改「重定向 URL」为新的值（必须和 .env 完全一致！）
   - 进入「版本管理与发布」
   - 创建新版本并发布（否则配置不生效！）

5. **测试飞书登录功能**

---

## 🆘 故障排查速查表（30秒定位问题）

遇到问题？对照下面的表格快速找到解决方案。

### 🔴 紧急问题（网站打不开）

| 现象 | 可能原因 | 快速诊断命令 | 解决方案 |
|------|---------|-------------|---------|
| **浏览器显示 502 Bad Gateway** | 后端容器挂了 | `docker ps -a \| grep backend` | 查看 `docker logs smartask-backend --tail 50` 找原因 |
| **浏览器显示 504 Gateway Timeout** | 后端响应太慢 | `docker logs --since 5m smartask-backend` | 检查是否有慢查询或死锁 |
| **浏览器白屏（无任何内容）** | 前端构建失败或Nginx配置错误 | `curl -I http://localhost:8888/` | 检查前端容器状态和 Nginx 配置 |
| **浏览器显示"无法访问此网站"** | Nginx未启动或防火墙拦截 | `nginx -t && netstat -tlnp \| grep :10899` | 启动 Nginx 或检查防火墙规则 |
| **连接超时** | 服务器宕机或网络不通 | `ping your-server-ip` | 检查服务器是否开机、网络是否通畅 |

### 🟡 功能异常（网站能打开但功能不对）

| 现象 | 可能原因 | 快速诊断命令 | 解决方案 |
|------|---------|-------------|---------|
| **登录失败（提示密码错误）** | 密码改了但没生效 | `grep ADMIN_PASSWORD .env` | 执行 `bash update.sh --no-pull` 重启 |
| **飞书登录提示"state校验失败"** | 回调URL不匹配 | `grep FEISHU_REDIRECT_URI .env` | 对比飞书平台配置，确保完全一致 |
| **提问时报错"API Key无效"** | AI模型API Key错误或过期 | `grep AI_API_KEY .env` | 检查Key是否正确，是否充值/激活 |
| **提问后一直转圈无响应** | AI服务商API挂了或网络不通 | `curl -X POST ${SMARTASK_AI_BASE_URL}/chat/completions ...` | 检查AI服务商状态，尝试换模型 |
| **SSE流式输出卡住** | Nginx开启了缓冲 | `grep proxy_buffering /etc/nginx/conf.d/smartask.conf` | 确认设置为 `off` |

### 🟢 运维问题（更新/部署相关）

| 现象 | 可能原因 | 快速诊断命令 | 解决方案 |
|------|---------|-------------|---------|
| **Git拉取失败（connection refused）** | GitHub被墙或网络不通 | `ping github.com` | 用代理或手动上传代码包 |
| **Docker构建失败（timeout）** | 镜像下载超时（国内常见） | `df -h` 检查磁盘空间 | 配置Docker镜像加速（见.env第九部分） |
| **容器反复Restarting** | .env配置有误 | `docker logs smartask-backend --tail 100` | 检查日志中的具体报错信息 |
| **端口被占用（port already allocated）** | 其他程序占用了5002/8888 | `netstat -tlnp \| grep -E '(5002\|8888)'` | 停止占用端口的程序或改端口 |
| **磁盘空间不足（No space left）** | 日志或镜像太多 | `df -h` | `docker system prune -a` 清理空间 |

### 🔵 数据问题（数据丢失或不一致）

| 现象 | 可能原因 | 快速诊断命令 | 解决方案 |
|------|---------|-------------|---------|
| **用户数据丢失** | 误删数据库或容器 | `docker exec smartask-postgres psql -l` | 从备份恢复（见操作4️⃣） |
| **配置被重置** | update.sh备份恢复逻辑出错 | `ls -lt backups/ \| head -5` | 手动从备份复制配置文件 |
| **权限配置丢失** | employee_permissions.json被覆盖 | `cat config/employee_permissions.json` | 从备份恢复该文件 |

---

## 📋 完整命令参考表（收藏这个）

把这一页加书签，随时查阅。

### 日常运维

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **更新代码+重启** | `cd /opta/smartask && bash update.sh` | 最常用！一键搞定 |
| **只重启（不改代码）** | `bash update.sh --no-pull` | 改了配置后用 |
| **跳过备份直接更新** | `bash update.sh --skip-backup` | 不推荐生产环境 |
| **指定分支更新** | `bash update.sh --branch main` | 默认是docker-setup |

### 服务管理

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **查看所有容器状态** | `docker-compose ps` | 显示运行状态和端口 |
| **启动所有服务** | `docker-compose up -d` | -d 表示后台运行 |
| **停止所有服务** | `docker-compose down` | 会停止并删除容器 |
| **重启某个服务** | `docker-compose restart backend` | 可指定 backend/frontend/postgres |
| **重启所有服务** | `docker-compose restart` | 一次性重启全部 |

### 日志查看

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **看后端实时日志** | `docker logs -f smartask-backend` | Ctrl+C 退出 |
| **看后端最后50行** | `docker logs smartask-backend --tail 50` | 不跟踪新日志 |
| **看前端日志** | `docker logs -f smartask-frontend` | 同上 |
| **看最近1小时的日志** | `docker logs --since 1h smartask-backend` | 按时间过滤 |
| **看包含ERROR的日志** | `docker logs smartask-backend 2>&1 \| grep ERROR` | 只看错误 |

### 备份恢复

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **备份数据库** | `docker exec smartask-postgres pg_dump -U smartask_user smartask_db > backup.sql` | 完整备份 |
| **恢复数据库** | `docker exec -i smartask-postgres psql -U smartask_user smartask_db < backup.sql` | 会覆盖现有数据 |
| **查看现有备份** | `ls -lh *.sql` 或 `ls -lt backups/` | 列出备份文件 |
| **备份配置文件** | `cp -r config/ backups/config_$(date +%Y%m%d)/` | 备份config目录 |

### 系统诊断

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **检查磁盘空间** | `df -h` | Use% 接近100%要清理 |
| **检查内存使用** | `free -h` | 看可用内存 |
| **检查Docker占用** | `docker system df` | 看镜像/容器/卷的大小 |
| **清理Docker无用资源** | `docker system prune -a` | ⚠️ 会删除停止的容器和未使用的镜像 |
| **检查端口占用** | `netstat -tlnp \| grep :5002` | 看5002端口谁在用 |
| **测试后端健康** | `curl http://localhost:5002/api/health` | 应返回 {"status":"ok"} |
| **测试前端可访问** | `curl -I http://localhost:8888/` | 应返回 HTTP/1.1 200 OK |

### Git 相关

| 我想要... | 执行这条命令 | 说明 |
|---------|-------------|------|
| **查看当前分支** | `git branch` | 应该显示 * docker-setup |
| **查看最近的提交** | `git log --oneline -5` | 看最近5次提交 |
| **查看未提交的改动** | `git status` | 看哪些文件被修改了 |
| **放弃本地改动** | `git checkout -- .` | ⚠️ 不可恢复！ |
| **回退到上一版本** | `git reset --hard HEAD~1` | ⚠️ 会丢失改动！ |

---

## 🆘 紧急情况处理（救火指南）

### 情况1：更新后网站打不开，想立即回滚

**目标：** 恢复到更新前的状态

**操作步骤（3分钟内恢复）：**

```bash
# 1. 查看最新的备份目录（通常在 backups/ 下）
ls -lt /opta/smartask/backups/runtime_config_* | head -1
# 输出示例：backups/runtime_config_before_pull_20260810_120000

# 2. 从备份恢复配置文件
cp /opta/smartask/backups/runtime_config_before_pull_20260810_120000/*.json /opta/smartask/config/

# 3. 如果还备份了 .env，也恢复它
cp /opta/smartask/backups/runtime_config_before_pull_20260810_120000/.env /opta/smartask/.env

# 4. 回退代码到上一个版本
git log --oneline -3  # 查看最近的3个版本
git reset --hard abc1234  # 回退到更新前的版本号

# 5. 重建容器
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build

# 6. 验证恢复成功
curl http://localhost:5002/api/health
```

**网站应该能在3分钟内恢复！**

---

### 情况2：完全搞不定，需要找别人帮忙

**目标：** 收集完整的错误信息发给运维同事或技术支持

**收集信息的命令（一键执行）：**

```bash
# 创建诊断信息文件
cat > /tmp/smartask_diagnosis.txt << 'EOF'
========== SmartAsk 诊断信息 ==========
采集时间: $(date)

【1. 系统信息】
$(uname -a)
$(cat /etc/os-release | head -5)

【2. Docker 信息】
$(docker --version)
$(docker-compose version)

【3. 当前目录和Git状态】
当前目录: $(pwd)
Git分支: $(git branch --show-current)
Git状态:
$(git status --short)

【4. 容器状态】
$(docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}")

【5. 最近的后端日志（最后50行）】
$(docker logs smartask-backend --tail 50 2>&1)

【6. Nginx 配置（如果存在）】
$(cat /etc/nginx/conf.d/smartask.conf 2>/dev/null || echo "Nginx配置文件不存在")

【7. 磁盘空间】
$(df -h /)

【8. 内存使用】
$(free -h)

【9. 端口监听情况】
$(netstat -tlnp 2>/dev/null | grep -E '(5002|8888|10899)' || echo "netstat不可用")
==========================================
EOF

echo "诊断信息已保存到: /tmp/smartask_diagnosis.txt"
echo "请把这个文件发给技术支持"
```

**然后把 `/tmp/smartask_diagnosis.txt` 发给你的运维同事或技术支持。**

---

### 情况3：怀疑被黑客入侵或数据泄露

**立即行动（按顺序执行）：**

1. **立即断网（物理拔网线或关闭网卡）**
   ```bash
   ifdown eth0  # 或你的网卡名称
   ```

2. **保留现场（不要重启或清理！）**
   ```bash
   # 复制所有日志到安全位置
   mkdir -p /tmp/incident_$(date +%Y%m%d_%H%M%S)
   cp -r /var/log/* /tmp/incident_*/
   docker logs smartask-backend > /tmp/incident_*/backend.log
   docker logs smartask-frontend > /tmp/incident_*/frontend.log
   ```

3. **快照虚拟机（如果是VMware/KVM/云主机）**

4. **联系安全团队或报警**

5. **修改所有密码**（在确认安全后）
   - 服务器root密码
   - 数据库密码
   - 管理员密码
   - AI模型API Key
   - 飞书应用Secret

---

## 📚 相关文档索引

| 文档名 | 用途 | 阅读难度 |
|--------|------|----------|
| **本文档** | 日常运维、故障排查 | ⭐ 小白友好 |
| [DEPLOY_QUICK.md](./DEPLOY_QUICK.md) | 从零开始首次部署（5分钟版） | ⭐ 小白友好 |
| [DEPLOY_TO_SERVER.md](./DEPLOY_TO_SERVER.md) | 完整部署指南（含详细原理解释） | ⭐⭐ 需要一定基础 |
| [.env.example](./.env.example) | 配置文件模板（含所有配置项注释） | ⭐⭐ 配置时参考 |
| [update.sh](./update.sh) | 更新脚本的源代码 | ⭐⭐⭐ 开发者用 |

---

## 🎯 核心要点总结（记住这就够了）

### 日常操作（90%的情况只需要这些）

1. **更新代码：** `cd /opta/smartask && bash update.sh`
2. **改配置后重启：** `bash update.sh --no-pull`
3. **看日志排错：** `docker logs -f smartask-backend --tail 100`
4. **确认服务正常：** `docker-compose ps` （全是 Up 就没问题）

### 遇到问题的思路

1. **先看日志** → 找到具体的报错信息
2. **再查文档** → 对照本文档的「故障排查速查表」
3. **试着重启** → 很多小问题重启就能解决
4. **不行就回滚** → 从 `backups/` 目录恢复配置
5. **实在搞不定** → 收集诊断信息找帮忙

### 安全注意事项

- **不要**把 .env 文件（含密码和API Key）发给别人或提交到Git
- **定期**修改密码（建议每季度一次）
- **经常**备份数据库（建议每天或每周）
- **及时**更新代码（修复安全漏洞）

---

## 💬 还是有问题？

如果你按照本文档操作还是遇到问题：

1. **仔细阅读报错信息**（很多时候答案就在报错里）
2. **Google/Baidu搜索报错关键词**（大概率别人也遇到过）
3. **查看项目的 GitHub Issues**（可能是已知问题）
4. **收集完整诊断信息后找人帮忙**（见上面的「情况2」）

---

**最后更新：** 2026-08-10
**适用对象：** Linux新手 / 偶尔需要维护服务器的非运维人员
**文档版本：** v2.0（大幅增强版，新增配置修改指南和故障排查速查表）

**祝你运维顺利！有问题多看日志，大部分都能解决！💪**
