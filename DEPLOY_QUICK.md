# 🚀 5分钟快速部署指南（小白专用）

> **适用场景：** 在服务器上从零开始部署 SmartAsk
>
> **预计时间：** 5-10分钟
>
> **前提条件：** 服务器已安装 Docker 和 Nginx

---

## ✅ 开始前的准备（30秒自检）

在开始之前，请确认你的服务器已经安装了以下软件：

```bash
# 检查 Docker 是否安装
docker --version
# 预期输出：Docker version 20.x.x ...

# 检查 Docker Compose 是否安装
docker-compose --version
# 预期输出：docker-compose version 2.x.x ...

# 检查 Nginx 是否安装
nginx -v
# 预期输出：nginx version: 1.x.x ...
```

**如果提示"command not found"，说明还没安装。请先安装：**
- [Docker 安装教程](https://docs.docker.com/get-docker/)
- [Nginx 安装教程](https://nginx.org/en/docs/install.html)

---

## 📋 一键部署流程（复制粘贴就行！）

### 第1步：SSH 登录服务器（1分钟）

打开终端（或 XShell/FinalShell/MobaXterm），输入：

```bash
ssh root@BISubApp01
```

**看到 `[root@BISubApp01 ~]#` 提示符就说明登录成功了！**

---

### 第2步：创建项目目录并克隆代码（2分钟）

**复制粘贴这一整段命令：**

```bash
# 创建目录（如果不存在）
mkdir -p /opta/smartask && cd /opta/smartask

# 克隆代码仓库
git clone https://github.com/qishen123456/docker-setup.git .

# 切换到正确的分支
git checkout docker-setup
```

**预期输出：**
```
Cloning into '.'...
remote: Enumerating objects: done, ...
Receiving objects: 100% (xxxx/xxxx), xx.xx MiB | xx.xx MiB/s, done.
Branch 'docker-setup' set up to track remote branch 'docker-setup'.
Already on 'docker-setup'
```

---

### 第3步：配置 .env 文件（最关键！3分钟）

#### 3.1 复制配置模板

```bash
cp .env.production .env
```

#### 3.2 编辑配置文件

```bash
vi .env
```

**按 `i` 键进入编辑模式，然后找到以下关键配置项并修改：**

##### 🔴 必须修改的配置项（不改会出问题！）

```ini
# ====== 第24行左右：数据库密码（必须改成强密码！）======
# 原始值：SMARTASK_DB_PASSWORD=YourStrongPasswordHere_ReplaceThisWithRealPassword_AtLeast32Chars
# 改成：SMARTASK_DB_PASSWORD=Xk9#mP2$vL5@nQ8wR4tY7uI0oP3sA6dF9gH1jL5nQ8wR

# ====== 第38行左右：管理员密码（必须改！）======
# 原始值：SMARTASK_ADMIN_PASSWORD=YourAdminPasswordHere_ChangeImmediately
# 改成：SMARTASK_ADMIN_PASSWORD=Admin@2026SecurePassword12345678

# ====== 第50行左右：AI模型API Key（必须填你自己的！）======
# 原始值：SMARTASK_AI_API_KEY=sk-your-openai-api-key-here
# 改成：SMARTASK_AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  （填你真实的Key）

# ====== 第51行左右：AI模型Base URL（根据你使用的服务商修改）======
# 如果用 DeepSeek（推荐）：
SMARTASK_AI_BASE_URL=https://api.deepseek.com/v1/
SMARTASK_AI_MODEL=deepseek-chat

# 如果用 OpenAI：
# SMARTASK_AI_BASE_URL=https://api.openai.com/v1/
# SMARTASK_AI_MODEL=gpt-4o

# ====== 第65行左右：安全密钥（必须生成随机密钥！）======
# 先在服务器上执行这条命令生成密钥：
python3 -c "import secrets; print(secrets.token_hex(32))"
# 会输出类似：a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# 然后把输出分别填到这两个地方：
SMARTASK_SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
SECRET_KEY=f9e8d7c6b5a4123012345678901234567890abcdef1234567890abcdef123456
# ⚠️ 注意：这两个值必须不一样！生成两次！
```

##### 🟡 可选配置项（看情况修改）

```ini
# ====== 第15行左右：飞书集成（如果用飞书登录才需要）======
SMARTASK_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx      # 从飞书开放平台获取
SMARTASK_FEISHU_APP_SECRET=your-feishu-secret     # 从飞书开放平台获取
```

#### 3.3 保存并退出

1. 按 `Esc` 键退出编辑模式
2. 输入 `:wq` 并按回车保存退出

---

### 第4步：配置 Nginx（2分钟）

#### 4.1 创建 Nginx 配置文件

```bash
vi /etc/nginx/conf.d/smartask.conf
```

#### 4.2 粘贴完整配置（直接复制下面的内容）

**按 `i` 键进入编辑模式，然后粘贴以下全部内容：**

```nginx
server {
    listen 10899 ssl http2;
    server_name bifine.angelgroup.com.cn;

    # SSL证书（⚠️ 请替换为你的实际证书路径）
    ssl_certificate     /etc/letsencrypt/live/bifine.angelgroup.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bifine.angelgroup.com.cn/privkey.pem;

    # SSL优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 日志
    access_log /var/log/nginx/smartask_access.log;
    error_log  /var/log/nginx/smartask_error.log;

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # 前端路由（/smart-ask/ → :8888）
    location /smart-ask/ {
        proxy_pass http://127.0.0.1:8888/;
        rewrite ^/smart-ask/(.*)$ /$1 break;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        try_files $uri $uri/ /index.html;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API路由（/smart-ask/api/ → :5002，SSE支持）
    location /smart-ask/api/ {
        proxy_pass http://127.0.0.1:5002/api/;
        proxy_buffering off;          # 必须关闭！SSE流式响应
        proxy_cache off;              # 必须关闭！
        proxy_read_timeout 300s;      # 长超时
        proxy_send_timeout 300s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://127.0.0.1:8888;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 4.3 保存并测试Nginx配置

```bash
# 按 Esc，输入 :wq 保存退出

# 测试配置语法
nginx -t
# 预期输出：nginx: configuration file /etc/nginx/nginx.conf test is successful

# 重载Nginx
nginx -s reload
```

**如果 `nginx -t` 报错，检查是否有语法错误（比如少了个分号）**

---

### 第5步：启动 Docker 容器（2-5分钟）

```bash
# 使用外部代理模式启动（推荐）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build
```

**你会看到类似这样的输出：**
```
Building backend
Step 1/10 : FROM python:3.11-slim
 ---> abc123def456
...
Successfully built abc123def456
Successfully tagged smartask-new_smartask-backend:latest

Creating smartask-postgres ... done
Creating smartask-backend  ... done
Creating smartask-frontend ... done
```

**首次构建可能需要几分钟下载镜像，耐心等待即可。**

---

### 第6步：验证部署是否成功（30秒）

```bash
# 1. 检查容器状态（应该都是 Up 状态）
docker-compose ps
# 预期输出：
# NAME                STATUS           PORTS
# smartask-backend    Up (healthy)
# smartask-frontend   Up (healthy)
# smartask-postgres   Up (healthy)

# 2. 测试后端API
curl http://localhost:5002/api/health
# 预期输出：{"status":"ok","version":"...","timestamp":"..."}

# 3. 测试前端
curl -I http://localhost:8888/
# 预期输出：HTTP/1.1 200 OK
```

---

### 第7步：浏览器访问测试（最后一步！）

**在你的电脑浏览器中打开：**

```
https://bifine.angelgroup.com.cn:10899/smart-ask/
```

**如果能看到登录页面，恭喜你！部署成功！🎉**

---

## ✅ 部署成功检查清单

部署完成后，逐一确认以下项目：

- [ ] **容器状态正常**：`docker-compose ps` 显示所有容器都是 `Up (healthy)` 状态
- [ ] **后端健康检查通过**：`curl http://localhost:5002/api/health` 返回 `{"status":"ok"}`
- [ ] **前端页面可访问**：浏览器打开公网地址能看到登录页
- [ ] **管理员账号可以登录**：用户名 `admin`，密码是你刚才设置的
- [ ] **飞书登录可用**（如果配置了）：点击飞书登录能正常跳转和回调
- [ ] **AI问数功能正常**：登录后提问一个问题，能看到实时流式响应

**全部打勾就说明部署完全成功！**

---

## 🆘 常见问题快速解决

### 问题1：容器启动失败

**现象：** `docker-compose up` 后容器很快退出

**解决：**
```bash
# 查看错误日志
docker logs smartask-backend --tail 50

# 常见原因：
# 1. .env 格式错误（检查是否有多余空格或特殊字符未转义）
# 2. 数据库密码太弱（至少32位）
# 3. 端口被占用（检查 5002/8888 是否已被使用）
```

### 问题2：Nginx 配置报错

**现象：** `nginx -t` 提示语法错误

**解决：**
```bash
# 查看具体错误信息
nginx -t

# 常见错误：
# - 缺少分号（每行结束都要有 ;）
# - 括号不匹配（{ } 要成对）
# - 路径错误（证书路径不存在）
```

### 问题3：浏览器访问 502 Bad Gateway

**现象：** 浏览器显示 502 错误

**解决：**
```bash
# 1. 检查容器是否正常运行
docker-compose ps

# 2. 检查端口是否正确监听
netstat -tlnp | grep -E '(5002|8888)'

# 3. 查看 Nginx 错误日志
tail -20 /var/log/nginx/smartask_error.log
```

### 问题4：飞书登录失败

**现象：** 点击飞书登录提示"OAuth state 校验失败"

**解决：**
```bash
# 1. 检查 .env 中的 FEISHU_REDIRECT_URI
grep FEISHU_REDIRECT_URI .env

# 2. 对比飞书开放平台的配置（必须完全一致！）
# 包括 https、域名、端口、路径，一个字符都不能差

# 3. 确认已发布新版本（修改配置后必须发布才生效）
```

### 问题5：Git 克隆失败

**现象：** `git clone` 超时或失败

**原因：** 国内服务器访问 GitHub 可能不稳定

**解决方案：**

**方案A：使用代理（如果有）**
```bash
export https_proxy=http://your-proxy:port
git clone https://github.com/qishen123456/docker-setup.git .
```

**方案B：手动上传代码包**
```bash
# 在本地电脑打包
git archive --format=zip -o smartask.zip docker-setup

# 上传到服务器（用 scp 或 FTP 工具）
scp smartask.zip root@BISubApp01:/opta/smartask/

# 在服务器解压
cd /opta/smartask
unzip -o smartask.zip
```

---

## 📞 下一步操作

部署成功后，你可能还需要：

1. **配置飞书 OAuth**（详见 `DEPLOY_TO_SERVER.md` 的「飞书 OAuth 配置」章节）
2. **设置 SSL 证书**（如果没有的话，可以用 Let's Encrypt 免费申请）
3. **配置定期备份**（建议每天自动备份数据库）
4. **更新代码**（以后更新只需执行 `bash update.sh`）

---

## 💡 小贴士

- **保存好 .env 文件**：包含数据库密码、API Key 等敏感信息，不要提交到 Git
- **定期更新代码**：`bash update.sh` 可以一键更新并重启
- **查看实时日志**：`docker logs -f smartask-backend` 可以查看后端运行日志
- **备份重要数据**：定期备份数据库和 config/ 目录下的配置文件

---

## 📚 更多详细文档

如果你需要更详细的说明，可以查看：

- **[完整部署指南](./DEPLOY_TO_SERVER.md)** - 包含每个配置项的详细解释
- **[日常维护手册](./QUICK_START_GUIDE.md)** - 更新代码、重启服务、故障排查
- **[.env 配置详解](./.env.example)** - 所有配置项的完整示例和说明

---

**祝部署顺利！遇到问题不要慌，仔细看错误日志，大部分问题都能快速解决！💪**
