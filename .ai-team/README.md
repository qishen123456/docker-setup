# .ai-team/ — 全栈研发专家团项目资产

一套**框架无关**的 9 角色全栈研发专家团资产，供 SmartAsk 项目内的 AI 工具和代码直接调用，不依赖 WorkBuddy 平台运行时。

## 这是什么

从 WorkBuddy 专家包 `fullstack-dev-team` 萃取的框架无关副本，包含：

| 文件 | 用途 |
|---|---|
| `team-config.yaml` | 机器可读的单一事实来源：角色注册表、SOP 编排、工作流路由、上下文规则、质量门禁 |
| `agents/*.md` | 9 个角色的纯 prompt 模板（已去除 WorkBuddy 专属 frontmatter，任何 LLM 可直接作为 system prompt 使用） |

## 怎么用

### AI 工具消费

在仓库根目录已有 `AGENTS.md` 项目公约。需要某角色能力时，读取 `agents/<角色>.md` 作为 system prompt 注入即可。

主理人文件 `agents/fullstack-dev-team-lead.md` 包含完整 SOP 与路由表，可独立驱动整个流程。

### 代码消费

```python
import yaml

cfg = yaml.safe_load(open('.ai-team/team-config.yaml'))

# 1. 获取某角色的 prompt
member = next(m for m in cfg['members'] if m['id'] == 'fullstack-dev-backend')
system_prompt = open(f".ai-team/{member['prompt_file']}").read()

# 2. 按 SOP 阶段编排
for phase in cfg['sop']['phases']:
    if phase['condition'] == 'brownfield' and not is_brownfield:
        continue
    for member_id in phase['members']:
        # 加载该角色 prompt，注入上下文，调用 LLM
        ...

# 3. 单点直调路由
question_type = "接口/数据库/性能"
target = cfg['routing_table'][question_type]  # → fullstack-dev-backend
```

### 在 WorkBuddy 中消费

专家包源头在 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/fullstack-dev-team/`，已注册到 WorkBuddy 专家中心，可直接以专家团形式对话使用。

## 同步

专家包是源头，本目录是副本。专家包变更后：

```bash
bash scripts/sync-from-expert-pack.sh
```

## 角色一览

| Agent ID | 花名 | 职业 |
|---|---|---|
| `fullstack-dev-team-lead` | 宋必达 | 交付总监（主理人） |
| `fullstack-dev-pm` | 文清源 | 产品经理 |
| `fullstack-dev-designer` | 简致远 | UI/UX 设计师 |
| `fullstack-dev-architect` | 梁定邦 | 系统架构师 |
| `fullstack-dev-frontend` | 叶明轩 | 前端工程师 |
| `fullstack-dev-backend` | 岳承基 | 后端工程师 |
| `fullstack-dev-reviewer` | 贺明察 | 代码审查工程师 |
| `fullstack-dev-qa` | 严守真 | 测试工程师 |
| `fullstack-dev-devops` | 常升平 | DevOps 工程师 |
