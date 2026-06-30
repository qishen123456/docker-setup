---
name: smartask-skill-maintenance
description: >
  SmartAsk 项目代码变更后，如何同步维护对应的 AI SKILL.md。
  适用于：用户说「我改了代码，SKILL 也要更新」「帮我维护技能」「这段改动要不要写进 SKILL」等场景。
  指导判断哪些变更需要沉淀为技能、更新现有 SKILL 还是新建 SKILL，并保持 name/description/frontmatter 与代码一致。
---

# SmartAsk SKILL 维护指南

## 1. SKILL 的定位

SKILL.md 是给 AI 助手的“领域记忆”，只存放** reusable（可复用）** 且**非显而易见**的知识：

- 项目级约束（Docker/UTF-8/目录结构）
- 反复踩坑的修复方案（历史清空 race、飞书链接被 .env 覆盖）
- 运维/操作流程（手动同步、配置迁移、构建验证）
- 复杂但稳定的业务规则（维度层级、指标口径）

**不要**把下面内容写进 SKILL：

- 一次性 bug 修复，后续不会再遇到。
- 临时调试脚本或临时配置。
- 已经自解释的代码实现细节。
- 还在剧烈变动的实验性功能。

## 2. 代码改动后是否需要更新 SKILL 的判断清单

| 改动类型 | 是否需要更新 SKILL | 说明 |
|---|---|---|
| 修复了一个反复出现的坑 | 是 | 沉淀到对应 SKILL，避免下次重踩。 |
| 新增/修改了运维操作流程 | 是 | 例如新增「手动同步后必须 TRUNCATE」的流程。 |
| 修改了项目级约束 | 是 | 例如目录结构、编码、Docker 运行方式变化。 |
| 修改了配置语义或默认值 | 是 | 例如 `.env` 不再覆盖某些字段。 |
| 修改了通用组件/工具函数签名 | 视情况 | 如果影响多个调用方，更新相关 SKILL 里的示例。 |
| 修改了某个具体问数问题的 prompt/SQL | 否 | 这类细节应通过测试/golden SQL 保证，不写入 SKILL。 |
| 纯 UI 样式微调 | 否 | 除非涉及构建/缓存等 reusable 知识。 |
| 临时加日志/debug | 否 | 上线后通常会回滚。 |

## 3. 更新现有 SKILL 的流程

1. **定位受影响 SKILL**
   查看 `.agents/skills/` 下所有 SKILL.md 的 `description`，找出主题最匹配的一个或多个。

2. **更新正文**
   - 如果旧内容已过时，直接替换。
   - 如果只是新增一个坑，追加到「踩坑记录」或「常见坑」小节。
   - 保持 SKILL.md 主体不超过 500 行；过长的参考材料放到 `references/`。

3. **检查 frontmatter**
   - `name` 必须和文件夹名完全一致。
   - `description` 必须仍然能准确触发。如果 SKILL 的适用范围变了，重写 description，加入新的关键词和场景。

4. **更新全局索引**
   如果新增或重命名了 SKILL，在 `smartask-global-constraints/SKILL.md` 的「本项目已封装的技能索引」里同步更新。

5. **验证触发**
   用一句用户可能问的话测试 description 是否会被命中，例如：

   > “飞书同步改了链接还是旧表怎么办？”

   如果这句话更该触发 `smartask-feishu-sync-ops`，确保 `smartask-global-constraints` 没有抢答。

## 4. 需要新建 SKILL 的场景

当满足以下全部条件时，新建一个 SKILL：

- 出现了一个独立的、反复出现的主题。
- 现有 SKILL 的 `description` 无法自然覆盖它。
- 内容足够多（>100 行）或足够重要，值得独立维护。

新建步骤：

1. 命名：`smartask-<主题>-<动作>`，例如 `smartask-feishu-sync-ops`。
2. 在 `.agents/skills/<name>/` 下创建 `SKILL.md`。
3. 写好 frontmatter 和正文。
4. 在 `smartask-global-constraints/SKILL.md` 的技能索引里注册。

## 5. 不要重复造轮子

- 飞书同步相关内容 → 放进 `smartask-feishu-sync-ops`。
- 运行态配置迁移 → 放进 `smartask-runtime-migration`。
- 通用约束/踩坑 → 放进 `smartask-global-constraints`。
- 排名/TopN 问数效果 → 放进 `smartask-ranking-debug`。
- SKILL 自身维护 → 放进 `smartask-skill-maintenance`（本技能）。

## 6. 与问数代码的边界

**SKILL 维护不涉及修改问数核心代码**（`four_agent_ask.py`、SQL 生成、prompt 工程等）。

如果代码改动是问数效果相关的，优先通过以下方式保证质量：

- 更新 `backend/tests/` 中的回归测试。
- 更新 `config/confirmed_behaviors_baseline.md`。
- 更新对应数据集的 `common_questions` / `golden_sql_samples`。

只有当上面积累成“AI 必须知道的约束/套路”时，才考虑写进 SKILL。

## 7. 更新 SKILL 后的检查项

- [ ] `name` 与文件夹名一致。
- [ ] `description` 包含触发关键词和场景。
- [ ] 正文无 BOM，UTF-8 编码。
- [ ] 超过 500 行的内容已拆到 `references/`。
- [ ] `smartask-global-constraints` 技能索引已同步。
- [ ] 没有与现有 SKILL 重复或冲突的描述。
