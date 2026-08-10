# 快速推送代码到 GitHub

> 一键式脚本，帮助你快速将本地代码推送到远程仓库。

---

## 🚀 快速开始（3步搞定）

### 第一步：查看当前状态

```bash
# 在项目根目录执行
git status
```

**预期输出：**
```
On branch main
Changes not staged for commit:
  modified:   deploy.sh
  modified:   update.sh
  ...
Untracked files:
  docker-compose.proxy.yml
  DEPLOY_TO_SERVER.md
  ...
```

---

### 第二步：提交所有更改

**方式A：提交所有更改（推荐新手）**

```bash
# 添加所有文件（包括新增和修改）
git add .

# 提交（使用有意义的消息）
git commit -m "feat: 完善部署脚本+自动环境检测+分支管理优化"
```

**方式B：选择性提交（推荐熟练用户）**

```bash
# 只添加特定文件
git add deploy.sh update.sh docker-compose.proxy.yml .env.production

# 提交
git commit -m "feat: 增强部署脚本支持自动环境检测"
```

---

### 第三步：推送到 GitHub

```bash
# 推送到 origin/main（首次需要 -u 参数）
git push -u origin main

# 后续推送只需
git push origin main
```

**成功输出示例：**
```
Enumerating objects: 25, done.
Counting objects: 100% (25/25), done.
Delta compression using up to 4 threads
Compressing objects: 100% (20/20), done.
Writing objects: 100% (20/20), 2.5 KiB | 2.5 MiB/s, done.
Total 20 (delta 8), reused 0 (delta 0)
To https://github.com/qishen123456/docker-setup.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

✅ **完成！代码已推送到 GitHub！**

---

## 📋 本次要推送的文件清单

### ✅ 核心配置文件（必须推送）

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `.env.production` | 🔧 更新 | 配置公网地址 `https://bifine.angelgroup.com.cn:10899/smart-ask` |
| `docker-compose.proxy.yml` | 🆕 新建 | 外部代理模式配置（禁用Docker内Nginx） |

### ✅ 部署脚本（重要更新）

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `deploy.sh` | 🔧 增强 | 新增proxy模式 + 自动环境检测 + 智能推荐 + 增强状态面板 |
| `update.sh` | 🔧 修复+增强 | 修复Git兼容性 + 自动环境检测 + **默认分支改为main** |

### ✅ 文档资料（新增）

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `DEPLOY_TO_SERVER.md` | 🆕 新建 | 专属服务器部署指南（含Nginx配置） |
| `GIT_BRANCH_GUIDE.md` | 🆕 新建 | Git分支管理完整指南 |
| `PUSH_TO_GITHUB.md` | 🆕 新建 | 本文档 |

---

## 🔧 推送前的检查清单

在推送前，建议先确认以下事项：

- [ ] **代码已本地测试通过**
  ```bash
  # 如果是前端改动，确认编译无报错
  cd frontend && npm run build

  # 如果是后端改动，确认语法正确
  cd backend && python -m py_compile controllers/*.py
  ```

- [ ] **敏感信息未泄露**
  ```bash
  # 确认没有提交密码、密钥等敏感信息
  git diff --cached | grep -i "password\|secret\|api_key"
  
  # 如果发现误提交，立即撤销
  git reset HEAD <file>
  ```

- [ ] **提交信息规范**
  ```
  格式：<type>(<scope>): <subject>

  type:
    feat     - 新功能
    fix      - Bug修复
    docs     - 文档更新
    style    - 代码格式调整（不影响功能）
    refactor - 重构（不是新功能也不是修复Bug）
    test     - 测试相关
    chore    - 构建/工具/辅助工具变动

  示例：
    feat(auth): 添加飞书账号合并功能
    fix(update): 解决旧版Git stash命令不兼容问题
    docs(deploy): 补充Nginx反向代理配置说明
  ```

- [ ] **分支正确**
  ```bash
  # 确保在 main 分支
  git branch
  # * main  ← 必须是这个
  ```

---

## ⚠️ 常见问题与解决方案

### Q1：提示 "src refspec you specified does not match any"

**原因：** 本地还没有任何提交或 main 分支不存在

**解决方案：**
```bash
# 创建初始提交
git add .
git commit -m "Initial commit: SmartAsk project setup"

# 推送时指定分支名
git push -u origin main
```

---

### Q2：提示 "fatal: remote origin already exists"

**原因：** 已经配置过远程仓库

**解决方案：**
```bash
# 查看当前远程仓库配置
git remote -v

# 如果URL正确，直接push即可
git push origin main

# 如果URL错误，重新设置
git remote set-url origin https://github.com/qishen123456/docker-setup.git
git push -u origin main
```

---

### Q3：提示 "error: failed to push some refs"

**原因：** 远程仓库有新的提交但本地没有

**解决方案：**
```bash
# 先拉取远程更改
git pull origin main --rebase

# 再推送
git push origin main
```

如果遇到冲突：
```bash
# 手动解决冲突后
git add .
git rebase --continue
git push origin main
```

---

### Q4：如何撤销已经推送的提交？

**⚠️ 谨慎操作！这会影响远程仓库**

```bash
# 方式一：软重置（保留本地更改）
git reset --soft HEAD~1
git push origin main --force-with-lease

# 方式二：完全删除上一个提交（不可逆）
git reset --hard HEAD~1
git push origin main --force-with-lease

# 方式三：恢复到某个历史版本
git log --oneline  # 找到要回退的commit hash
git reset --hard <commit-hash>
git push origin main --force-with-lease
```

---

### Q5：如何只推送某个文件的修改？

```bash
# 只添加并推送单个文件
git add deploy.sh
git commit -m "fix(deploy): 修复Git兼容性问题"
git push origin main
```

---

## 💡 高级技巧

### 技巧1：一键推送脚本

创建 `quick-push.sh`：

```bash
#!/bin/bash
# quick-push.sh - 快速推送脚本

echo "📦 开始推送代码..."
echo ""

# 1. 显示状态
echo "📋 当前状态："
git status --short
echo ""

# 2. 确认推送
read -p "确认推送以上更改？(y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  # 3. 提交并推送
  read -p "请输入提交信息: " message
  git add .
  git commit -m "$message" || git commit -m "chore: update files $(date +%Y%m%d_%H%M%S)"
  git push origin main
  
  echo ""
  echo "✅ 推送成功！"
else
  echo "❌ 已取消推送"
fi
```

使用方法：
```bash
chmod +x quick-push.sh
./quick-push.sh
```

---

### 技巧2：推送到多个远程仓库

```bash
# 添加第二个远程仓库（如备份到GitLab）
git remote add backup git@gitlab.com:user/smartask.git

# 同时推送到两个仓库
git push origin main && git push backup main
```

---

### 技巧3：查看推送历史

```bash
# 查看最近的推送记录
git log --oneline --graph --all -10

# 查看某个文件的历史
git log --oneline deploy.sh -10
```

---

## 🎯 推荐的工作流

### 日常开发流程（推荐）

```bash
# 1. 开始工作前，拉取最新代码
git pull origin main

# 2. 创建功能分支（可选但推荐）
git checkout -b feature/your-feature-name

# 3. 开发并测试
# ... 写代码 ...

# 4. 提交更改
git add .
git commit -m "feat: 你的功能描述"

# 5. 合并回主分支
git checkout main
git merge feature/your-feature-name

# 6. 删除功能分支（可选）
git branch -d feature/your-feature-name

# 7. 推送到GitHub
git push origin main

# 8. （可选）服务器更新
ssh root@server "cd /opta/smartask && bash update.sh"
```

---

## 📊 推送后的验证步骤

推送成功后，建议进行以下验证：

### 1️⃣ 验证GitHub上的代码

访问：https://github.com/qishen123456/docker-setup/tree/main

确认文件已更新。

---

### 2️⃣ 验证服务器能否拉取

```bash
# SSH 登录服务器
ssh root@BISubApp01

# 测试拉取（不实际执行更新）
cd /opta/smartask
git fetch origin
git log HEAD..origin/main --oneline
# 应该显示你刚刚推送的提交记录
```

---

### 3️⃣ 执行服务器更新（可选）

```bash
# 实际执行更新
bash update.sh

# 验证服务状态
curl http://localhost:5002/api/health
```

---

## ✅ 总结

**现在你可以安全地推送代码了！**

**核心要点：**
1. ✅ 统一使用 `main` 分支（本地+远程+服务器一致）
2. ✅ 推送前先 `git pull`（避免冲突）
3. ✅ 使用规范的提交信息（方便追踪）
4. ✅ 重要操作前先备份（update.sh 会自动做）
5. ✅ 推送后在GitHub上验证（确保文件正确）

**本次推送包含的重要更新：**
- 🔧 修复了 update.sh 的 Git 兼容性问题
- 🎯 默认分支改为 `main`（解决分支不匹配问题）
- 🤖 添加自动环境检测（Linux→proxy, Windows→local）
- 📚 新增完整的文档资料

**准备好了吗？执行以下命令即可推送：**

```bash
git add .
git commit -m "feat: 完善部署体系+自动环境检测+分支管理优化"
git push -u origin main
```

🎉 **祝推送顺利！**

---

**最后更新时间：2026-08-10**
