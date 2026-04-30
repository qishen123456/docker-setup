# Git 管理指南

## 🚀 快速开始

### 当前状态
- ✅ Git仓库已初始化
- ✅ 所有文件已添加到版本控制
- ✅ 第一次提交已完成 (commit: d689f9a)

## 📋 常用Git命令

### 🔍 查看状态
```bash
git status                    # 查看工作区状态
git log --oneline            # 查看提交历史
git diff                     # 查看文件变更
git diff --staged            # 查看暂存区变更
```

### ➕ 添加和提交
```bash
git add .                    # 添加所有文件
git add <filename>           # 添加指定文件
git commit -m "提交信息"      # 提交变更
git commit -am "提交信息"     # 添加并提交
```

### 🔀 分支管理
```bash
git branch                   # 查看所有分支
git branch <branch-name>     # 创建新分支
git checkout <branch-name>   # 切换分支
git checkout -b <branch-name> # 创建并切换分支
git merge <branch-name>     # 合并分支
git branch -d <branch-name> # 删除分支
```

### 📤 推送和拉取
```bash
git remote add origin <url>  # 添加远程仓库
git push -u origin master   # 首次推送到远程
git push                    # 推送到远程
git pull                    # 拉取远程变更
git fetch                   # 获取远程信息
```

### ↩️ 撤销操作
```bash
git reset --soft HEAD~1     # 撤销最后一次提交（保留变更）
git reset --hard HEAD~1     # 撤销最后一次提交（丢弃变更）
git checkout -- <file>      # 撤销文件修改
git clean -fd               # 清理未跟踪文件
```

## 🎯 推荐工作流

### 1. 功能开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/新功能名称

# 2. 开发和提交
git add .
git commit -m "feat: 添加新功能描述"

# 3. 切换回主分支并合并
git checkout master
git merge feature/新功能名称

# 4. 删除功能分支
git branch -d feature/新功能名称
```

### 2. 提交信息规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具的变动
```

### 3. 日常开发流程
```bash
# 开始工作前
git pull                    # 拉取最新代码

# 开发过程中
git add .
git commit -m "描述变更"

# 完成工作后
git push                    # 推送到远程
```

## 📁 项目结构

### 已忽略的文件 (.gitignore)
- `node_modules/` - 前端依赖
- `__pycache__/` - Python缓存
- `*.log` - 日志文件
- `.env` - 环境变量（敏感信息）
- `dist/` - 构建产物
- `_legacy/` - 归档的遗留代码
- `chroma_db/` - 向量数据库
- IDE配置文件

### 重要文件说明
- `frontend/` - Vue 3 前端项目
- `backend/` - Flask 后端服务
- `config/` - 运行时配置 (JSON)
- `docker/` - Docker 初始化脚本
- `scripts/` - 运维脚本（测试、备份、验证）
- `deploy.ps1` / `deploy.bat` - 一键部署入口
- `docker-compose.yml` - 服务编排

## 🔧 高级操作

### 标签管理
```bash
git tag v1.0.0               # 创建标签
git tag                      # 查看所有标签
git push origin v1.0.0       # 推送标签
```

### 暂存操作
```bash
git stash                    # 暂存当前工作
git stash pop                # 恢复暂存的工作
git stash list               # 查看暂存列表
```

### 查看历史
```bash
git log --graph --oneline    # 图形化提交历史
git log --stat               # 查看提交统计
git blame <file>             # 查看文件修改历史
```

## 🌐 远程仓库设置

### 添加GitHub仓库
```bash
git remote add origin https://github.com/用户名/仓库名.git
git push -u origin master
```

### 查看远程仓库
```bash
git remote -v                # 查看所有远程仓库
git remote show origin       # 查看远程仓库详情
```

## 💡 最佳实践

1. **频繁提交**：小步快跑，便于回滚
2. **清晰的提交信息**：描述做了什么，为什么做
3. **分支开发**：主分支保持稳定
4. **定期推送**：防止本地代码丢失
5. **代码审查**：重要功能合并前进行审查

## 🚨 注意事项

- 不要提交敏感信息（密码、API密钥等）
- 大文件考虑使用Git LFS
- 定期清理不需要的分支
- 重要节点打标签便于版本管理

## 📞 获取帮助

```bash
git help <command>          # 查看命令帮助
git --help                  # 查看Git帮助
```
