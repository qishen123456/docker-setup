# SmartAsk 服务器部署指南（你的场景）

> **公网地址：** `https://bifine.angelgroup.com.cn:10899/smart-ask`
>
> **架构：** 外部Nginx/负载均衡 → Docker容器

---

## 📋 你的架构理解

```
用户浏览器
    ↓ HTTPS :10899
外部 Nginx / 负载均衡
    ├─ /smart-ask/      → Docker Frontend (:8888)
    └─ /smart-ask/api/  → Docker Backend (:5002)
    ↓
Docker 容器
  ├── smartask-frontend  (端口8888映射到宿主机)
  ├── smartask-backend   (端口5002映射到宿主机)
  └── smartask-postgres  (端口5433映射到宿主机，仅内部使用)
```

---

## 🚀 部署步骤（5分钟搞定）

### 步骤1：准备配置文件

在服务器上：

```bash
# 进入项目目录
cd /path/to/smartask-new

# 复制生产环境配置
cp .env.production .env
```

### 步骤2：验证配置

```bash
# 检查关键配置项
grep -E "^(PUBLIC_DOMAIN|PUBLIC_PORT|BASE_PATH|FEISHU_REDIRECT_URI)" .env
```

**预期输出：**
```
PUBLIC_DOMAIN=bifine.angelgroup.com.cn
PUBLIC_PORT=10899
BASE_PATH=/smart-ask
FEISHU_REDIRECT_URI=https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback
```

### 步骤3：启动服务

```bash
# 使用外部代理模式启动（推荐）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build
```

**或者使用部署脚本：**
```bash
chmod +x deploy.sh
./deploy.sh production
# 然后手动执行：
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build
```

### 步骤4：验证服务状态

```bash
# 查看所有容器状态
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml ps

# 预期输出（所有服务应该是 Up 状态）：
# NAME                STATUS                      PORTS
# smartask-backend    Up (healthy)                 0.0.0.0:5002->5002/tcp
# smartask-frontend   Up (healthy)                 0.0.0.0:8888->80/tcp
# smartask-postgres   Up (healthy)                 0.0.0.0:5433->5432/tcp
```

### 步骤5：健康检查

```bash
# 测试后端API（在服务器上）
curl http://localhost:5002/api/health

# 测试前端（在服务器上）
curl -I http://localhost:8888/

# 预期返回 HTTP 200 OK
```

---

## 🔧 外部Nginx配置（关键！）

你的外部Nginx需要这样配置：

```nginx
server {
    listen 10899 ssl;
    server_name bifine.angelgroup.com.cn;

    # SSL证书配置（根据实际情况修改）
    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # ====== SmartAsk 前端路由 ======
    location /smart-ask/ {
        # 转发到Docker前端容器
        proxy_pass http://127.0.0.1:8888/;

        # 基础路径重写（重要！）
        rewrite ^/smart-ask/(.*)$ /$1 break;

        # 标准代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Vue Router history 模式支持
        try_files $uri $uri/ /index.html;
    }

    # ====== SmartAsk API路由 ======
    location /smart-ask/api/ {
        # 转发到Docker后端容器
        proxy_pass http://127.0.0.1:5002/api/;

        # SSE流式响应支持（必须！）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;

        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 标准代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 文件上传大小限制
        client_max_body_size 100M;
    }
}
```

**关键点说明：**
1. `rewrite ^/smart-ask/(.*)$ /$1 break;` - 去掉路径前缀，否则前端会找不到资源
2. `proxy_buffering off;` - 必须关闭缓冲，否则SSE流式响应不工作
3. `proxy_read_timeout 300s;` - 长连接超时时间要足够长

---

## 🔐 飞书OAuth配置（必须更新！）

### 在飞书开放平台操作：

1. **登录飞书开发者后台**：https://open.feishu.cn/app
2. **选择你的应用**（SmartAsk相关应用）
3. **进入 安全设置 → 重定向 URL**
4. **添加以下URL**（如果还没有的话）：

```
https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback
```

5. **保存并发布应用版本**（重要！修改后需要重新发布才生效）

### 验证飞书登录流程：

1. 访问：`https://bifine.angelgroup.com.cn:10899/smart-ask`
2. 点击"使用飞书组织身份登录"
3. 应该跳转到飞书授权页面
4. 授权后回调到：`https://.../api/auth/feishu/callback?code=xxx&state=xxx`
5. 自动跳转回前端页面并完成登录

**常见问题：**
- ❌ `飞书 OAuth state 校验失败` → 检查FEISHU_REDIRECT_URI是否与飞书平台配置一致
- ❌ `502 Bad Gateway` → 检查外部Nginx是否正确转发到Docker容器
- ❌ `回调地址不匹配` → 飞书平台的URL必须与.env中的完全一致（包括协议、域名、端口、路径）

---

## ✅ 部署检查清单

部署完成后，逐一验证：

- [ ] **Docker容器运行正常**
  ```bash
  docker-compose -f docker-compose.yml -f docker-compose.proxy.yml ps
  ```

- [ ] **后端健康检查通过**
  ```bash
  curl http://localhost:5002/api/health
  # 返回：{"status":"ok",...}
  ```

- [ ] **前端页面可访问**
  ```bash
  curl -I https://bifine.angelgroup.com.cn:10899/smart-ask/
  # 返回：HTTP/1.1 200 OK
  ```

- [ ] **API接口可访问**
  ```bash
  curl https://bifine.angelgroup.com.cn:10899/smart-ask/api/health
  # 返回：{"status":"ok",...}
  ```

- [ ] **账号密码登录成功**
  - 访问前端页面
  - 输入手机号和密码
  - 成功进入系统

- [ ] **飞书登录成功**
  - 点击"使用飞书组织身份登录"
  - 完成飞书授权
  - 成功回到系统并显示用户信息

- [ ] **智能问数功能正常**
  - 输入问题："上海的业绩"
  - 能看到SSE流式响应
  - 返回查询结果

- [ ] **模型权限过滤生效**
  - 登录刘太琳账号
  - 点击模型下拉框
  - 只看到默认模型（MiniMax-M2.5）

- [ ] **日志无报错**
  ```bash
  # 查看后端日志
  docker logs smartask-backend --tail 50

  # 查看前端日志
  docker logs smartask-frontend --tail 20
  ```

---

## 🔄 常用运维命令

```bash
# === 启动/停止/重启 ===

# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d

# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml down

# 重启某个服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml restart backend

# 重新构建并启动（代码更新后）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build


# === 日志查看 ===

# 实时查看后端日志
docker logs -f smartask-backend

# 查看最近100行前端日志
docker logs smartask-frontend --tail 100

# 查看特定时间的日志（今天）
docker logs smartask-backend --since "2026-08-10T00:00:00"


# === 数据备份 ===

# 导出数据库备份
docker exec smartask-postgres pg_dump -U postgres > backup_$(date +%Y%m%d).sql

# 备份配置文件
tar czf config_backup_$(date +%Y%m%d).tar.gz config/


# === 故障排查 ===

# 检查端口占用
netstat -tlnp | grep -E '(5002|8888|5433)'

# 测试内部网络连通性
docker exec smartask-frontend wget -qO- http://smartask-backend:5002/api/health

# 进入容器调试
docker exec -it smartask-backend bash
docker exec -it smartask-frontend sh
```

---

## ⚠️ 注意事项

### 1. 防火墙设置
确保服务器防火墙允许以下端口：
- **10899** - 对外提供HTTPS访问（SmartAsk）
- **22** - SSH远程管理（如果需要）

**不需要对外暴露的端口：**
- ~~5002~~ - 后端API（只绑定到localhost）
- ~~8888~~ - 前端（只绑定到localhost）
- ~~5433~~ - PostgreSQL（只绑定到localhost）

### 2. SSL证书
确保SSL证书有效且未过期。可以使用：
- Let's Encrypt免费证书
- 公司自有证书
- 自签名证书（仅测试用）

### 3. 性能优化建议
- 开启Nginx的Gzip压缩
- 配置静态资源缓存（JS/CSS/图片）
- 定期清理Docker日志（避免磁盘占满）

### 4. 安全加固
- 修改 `.env` 中的默认密码（SMARTASK_ADMIN_PASSWORD等）
- 定期更新基础镜像（`docker pull` + 重新build）
- 限制Docker容器的资源使用（memory/cpu limits）

---

## 📞 问题排查速查表

| 问题现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 访问页面502 | 外部Nginx未启动或配置错误 | 检查 `nginx -t && nginx -s reload` |
| 飞书OAuth失败 | 回调URL不匹配 | 对比 `.env` 和飞书平台配置 |
| SSE无响应 | Nginx开启了buffering | 设置 `proxy_buffering off;` |
| 登录后白屏 | Vue Router路径错误 | 检查 `try_files` 配置 |
| API跨域错误 | 缺少CORS头 | 添加 `Access-Control-Allow-Origin` |
| 数据库连不上 | Postgres容器未启动 | `docker-compose up postgres` |

---

## 💡 下一步建议

1. **首次部署**：先按上述步骤完成部署
2. **功能验证**：使用Playwright自动化测试（刚才已验证通过）
3. **性能监控**：接入Prometheus+Grafana监控Docker容器
4. **日志收集**：配置ELK或Loki收集应用日志
5. **自动备份**：设置cron定时备份数据库和配置

---

## 📚 相关文件索引

| 文件 | 用途 |
|------|------|
| `.env.production` | 生产环境变量模板（已配置你的地址） |
| `docker-compose.proxy.yml` | 外部代理模式override（推荐使用） |
| `deploy.sh` | Linux/Mac部署脚本 |
| `deploy.ps1` | Windows部署脚本 |
| `NGINX_DEPLOYMENT.md` | 完整Nginx配置指南（通用版） |
| `DEPLOY_TO_SERVER.md` | 本文档（你的专属部署指南） |

---

**最后更新：** 2026-08-10
**适用场景：** `https://bifine.angelgroup.com.cn:10899/smart-ask`
