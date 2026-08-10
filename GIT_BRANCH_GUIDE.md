# Git 分支管理指南

> 本文档说明 SmartAsk 项目的 Git 分支策略，确保本地开发和服务器部署保持同步。

---

## 📊 当前分支架构

```
远程仓库: https://github.com/qishen123456/docker-setup.git
├── main          ← 主开发分支（推荐）✅
├── docker-setup  ← 旧版部署分支（已弃用）
└── feature/*     ← 功能开发分支（可选）
```

### 推荐策略：统一使用 main 分支

| 环境 | 分支 | 说明 |
|------|------|------|
| **本地开发** | `main` | 所有新功能都在此分支开发 |
| **服务器部署** | `main` | update.sh 默认拉取 main 分支 |
| **GitHub仓库** | `origin/main` | 远程主分支 |

---

## 🚀 标准工作流程

### 步骤1：本地开发（在 main 分支）

```bash
# 确保在 main 分支
git branch
# * main

# 查看修改状态
git status

# 提交更改
git add .
git commit -m "feat: 添加用户角色模型权限控制"
```

### 步骤2：推送到远程

```bash
# 推送到 origin/main
git push origin main

# 如果是首次推送
git push -u origin main
```

### 步骤3：服务器更新

```bash
# SSH 登录服务器
ssh root@your-server-ip
cd /opta/smartask

# 执行更新（自动拉取 main 分支）
bash update.sh
```

**update.sh 会自动执行以下操作：**
1. ✅ 备份配置文件（包括用户权限、模型配置等）
2. ✅ 切换到 `main` 分支
3. ✅ 拉取最新代码 (`git pull origin main`)
4. ✅ 恢复配置文件
5. ✅ 重建 Docker 容器
6. ✅ 健康检查验证

---

## 🔧 特殊场景处理

### 场景A：需要使用其他分支

如果需要从特定分支更新服务器：

```bash
# 方式一：通过参数指定
bash update.sh --branch docker-setup

# 方式二：通过环境变量指定
export SMARTASK_GIT_BRANCH=docker-setup
bash update.sh
```

### 场景B：多环境部署（测试/生产）

**推荐方案：使用不同分支对应不同环境**

```bash
# 测试环境（从 dev 分支更新）
export SMARTASK_GIT_BRANCH=dev
bash update.sh --no-build

# 生产环境（从 main 分支更新，默认）
bash update.sh
```

**或创建专用脚本：**

```bash
#!/bin/bash
# update-test.sh - 测试环境更新脚本
export SMARTASK_GIT_BRANCH=dev
exec bash update.sh "$@"
```

### 场景C：紧急修复（Hotfix）

```bash
# 1. 在 main 分支创建 hotfix 分支
git checkout -b hotfix/fix-login-bug

# 2. 修复问题并提交
git add .
git commit -m "fix: 修复飞书登录502错误"

# 3. 合并回 main 并推送
git checkout main
git merge hotfix/fix-login-bug
git push origin main

# 4. 服务器立即更新
ssh root@server "cd /opta/smartask && bash update.sh"
```

---

## ⚠️ 常见问题与解决方案

### Q1：为什么默认改成了 main 分支？

**原因：**
- 你在本地 `main` 分支开发代码
- 旧版 update.sh 默认拉取 `docker-setup` 分支
- 导致服务器获取的代码不是最新的

**解决方案：**
- 已将默认分支改为 `main`
- 本地推送到 `origin/main`
- 服务器拉取 `origin/main`

✅ **现在完全一致了！**

---

### Q2：我之前用 docker-setup 分支怎么办？

**情况分析：**

如果你的服务器上还有旧的 `docker-setup` 分支：

```bash
# 查看当前分支
git branch -a

# 如果存在 docker-setup 分支且不再需要
git branch -D docker-setup        # 删除本地分支
git push origin --delete docker-setup  # 删除远程分支
```

**迁移到 main 分支：**

```bash
# 1. 在服务器上切换到 main 分支
cd /opta/smartask
git fetch origin
git checkout main

# 2. 执行更新
bash update.sh
```

---

### Q3：如何确认服务器拉取的是正确分支？

**方法1：查看 update.sh 日志**

```bash
bash update.sh 2>&1 | grep "分支"

# 输出示例：
# ==> 拉取最新代码 (分支: main)
# Git checkout: main
# Git pull: origin main
```

**方法2：检查 Git 状态**

```bash
cd /opta/smartask
git branch
# * main
git log --oneline -3
# 显示最近的提交记录
```

---

### Q4：多人协作时如何避免冲突？

**场景：** 团队成员 A 和 B 同时在 main 分支开发

**解决方案：**

```bash
# 成员A的工作流程
git pull origin main           # 先拉取最新代码
git add . && git commit -m "feat: xxx"  # 提交
git push origin main           # 推送

# 成员B的工作流程（遇到冲突时）
git pull origin main           # 拉取时提示冲突
# 手动解决冲突文件...
git add .
git commit -m "merge: 解决与xxx的冲突"
git push origin main           # 推送合并后的代码
```

**最佳实践：**
- ✅ 每次开始工作前先 `git pull`
- ✅ 频繁提交小改动（不要堆积大量改动）
- ✅ 使用有意义的提交信息
- ✅ 重要功能先创建功能分支，测试后再合并到 main

---

## 📝 分支命名规范

| 类型 | 格式 | 示例 | 用途 |
|------|------|------|------|
| **主分支** | `main` | `main` | 主开发分支（稳定可用） |
| **功能分支** | `feature/描述` | `feature/user-model-permission` | 新功能开发 |
| **修复分支** | `fix/问题描述` | `fix/feishu-login-502` | Bug修复 |
| **热修复** | `hotfix/问题描述` | `hotfix/security-patch` | 紧急线上修复 |
| **测试分支** | `test/描述` | `test/nginx-proxy-mode` | 测试新特性 |

---

## 🔄 完整示例：从开发到部署

### 示例：添加新功能并部署到服务器

#### 第一步：本地开发

```bash
# 1. 进入项目目录
cd d:\1.智能问数项目\本地测试版2.0\smartask-new

# 2. 创建功能分支（可选，但推荐）
git checkout -b feature/model-permission-tree-ui

# 3. 开发并测试
# ... 编写代码 ...

# 4. 提交更改
git status                    # 查看状态
git diff                      # 查看具体改动
git add frontend/src/views/EmployeePermissions.vue
git commit -m "feat: 实现树形结构模型权限选择器UI"

# 5. 合并回 main 并推送
git checkout main
git merge feature/model-permission-tree-ui
git push origin main
```

#### 第二步：服务器部署

```bash
# 1. SSH 登录服务器
ssh root@BISubApp01

# 2. 进入项目目录
cd /opta/smartask

# 3. 执行更新（全自动！）
bash update.sh

# 输出：
# [OK] 检测到密文主密钥文件: config/.secret_master_key
#
# ==> 更新前备份
# SmartAsk Linux backup
# 输出目录: /opta/smartask/backups/20260810_120000
#
# ==> 拉取最新代码 (分支: main)
# Git checkout: main
# Git pull: origin main
# From https://github.com/qishen123456/docker-setup
#    8858bef..8f93361  main -> origin/main
#
# ==> 重建并启动容器
# 检测到Linux服务器环境，将使用外部代理模式（proxy）启动...
# 配置文件：docker-compose.yml docker-compose.proxy.yml
#
# [OK] 更新完成。
# 用户访问地址: https://bifine.angelgroup.com.cn:10899/smart-ask
```

#### 第三步：验证部署

```bash
# 在浏览器中访问
https://bifine.angelgroup.com.cn:10899/smart-ask/

# 或使用 curl 测试API
curl http://localhost:5002/api/health
# {"status":"ok","version":"..."}
```

---

## 🛠️ 高级技巧

### 技巧1：自动化部署（Git Hook）

在 `.git/hooks/post-push` 中添加：

```bash
#!/bin/bash
# 自动触发服务器更新（可选）

if [[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ]]; then
  echo "检测到 main 分支推送，是否要更新服务器？(y/n)"
  read -r answer
  if [[ "$answer" == "y" ]]; then
    ssh root@BISubApp01 "cd /opta/smartask && bash update.sh"
  fi
fi
```

### 技巧2：查看更新历史

```bash
# 服务器上查看最近10次更新记录
ls -lt /opta/smartask/backups/ | head -11

# 查看某次更新的详细日志
cat /opta/smartask/backups/20260810_120000/update.log
```

### 技巧3：快速回滚

```bash
# 回滚到上一个版本
bash update.sh --no-pull  # 不拉取新代码，只用当前代码重启

# 或手动恢复备份
cp /opta/smartask/backups/20260809_180000/config/*.json config/
docker-compose restart backend
```

---

## 📚 相关文档索引

| 文档 | 用途 |
|------|------|
| [DEPLOY_TO_SERVER.md](./DEPLOY_TO_SERVER.md) | 服务器部署完整指南 |
| [NGINX_DEPLOYMENT.md](./NGINX_DEPLOYMENT.md) | Nginx反向代理配置 |
| [.env.production](./.env.production) | 生产环境变量配置 |
| [deploy.sh](./deploy.sh) | 部署模式切换脚本 |
| [update.sh](./update.sh) | 一键更新脚本 |

---

## ✅ 总结

**核心原则：**
1. ✅ **统一使用 `main` 分支**（本地开发 + 服务器部署）
2. ✅ **推送前先 pull**（避免冲突）
3. ✅ **使用有意义的提交信息**（方便追踪历史）
4. ✅ **重要操作前先备份**（update.sh 会自动做）
5. ✅ **测试通过后再推送**（保证服务器稳定性）

**现在的配置已经完全统一：**
- 本地开发：`main` 分支 ✅
- 远程仓库：`origin/main` ✅
- 服务器更新：`main` 分支（默认） ✅

**不会再出现分支不匹配的问题了！** 🎉

---

**最后更新时间：2026-08-10**
