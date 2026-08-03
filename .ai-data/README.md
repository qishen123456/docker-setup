# .ai-data/ - 数据分析与研究洞察专家团

一套**框架无关**的数据分析/研究洞察/金融分析专家团资产，与 `.ai-team/`（代码开发团队）平级。

## 这是什么

从 WorkBuddy 平台 12 个专家包（70 个角色）中整合萃取为 **10 个各司其职的专家角色**。所有 prompt 已去除平台专属 frontmatter，任何 LLM 可直接作为 system prompt 使用。

## 与 .ai-team/ 的区别

| | `.ai-team/` | `.ai-data/` |
|---|---|---|
| 定位 | 帮 SmartAsk 写代码 | 帮 SmartAsk 做数据分析/研究/金融分析 |
| 消费者 | 人 + IDE（开发者本人） | SmartAsk 系统（集成到四智能体流水线） |
| 运行环境 | 开发态 | 生产态 |
| 角色数 | 9 | 10 |
| Agent ID 前缀 | `fullstack-dev-*` | `data-team-*` |
| 当前状态 | 已复刻，可使用 | 已存入项目，尚未集成到系统 |

## 10 位专家

| 角色 | ID | 职责边界 | 融合自 |
|---|---|---|---|
| 主理人 | `data-team-lead` | 编排调度、工作流路由、合成交付 | huashu 主理人 + data-analytics 主理人 |
| 数据工程师 | `data-team-data-engineer` | 数据采集、清洗、存储、质量把关 | data-source-engineer |
| 趋势分析师 | `data-team-trend-analyst` | 时间序列、拐点、季节性、行业趋势 | huashu 趋势 + trend-researcher |
| 结构分析师 | `data-team-structure-analyst` | 占比、帕累托、集中度、指标体系 | huashu 结构 + data-stat-analyst |
| 异常侦察员 | `data-team-anomaly-analyst` | 离群检测、突变、数据质量、风险分级 | huashu 异常 + data-mining-expert |
| 算法工程师 | `data-team-ml-engineer` | 预测、聚类、推荐、特征工程 | data-ml-engineer |
| 行业研究员 | `data-team-industry-researcher` | 行业趋势、竞品、市场、政策、AI资讯 | fbsir + product-strategy + aihot + data-industry |
| 深度研究员 | `data-team-deep-researcher` | 5阶段研究流水线、Web搜索、报告 | gpt-researcher(7角色) + deep-research |
| 金融分析师 | `data-team-financial-analyst` | DCF/LBO/估值、A股、投资大师、交易决策 | financial-analysis + a-share + ai-hedge-fund + trading-agent |
| 可视化设计师 | `data-team-viz-designer` | 看板、图表选型、视觉规范、前端实现 | data-viz-designer + data-frontend-dev |

## 文件结构

```
.ai-data/
├── team-config.yaml              # 机器可读：成员注册表、工作流、路由表、门禁、上下文规则
├── README.md                     # 本文件
├── agents/                       # 10 个角色的纯 prompt 模板
│   ├── team-lead.md
│   ├── data-engineer.md
│   ├── trend-analyst.md
│   ├── structure-analyst.md
│   ├── anomaly-analyst.md
│   ├── ml-engineer.md
│   ├── industry-researcher.md
│   ├── deep-researcher.md
│   ├── financial-analyst.md
│   └── viz-designer.md
├── knowledge-base/               # 知识沉淀
│   ├── pitfalls.md               # 数据分析踩坑记录
│   ├── decisions.md              # 分析方法决策记录
│   └── patterns.md               # 重复有效的分析模式
└── checklists/                   # 审查清单
    ├── data-quality-check.md     # 数据质量校验
    ├── viz-spec-check.md         # 可视化规范校验
    └── analysis-rigor-check.md   # 分析严谨性校验
```

## 工作流

| 场景 | 走哪条 |
|---|---|
| 只问一个维度 | 单点直调（见 routing_table） |
| 一份数据全视角分析 | 三视角并行（趋势 / 结构 / 异常 -> 合成） |
| 从数据到看板 | 全链路 SOP（5 阶段） |
| 需要外部研究支撑 | 跨域协作（分析 / 研究 -> 合成） |
| 金融投资决策 | 金融分析 SOP（估值 -> 风险 -> 决策） |

## 质量门禁

6 道门禁面向"分析结论质量"：数据完整性 -> 分析方法严谨性 -> 多视角交叉验证 -> 模型可解释性 -> 可视化规范 -> 结论可溯源。详见 `team-config.yaml` 的 `quality_gates` 配置块。

## 同步说明

`.ai-data/` 从 12 个源头专家包整合而来，无自动同步脚本。源头更新时需手动比对并更新对应 `agents/*.md`。详见 `team-config.yaml` 的 `sync_note`。

## 当前状态

专家资产已存入项目，尚未集成到 SmartAsk 系统。集成设计见 `docs/data-analysis-integration-design.md`。
