---
name: smartask-skill-usage-guide
description: >
  SmartAsk 项目 SKILL（AI 技能）的使用与维护操作指引。
  适用于：用户问「怎么调用 SKILL」「如何更新 SKILL」「清空上下文后怎么让 AI 识别 SKILL」「我的 SKILL 为什么没生效」「帮我新建/修改一个 SKILL」等场景。
  当用户提到 SKILL、技能、skill-name、调用技能、更新技能、技能不生效时触发。
---

# SmartAsk SKILL 使用与维护操作指引

> 本指引同时给**人类用户**阅读和**AI 助手**执行。目标是：每次清空上下文后，你都能用一句话让 AI 快速识别并调用正确的 SKILL。

---

## 1. 什么是 SKILL？

SKILL 是放在 `smartask/.agents/skills/` 下的 `SKILL.md` 文件。它把项目里的**约束、踩坑记录、运维流程、业务口径**等知识沉淀下来，让 AI 不用每次重新读大量代码也能做对事。

SKILL 本身**不修改代码、不参与运行时**，只影响 AI 的推理和行为。

---

## 2. SKILL 放在哪里？

Kimi 只认这几个位置：

| 类型 | Windows 路径 | 用途建议 |
|---|---|---|
| 项目级（推荐） | `smartask/.agents/skills/<skill-name>/SKILL.md` | 跟项目一起提交，团队共享 |
| 用户级 | `C:\Users\<你的用户名>\.config\agents\skills\<skill-name>\SKILL.md` | 个人专属，换项目也能用 |
| 用户级备选 | `C:\Users\<你的用户名>\.kimi\skills\<skill-name>\SKILL.md` | 个人备用 |

> 本项目所有 SKILL 建议统一放在 `smartask/.agents/skills/`，这样换电脑/换仓库时不会丢。

---

## 3. SKILL 文件格式

每个 SKILL 必须是一个目录 + 一个 `SKILL.md`：

```text
smartask/.agents/skills/smartask-feishu-sync-ops/
└── SKILL.md
```

`SKILL.md` 最顶部必须有 YAML frontmatter：

```yaml
---
name: smartask-feishu-sync-ops
description: >
  SmartAsk 飞书多维表数据同步的运维、配置与排查。
  适用于：新增/修改飞书同步配置、手动触发同步、验证同步结果、处理「改了链接仍同步旧表」、全量同步清表、同步重复数据、定时任务不更新、同步状态异常等问题。
  当用户提到「飞书同步」「feishu_sync」「同步任务」「清表」「TRUNCATE」「同步链接改了没用」「同步重复」「靳锋重复」时触发。
---
```

### 3.1 name 规则

- 必须和文件夹名完全一致。
- 只能用小写字母、数字、连字符 `-`。
- 建议命名空间：`smartask-<主题>-<动作>`，例如 `smartask-feishu-sync-ops`。

### 3.2 description 规则（最重要）

`description` 是 AI 判断是否调用该 SKILL 的唯一依据。写得好不好直接决定 SKILL 生不生效。

**差示例：**

```yaml
description: 这是一个飞书同步技能。
```

**好示例：**

```yaml
description: >
  SmartAsk 飞书多维表数据同步的运维、配置与排查。
  适用于：新增/修改飞书同步配置、手动触发同步、验证同步结果、处理「改了链接仍同步旧表」、全量同步清表、同步重复数据、定时任务不更新、同步状态异常等问题。
  当用户提到「飞书同步」「feishu_sync」「同步任务」「清表」「TRUNCATE」「同步链接改了没用」「同步重复」「靳锋重复」时触发。
```

**description 写作原则：**

- 第一句说清 SKILL 是做什么的。
- 列出具体适用场景（用户怎么问会触发）。
- 列出关键词（飞书同步、TRUNCATE、清表、重复等）。
- 不要写得太抽象，也不要和现有 SKILL 重叠。

---

## 4. 清空上下文后，如何快速调用 SKILL？

### 方法一：直接说主题（最自然）

只要你的问题匹配 SKILL 的 `description`，AI 会自动加载：

> “飞书同步改了链接还是同步旧表怎么办？”

AI 会自动读取 `smartask-feishu-sync-ops`。

### 方法二：点名 SKILL（最准确）

如果你希望强制使用某个 SKILL，直接说出名字：

> “用 smartask-feishu-sync-ops 帮我排查飞书同步重复数据。”

### 方法三：说“按 SKILL 来”

> “按 smartask-runtime-migration 的指引，帮我导出运行态配置。”

### 快速识别模板

清空上下文后，你可以用下面任意一种句式开头：

| 你想做的事 | 你可以这样说 |
|---|---|
| 排查飞书同步 | “飞书同步……” / “用 smartask-feishu-sync-ops……” |
| 导入导出运行态配置 | “导出 runtime bundle” / “用 smartask-runtime-migration……” |
| 了解项目约束 | “这个项目有什么约束？” / “smartask-global-constraints 里怎么说？” |
| 排名/TopN 问数异常 | “前三返回了全部” / “用 smartask-ranking-debug……” |
| 更新 SKILL | “我改了代码，帮我更新 SKILL” / “按 smartask-skill-maintenance……” |

---

## 5. SKILL 生效 checklist

如果你发现 SKILL 没生效，按这个顺序检查：

1. **位置对不对？**
   - 是否在 `smartask/.agents/skills/<skill-name>/SKILL.md`？

2. **文件名对不对？**
   - 必须叫 `SKILL.md`，不能叫 `skill.md`、`Skill.md`、`README.md`。

3. **frontmatter 有没有？**
   - 最顶部必须有 `---` 包裹的 `name` 和 `description`。

4. **name 和文件夹名一致吗？**
   - 文件夹 `smartask-feishu-sync-ops/` 里的 `name` 必须是 `smartask-feishu-sync-ops`。

5. **description 是否包含你的关键词？**
   - 如果你的问题是“飞书链接改了没用”，description 里要有“飞书同步”“链接”“旧表”等词。

6. **是否开的是新会话？**
   - SKILL 在会话启动时扫描。新增或修改 SKILL 后，要**重新打开工作区或开新会话**才生效。

7. **是否和其他 SKILL 描述冲突？**
   - 如果两个 SKILL 的 description 都在说同一件事，AI 可能选错。

---

## 6. 改了代码，如何更新 SKILL？

### 6.1 先判断要不要更新

不是所有代码改动都需要更新 SKILL。参考 `smartask-skill-maintenance` 的判断标准：

**需要更新：**

- 修复了一个反复出现的坑。
- 新增/修改了运维操作流程。
- 项目级约束变化（目录、编码、Docker 等）。
- 配置语义变化（例如 `.env` 不再覆盖某些字段）。

**不需要更新：**

- 一次性 bug 修复。
- 临时调试脚本。
- 某个具体问数问题的 prompt/SQL 调整。
- 还在剧烈变动的实验性功能。

### 6.2 更新流程

**Step 1：找到对应 SKILL**

查看 `smartask/.agents/skills/` 下所有 SKILL.md 的 `description`，选主题最匹配的一个。

**Step 2：修改 SKILL.md**

- 如果是新增一个坑，追加到「踩坑记录」或「常见坑」小节。
- 如果是流程变更，更新对应操作步骤。
- 如果旧内容完全过时，直接替换。

**Step 3：检查 frontmatter**

- `name` 和文件夹名一致。
- `description` 仍能准确触发；如果适用范围变了，重写 description。

**Step 4：同步全局索引**

打开 `smartask/.agents/skills/smartask-global-constraints/SKILL.md`，在「本项目已封装的技能索引」里确认该 SKILL 已列出。

**Step 5：验证触发**

新开一个会话，用一句用户可能问的话测试：

> “飞书同步改了链接还是同步旧表怎么办？”

如果 AI 回答里出现了 SKILL 里的关键知识点，说明生效。

### 6.3 常用修改命令

```bash
# 查看所有 SKILL
cd smartask
ls .agents/skills/

# 编辑某个 SKILL（用你喜欢的编辑器）
code .agents/skills/smartask-feishu-sync-ops/SKILL.md

# 编辑全局索引
code .agents/skills/smartask-global-constraints/SKILL.md
```

---

## 7. 如何新建一个 SKILL？

### 7.1 触发条件

满足以下全部条件才新建：

- 出现了一个独立的、反复出现的主题。
- 现有 SKILL 无法自然覆盖。
- 内容足够多（>100 行）或足够重要。

### 7.2 创建步骤

**Step 1：命名**

```text
smartask-<主题>-<动作>
```

例如：`smartask-frontend-cache-guide`、`smartask-history-recovery`。

**Step 2：创建目录和文件**

```bash
cd smartask
mkdir -p .agents/skills/smartask-example-skill
touch .agents/skills/smartask-example-skill/SKILL.md
```

**Step 3：写入内容**

参考现有 SKILL 的格式：

```markdown
---
name: smartask-example-skill
description: >
  一句话说明这是做什么的。
  适用于：场景1、场景2、场景3。
  当用户提到「关键词1」「关键词2」「关键词3」时触发。
---

# 标题

## 1. 核心文件

- `smartask/backend/xxx.py`
- `smartask/config/xxx.json`

## 2. 操作步骤

1. ...
2. ...
3. ...

## 3. 常见坑

...
```

**Step 4：注册到全局索引**

在 `smartask/.agents/skills/smartask-global-constraints/SKILL.md` 的「本项目已封装的技能索引」里新增一行。

**Step 5：开新会话验证**

---

## 8. 快速模板

### 8.1 新建 SKILL 模板

```markdown
---
name: smartask-<name>
description: >
  SmartAsk XXX 的说明。
  适用于：场景1、场景2。
  当用户提到「关键词1」「关键词2」时触发。
---

# SmartAsk XXX

## 1. 核心文件

- `smartask/backend/xxx.py`
- `smartask/frontend/src/xxx.vue`

## 2. 适用场景

...

## 3. 操作步骤

...

## 4. 常见坑

...
```

### 8.2 更新 SKILL 时的描述检查模板

改完 SKILL 后，用下面问题自测：

- 我的问题里出现哪些词时，应该触发这个 SKILL？
- 这些词是否都写进了 `description`？
- 有没有和别的 SKILL description 重叠？
- `name` 和文件夹名是否一致？

---

## 9. 常见误区

### 误区 1：SKILL 会出现在聊天界面列表里

**不会。** SKILL 是自动触发的，不会以按钮或列表形式展示。你只能通过“说对关键词”或“点名 SKILL”来调用。

### 误区 2：SKILL 修改后立刻生效

**不会立刻生效。** 需要**新开一个会话**或**重新加载工作区**才会重新扫描。

### 误区 3：把 SKILL 当成代码注释

SKILL 是给 AI 的“领域知识”，不是代码注释。不要把每个函数的实现细节都写进 SKILL。

### 误区 4：一个 SKILL 包罗万象

SKILL 越小越聚焦，触发越准确。不要把飞书同步、历史管理、前端部署全塞进一个 SKILL。

---

## 10. 本项目 SKILL 索引

| SKILL | 用途 | 触发关键词 |
|---|---|---|
| `smartask-global-constraints` | 项目通用约束、Docker/UTF-8、踩坑记录 | 项目约束、Docker、UTF-8、踩坑 |
| `smartask-ranking-debug` | 排名/TopN 问数效果排查 | 前三、排名、TopN、返回全部、标题重复 |
| `smartask-feishu-sync-ops` | 飞书同步运维 | 飞书同步、同步任务、清表、TRUNCATE、同步重复 |
| `smartask-runtime-migration` | 运行态配置迁移 | runtime bundle、备份配置、迁移配置、config 丢失 |
| `smartask-skill-maintenance` | 代码改动后更新 SKILL 的判断标准 | 更新 SKILL、维护技能、改了代码 SKILL |
| `smartask-skill-usage-guide` | SKILL 使用与维护操作指引（本指引） | SKILL、技能、调用技能、更新技能、技能不生效 |

---

## 11. 一句话总结

> **清空上下文后，想调用 SKILL：直接说主题或点名 SKILL。**
>
> **改了代码后，想更新 SKILL：判断是否是复用性知识 → 改对应 SKILL.md → 检查 name/description → 同步全局索引 → 开新会话验证。**
