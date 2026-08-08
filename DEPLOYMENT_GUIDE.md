# SmartAsk 服务器部署操作指南

> **适用场景**: 从零开始的公司服务器部署（Linux环境）
> **最后更新**: 2026-08-07
> **部署工具**: `auto-deploy.sh` (一键部署脚本)

---

## 📋 目录

1. [部署前准备](#1-部署前准备)
2. [手动配置项清单](#2-手动配置项清单)
3. [一键部署流程](#3-一键部署流程)
4. [部署后初始化](#4-部署后初始化)
5. [功能验证清单](#5-功能验证清单)
6. [常见问题排查](#6-常见问题排查)
7. [日常运维命令](#7-日常运维命令)

---

## 1. 部署前准备

### 1.1 服务器要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2核 | 4核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB SSD | 100GB+ SSD |
| 操作系统 | Ubuntu 20.04+ / CentOS 8+ / Debian 11+ | Ubuntu 22.04 LTS |
| 网络 | 公网IP，开放5002/8888端口 | 同左 + CDN |

### 1.2 安装必要软件

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装Docker (如果未安装)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装Docker Compose V2插件
sudo apt install -y docker-compose-plugin

# 验证安装
docker --version          # Docker Engine >= 24.0
docker compose version    # Compose V2

# 安装其他必要工具
sudo apt install -y git curl wget

# 重新登录使docker组生效（或执行 newgrp docker）
```

### 1.3 网络与防火墙

```bash
# 开放必要端口（根据你的安全策略调整）
sudo ufw allow 5002/tcp   # 后端API
sudo ufw allow 8888/tcp   # 前端界面（开发模式）
# 生产环境建议使用Nginx反向代理80/443

# 或者使用firewalld（CentOS）
sudo firewall-cmd --permanent --add-port=5002/tcp
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --reload
```

---

## 2. 手动配置项清单

### ⚠️ 必须手动修改的配置（共5项）

这些配置**无法自动生成**，必须由你提供真实值：

#### 2.1 数据库密码
```env
# 文件: .env
SMARTASK_DB_PASSWORD=YourStrongPasswordHere_32chars+
```
**要求**:
- 长度 ≥ 32个字符
- 包含大小写字母+数字+特殊字符
- 示例: `Xk9#mP2$vL5@nQ8&wR3!yT6*`

#### 2.2 管理员密码
```env
SMARTASK_ADMIN_PASSWORD=AdminStrongPassword123!
```
**要求**:
- 不能是弱密码（禁止: admin123456, password, 123456）
- 长度 ≥ 12个字符
- **首次登录后立即修改**

#### 2.3 AI模型API Key
```env
# 选项A: OpenAI官方
SMARTASK_AI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
SMARTASK_AI_BASE_URL=https://api.openai.com/v1/
SMARTASK_AI_MODEL=gpt-4o

# 选项B: DeepSeek（推荐，性价比高）
SMARTASK_AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
SMARTASK_AI_BASE_URL=https://api.deepseek.com/v1/
SMARTASK_AI_MODEL=deepseek-chat

# 选项C: 其他兼容接口（Azure OpenAI, 通义千问等）
SMARTASK_AI_API_KEY=your-api-key
SMARTASK_AI_BASE_URL=https://your-endpoint.openai.azure.com/openai/deployments/xxx
SMARTASK_AI_MODEL=gpt-4
```

**获取方式**:
- OpenAI: https://platform.openai.com/api-keys
- DeepSeek: https://platform.deepseek.com/api_keys

#### 2.4 安全密钥（Session签名用）
```bash
# 生成随机密钥（执行此命令输出结果填入.env）
python3 -c "import secrets; print(secrets.token_hex(32))"
# 输出示例: a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef12

SMARTASK_SECRET_KEY=a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef12
SECRET_KEY=b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef123456
```

**重要**: 每个密钥必须不同！不要复用！

#### 2.5 飞书集成（可选）
```env
# 仅在使用飞书数据同步时需要
SMARTASK_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
SMARTASK_FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```
**获取方式**: 飞书开放平台 → 创建应用 → 凭证管理

---

## 3. 一键部署流程

### 3.1 快速开始（首次部署）

```bash
# 1. 进入目标目录（建议使用空目录）
cd /opt
sudo mkdir smartask && cd smartask

# 2. 下载部署脚本（或从Git仓库获取）
wget https://raw.githubusercontent.com/your-org/smartask/main/auto-deploy.sh
chmod +x auto-deploy.sh

# 3. 执行一键部署
./auto-deploy.sh \
  --git-url https://github.com/your-org/smartask.git \
  --branch main

# 4. 根据提示编辑 .env 文件
vim .env

# 5. 重新运行（跳过Git拉取）
./auto-deploy.sh --skip-git
```

### 3.2 完整示例输出

```
============================================================
  SmartAsk 一键部署工具 v1.0
============================================================

[INFO] 14:30:00 Phase 0/6: 检查运行环境...
  [========================================] 100% 磁盘空间 (120GB)
[OK] 环境检查通过 ✓

[INFO] 14:30:05 Phase 1/6: 从Git拉取代码...
仓库地址: https://github.com/org/smartask.git
目标分支: main
[OK] 代码准备完成 ✓

[INFO] 14:30:15 Phase 2/6: 检查并配置环境变量...
创建持久化目录...
[OK] 环境变量配置完成 ✓

[INFO] 14:30:20 Phase 3/6: 构建并启动Docker服务...
构建Docker镜像（可能需要5-15分钟）...
[OK] Docker服务已启动 ✓

[INFO] 14:35:45 Phase 4/6: 初始化数据库...
等待后端服务就绪...
[OK] 后端服务已就绪 ✓
补充缺失的业务表...
[OK] 数据库初始化完成 ✓

[INFO] 14:36:10 Phase 5/6: 执行功能验证...
[1/5] 健康检查...
[OK] 健康检查通过 ✓
[2/5] 管理员登录测试...
[OK] 管理员登录成功 ✓ (Token: eyJhbGciOiJIUzI1NiIs...)
[3/5] 权限API测试...
[OK] 权限API正常 ✓
[4/5] 运行态导出测试...
[OK] 运行态导出正常 ✓ (57420832字节)
[5/5] Docker容器状态...
[OK] 所有容器运行正常 ✓
[OK] 功能验证完成 ✓

[INFO] 14:36:30 Phase 6/6: 部署总结

============================================================
🎉 SmartAsk 部署成功！
============================================================

📌 访问地址:
  前端界面: http://192.168.1.100:8888
  后端API:  http://192.168.1.100:5002/api/health
  数据库:   192.168.1.100:5433 (仅内部访问)

👤 默认账号:
  用户名: admin
  密码:   ***请查看.env***

📋 后续操作:
  1. 登录前端界面修改默认密码
  2. 配置飞书同步（如果需要）
  3. 导入书架元数据和业务数据
  4. 触发第一次全量数据同步

📝 常用命令:
  查看日志: docker compose logs -f backend
  停止服务: docker compose down
  重启服务: docker compose restart
  备份数据: docker exec smartask-backend python /app/scripts/backup_all.py
  更新部署: ./auto-deploy.sh --skip-git

📄 日志文件: deploy_20260807_143000.log
============================================================
```

### 3.3 更新已有部署

```bash
# 方式A: 使用自动更新脚本
./auto-deploy.sh --skip-git

# 方式B: 手动更新代码后重启
git pull origin main
docker compose up -d --build
```

### 3.4 迁移部署（带旧数据）

```bash
# 1. 从旧服务器导出备份
ssh old-server 'docker exec smartask-backend python /app/scripts/export_runtime_config.py' > runtime_config_bundle.json

# 2. 在新服务器部署并导入
scp runtime_config_bundle.json new-server:/opt/smartask/

ssh new-server
cd /opt/smartask
./auto-deploy.sh \
  --skip-git \
  --with-backup \
  --backup-file ./runtime_config_bundle.json
```

---

## 4. 部署后初始化

### 4.1 登录系统并修改密码

1. 打开浏览器访问: `http://服务器IP:8888`
2. 使用默认管理员账号登录
3. **立即修改默认密码**
4. 创建业务用户账号（按需）

### 4.2 导入业务数据（关键步骤！）

#### 4.2.1 导入书架元数据

```bash
# 如果有旧环境的书架数据
scp user@old-server:/path/to/bookshelf_bundle.json ./

# 导入到新环境
docker exec -i smartask-backend python /app/scripts/import_runtime_config.py \
  --input /dev/stdin \
  --mode merge < bookshelf_bundle.json
```

#### 4.2.2 配置飞书同步（如果使用）

1. 登录前端 → 管理后台 → 飞书数据同步
2. 编辑每个同步任务的飞书链接（base_id/table_id/view_id）
3. 保存配置
4. 手动触发一次全量同步：
   ```bash
   # 通过API触发所有同步任务
   TOKEN=$(curl -s -X POST http://localhost:5002/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"你的密码"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

   for i in {1..7}; do
     curl -s -X POST "http://localhost:5002/api/feishu-sync/run/$i" \
       -H "X-Auth-Token: $TOKEN"
     echo "已触发任务 $i"
   done
   ```

5. 监控同步进度：
   ```bash
   docker compose logs -f backend | grep -E "(sync|feishu|完成)"
   ```

#### 4.2.3 重建节点索引

```bash
# 同步完成后必须重建索引（确保问数口径一致）
docker exec smartask-backend python /app/backend/build_dataset_node_index.py

# 验证索引文件生成
ls -lh config/dataset_node_index.json
```

### 4.3 验证问数功能

在系统中测试以下典型问题：

| 测试场景 | 示例问题 | 预期结果 |
|---------|---------|---------|
| Overview类 | "商用事业部的业绩情况" | 返回汇总数据 |
| 排名TopN | "前5的业务承接人" | 返回Top5列表 |
| 人名识别 | "丁杰的业绩怎么样" | 正确识别主体 |
| 对比分析 | "东部和西部对比一下" | 返回对比数据 |

---

## 5. 功能验证清单

部署完成后，逐项确认以下功能正常：

### 5.1 基础服务 ✅

- [ ] 访问 `http://IP:8888` 能看到前端界面
- [ ] 访问 `http://IP:5002/api/health` 返回 `{"status":"ok"}`
- [ ] 管理员可以登录系统
- [ ] Docker三个容器都在运行（postgres/backend/frontend）

### 5.2 核心功能 ✅

- [ ] NL2SQL问数能返回结果（至少测5个问题）
- [ ] 排名/TopN查询正确
- [ ] 层级Overview显示正常
- [ ] 人名识别准确
- [ ] 对比分析功能可用

### 5.3 权限系统 ✅

- [ ] 超管可以看到所有菜单
- [ ] 普通用户只能看到授权的功能
- [ ] 数据集权限隔离有效
- [ ] 可以新建用户并分配角色

### 5.4 数据管理 ✅

- [ ] 飞书同步定时任务在运行
- [ ] 可以手动触发同步
- [ ] 数据导出（Excel/PDF）正常
- [ ] 备份功能正常（`backup_all.py`可执行）

### 5.5 日志监控 ✅

- [ ] 无ERROR级别异常日志
- [ ] 飞书同步日志正常记录
- [ ] 容器健康检查通过

---

## 6. 常见问题排查

### 6.1 端口被占用

**现象**: 启动时报错 `port already in use`

**解决**:
```bash
# 查看占用端口的进程
lsof -i :5002
lsof -i :8888

# 杀掉进程或修改.env中的端口号
vim .env
# 修改 SMARTASK_BACKEND_PORT=5002 为其他端口
```

### 6.2 数据库连接失败

**现象**: 后端日志报 `Connection refused` 或 `password authentication failed`

**解决**:
```bash
# 1. 检查PostgreSQL是否启动
docker compose ps postgres

# 2. 检查.env中的数据库配置是否匹配
grep SMARTASK_DB_ .env

# 3. 重置PostgreSQL（会丢失数据！仅用于测试环境）
docker compose down -v
docker compose up -d postgres
```

### 6.3 AI模型调用失败

**现象**: 问数时返回"AI调用失败"

**解决**:
```bash
# 1. 检查API Key是否正确
grep SMARTASK_AI_API_KEY .env

# 2. 测试API连通性
curl -H "Authorization: Bearer $SMARTASK_AI_API_KEY" \
  "$SMARTASK_AI_BASE_URL/models"

# 3. 检查余额/额度是否充足
```

### 6.4 镜像构建失败

**现象**: `docker compose build` 报错

**解决**:
```bash
# 清理Docker缓存重试
docker builder prune -f
docker compose build --no-cache

# 如果网络问题，配置镜像加速
# 参考 .env 中的 SMARTASK_DOCKER_REGISTRY_MIRRORS
```

### 6.5 问数效果差/口径不一致

**现象**: 相同问题在不同环境返回不同结果

**原因**: `dataset_node_index.json` 缺失或过期

**解决**:
```bash
# 1. 重建节点索引
docker exec smartask-backend python /app/backend/build_dataset_node_index.py

# 2. 确保飞书数据已同步
# 3. 检查 config/dataset_dimension_profiles.json 是否存在（审计A-02）
```

---

## 7. 日常运维命令

### 7.1 服务管理

```bash
# 查看状态
docker compose ps

# 查看日志（实时）
docker compose logs -f backend      # 后端日志
docker compose logs -f postgres     # 数据库日志
docker compose logs -f frontend     # 前端日志

# 重启服务
docker compose restart             # 重启全部
docker compose restart backend      # 只重启后端

# 停止服务
docker compose stop                # 停止不删除
docker compose down                # 停止并删除容器
docker compose down -v              # 停止并删除卷（会丢失数据！）
```

### 7.2 数据备份

```bash
# 全量备份（推荐每天执行）
docker exec smartask-backend python /app/scripts/backup_all.py
# 输出: backups/YYYYMMDD_HHMMSS/

# 只备份运行态配置
docker exec smartask-backend python /app/scripts/export_runtime_config.py \
  --output /app/backups/runtime_config_bundle.json

# 只备份数据库
docker exec smartask-postgres pg_dump -U smartask_user smartask_db > db_backup.sql
```

### 7.3 数据恢复

```bash
# 从备份恢复运行态配置
docker exec smartask-backend python /app/scripts/import_runtime_config.py \
  --input /app/backups/runtime_config_bundle.json \
  --mode merge

# 恢复数据库（危险操作！）
docker exec -i smartask-postgres psql -U smartask_user smartask_db < db_backup.sql
```

### 7.4 性能监控

```bash
# 查看资源使用情况
docker stats --no-stream

# 查看磁盘空间
df -h
du -sh smartask_pg_data/    # 数据库大小
du -sh config/              # 配置文件大小
du -sh logs/                # 日志大小

# 清理日志（保留最近7天）
find logs/ -name "*.log" -mtime +7 -delete
```

### 7.5 版本更新

```bash
# 方法1: 使用自动更新脚本（推荐）
./auto-deploy.sh --skip-git

# 方法2: 手动更新
git pull origin main
docker compose up -d --build

# 更新后验证
curl http://localhost:5002/api/health
```

---

## 📞 技术支持

如遇问题无法解决：

1. 查看详细日志: `cat deploy_*.log`
2. 执行诊断: `bash doctor.sh` （如果有）
3. 收集信息:
   - 操作系统版本: `cat /etc/os-release`
   - Docker版本: `docker version`
   - 错误日志: `docker compose logs --tail=200 backend > debug.log`
4. 提交Issue到项目仓库

---

## 📌 附录：快速参考卡

### 最常用命令速查

```bash
# 一键部署
./auto-deploy.sh --git-url <repo-url>

# 更新部署
./auto-deploy.sh --skip-git

# 查看日志
docker compose logs -f backend

# 备份
docker exec smartask-backend python /app/scripts/backup_all.py

# 重启
docker compose restart backend

# 停止
docker compose down
```

### 关键文件位置

| 文件 | 用途 | 是否需要备份 |
|------|------|------------|
| `.env` | 所有配置 | ⚠️ 是（含密码）|
| `config/*.json` | 运行态配置 | ✅ 是 |
| `config/dataset_node_index.json` | 节点索引 | ✅ 是 |
| `backups/` | 自动备份输出 | 可选 |
| `logs/` | 运行日志 | 否（可重建）|

### 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 5002 | 后端API | Flask应用 |
| 8888 | 前端界面 | Vue SPA (Nginx) |
| 5433 | PostgreSQL | 数据库映射端口（生产环境不应暴露）|

---

**祝部署顺利！** 🚀
