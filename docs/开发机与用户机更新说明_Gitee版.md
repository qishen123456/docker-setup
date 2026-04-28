# 开发机与用户机更新说明（Gitee版）

更新时间：2026-04-28

适用场景：

- 你的电脑是开发机，负责改代码、调试、发版本
- 别人的电脑是用户机，负责拉版本、启动系统、正常使用
- 代码仓库使用 Gitee
- 项目未来采用 Docker / Docker Compose 方式运行

---

## 1. 先说最核心的一句话

以后这套项目的更新方式，不是去用户电脑上手工改文件。

而是：

1. 你在开发机改代码
2. 你把代码提交到 Gitee
3. 用户机拉取最新代码
4. 用户机执行 `docker compose up -d --build`
5. 新版本生效

你可以把它理解成：

- 开发机负责“做菜”
- 用户机负责“热菜上桌”

---

## 2. 角色怎么分

### 2.1 开发机负责什么

开发机负责：

- 改前端代码
- 改后端代码
- 本地调试
- 验证功能正常
- 提交到 Gitee
- 决定哪个版本给用户使用

### 2.2 用户机负责什么

用户机负责：

- 从 Gitee 拉代码
- 启动 Docker 容器
- 使用系统
- 遇到问题时回退到上一个稳定版本

用户机不需要做这些事：

- 不需要改代码
- 不需要安装 Python 开发环境
- 不需要安装 Node 开发环境
- 不需要本地手工搭 PostgreSQL 开发环境

---

## 3. 推荐的仓库使用方式

推荐至少保留这两个分支：

- `main`
  作为稳定分支，用户机默认使用它
- `dev`
  作为开发分支，你平时先往这里提交

如果你现在不想搞这么复杂，也可以先只用一个 `main` 分支。

最简单的做法是：

- 你在开发机本地改好
- 本地验证通过
- 直接推送到 `main`
- 用户机再拉取 `main`

如果以后项目更正式，再升级为：

- `dev` 日常开发
- `main` 稳定发布

---

## 4. Gitee 下的推荐发布流程

### 4.1 开发机日常开发

在开发机上：

```powershell
git pull
```

改完代码后：

```powershell
git add .
git commit -m "优化问数页面与执行链路"
git push origin main
```

如果你后面采用 `dev` 分支，则是：

```powershell
git add .
git commit -m "优化问数页面与执行链路"
git push origin dev
```

然后等验证通过，再把 `dev` 合并到 `main`。

---

## 5. 用户机怎么更新

### 5.1 最简单的更新方式

用户机进入项目目录后，执行：

```powershell
git pull
docker compose up -d --build
```

这两句的意思分别是：

- `git pull`
  把 Gitee 上的最新代码拉下来
- `docker compose up -d --build`
  按最新代码重新构建并启动服务

这就是以后用户机最常用的更新方式。

### 5.2 如果只是重启，不更新代码

```powershell
docker compose up -d
```

### 5.3 如果要停服务

```powershell
docker compose down
```

### 5.4 如果要看日志

```powershell
docker compose logs -f
```

---

## 6. 最推荐的“稳定发布”方式

如果你不希望用户机每次都拿到最新开发代码，推荐你发“版本号”。

比如：

- `v1.0.0`
- `v1.0.1`
- `v1.1.0`

### 6.1 开发机打版本标签

当你确认一个版本稳定后，在开发机执行：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

以后又出了新稳定版本：

```powershell
git tag v1.0.1
git push origin v1.0.1
```

### 6.2 用户机按版本更新

用户机可以不直接跟 `main`，而是切到某个稳定版本：

```powershell
git fetch --all --tags
git checkout v1.0.0
docker compose up -d --build
```

这样做的好处是：

- 用户机更稳定
- 你可以控制谁用哪个版本
- 出问题时更容易回退

---

## 7. 出问题怎么回退

这是最重要的一块，建议你以后一定养成“发版本标签”的习惯。

假设用户机升级到 `v1.0.1` 后有问题，要回退到 `v1.0.0`：

```powershell
git fetch --all --tags
git checkout v1.0.0
docker compose up -d --build
```

这样就能快速回退到旧版本。

如果你没有打标签，只靠 `main` 更新，那回退会麻烦很多。

所以强烈建议：

- 稳定版本一定打 tag
- 用户机优先使用 tag，而不是直接跟开发中的代码

---

## 8. 你以后最省心的工作流

### 8.1 方案 A：最简单，适合当前阶段

开发机：

1. 改代码
2. 本地验证
3. `git push origin main`

用户机：

1. `git pull`
2. `docker compose up -d --build`

优点：

- 简单
- 上手快

缺点：

- 用户机会直接拿到最新代码
- 如果你刚提交的版本有问题，用户机也会跟着中招

### 8.2 方案 B：更稳，推荐后面采用

开发机：

1. 平时改 `dev`
2. 验证通过后合并到 `main`
3. 打 tag

用户机：

1. 拉 tag
2. 重新启动 Docker

优点：

- 稳定
- 容易回退
- 更像正式发布

缺点：

- 比方案 A 多一步版本管理

---

## 9. 你在新电脑上到底要做什么

如果以后你换了一台新开发电脑，流程是：

1. 安装 `Git`
2. 安装 `Docker Desktop`
3. 从 Gitee 拉代码
4. 配置 `.env`
5. 启动容器

示例：

```powershell
git clone <你的Gitee仓库地址>
cd 智能问数项目_v20260330_004926
copy .env.example .env
docker compose up -d --build
```

如果你是继续开发，就正常改代码、提交、推送。

---

## 10. 用户机第一次部署怎么做

用户机第一次部署时：

1. 安装 `Git`
2. 安装 `Docker Desktop`
3. 拉代码
4. 配置 `.env`
5. 启动容器

示例：

```powershell
git clone <你的Gitee仓库地址>
cd 智能问数项目_v20260330_004926
copy .env.example .env
docker compose up -d --build
```

以后每次更新就不用重新 clone 了，只需要：

```powershell
git pull
docker compose up -d --build
```

---

## 11. 你可以直接这样理解整个机制

以后这套项目分成两部分：

### 11.1 代码更新靠什么

靠 Git / Gitee。

也就是：

- 你提交代码
- 用户机拉代码

### 11.2 服务运行靠什么

靠 Docker Compose。

也就是：

- 把前端、后端、数据库按固定方式运行起来
- 保证换电脑后环境差异尽量小

所以不要把这两件事混在一起：

- Git 负责“更新代码”
- Docker 负责“跑代码”

---

## 12. 我对你当前阶段的建议

结合你现在的项目状态，我建议你这样走：

### 第一步

先把项目做成 Docker 可运行版。

也就是补齐：

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`

### 第二步

先用最简单的发布方式：

- 开发机推 `main`
- 用户机 `git pull + docker compose up -d --build`

### 第三步

等你稳定一段时间后，再加版本标签：

- `v1.0.0`
- `v1.0.1`
- `v1.1.0`

### 第四步

再升级成更正式的：

- `dev` 开发分支
- `main` 稳定分支
- tag 稳定发布

---

## 13. 最后一段大白话总结

以后你还是在自己的电脑上开发。

你改完以后，不是去别人电脑上手工改，而是：

1. 你把代码推到 Gitee
2. 别人电脑把代码拉下来
3. 别人电脑重新执行一次 Docker 启动命令

就这么简单。

你只要记住一句：

- 开发机负责改代码和发版本
- 用户机负责拉版本和运行系统

---

## 14. 后续如果继续推进，建议直接补的文件

如果下一步正式开始落地，建议直接补下面这些文件：

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `docs/用户机部署手册.md`
- `docs/版本发布与回退手册.md`

---

## 15. 常用命令速查

### 开发机提交代码

```powershell
git add .
git commit -m "你的修改说明"
git push origin main
```

### 用户机更新版本

```powershell
git pull
docker compose up -d --build
```

### 用户机停止服务

```powershell
docker compose down
```

### 用户机查看日志

```powershell
docker compose logs -f
```

### 开发机打稳定版本

```powershell
git tag v1.0.0
git push origin v1.0.0
```

### 用户机切换到稳定版本

```powershell
git fetch --all --tags
git checkout v1.0.0
docker compose up -d --build
```
