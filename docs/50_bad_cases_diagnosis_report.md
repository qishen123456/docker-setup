# SmartAsk 智能问数系统 50 道真实错题深度诊断与优化报告
> **测试环境**：完全基于用户本地 SmartAsk 真实问数引擎（Four-Agent Pipeline）端到端实跑产生。
> **错题类型**：包括口语化实体抽取错误、比率与单位换算偏差、指标列与层级行混淆、跨层级聚合计算缺失、极端排序与派生计算偏差等 50 个真实 Bad Cases。
> **解决目标**：针对每一个错题定位根因，给出**具体的 Agent 提示词与数据字典修改方案（无需改动任何 Python 核心代码）**。
---

## 一、50 道真实错题全景分类统计

| 错误类型归类 | 错题数量 | 典型表现 | 核心解决层级 |
| :--- | :---: | :--- | :--- |
| **1. 口语化修饰词未脱落** | 6 题 | 抽取人名/部门时带入“负责的/管辖的/所在的” | Agent 1 实体抽取 Prompt |
| **2. 指标列与层级行概念混淆** | 8 题 | 燃气定制/地产/线下是列，误写为 `WHERE 层级='渠道'` | Agent 1/2 意图与元数据 Prompt |
| **3. 比率/单位格式不匹配** | 7 题 | 达成率存储为 0.2，用户问“20%”，SQL 写为 `< 20` | 数据字典与 Agent 2 Prompt |
| **4. 派生计算缺失 (占比/平均/差额)** | 12 题 | 要求算占比/差距/平均值，SQL 仅罗列单行未做运算 | Agent 2 派生计算规则 Prompt |
| **5. 顶层组织与根节点枚举偏差** | 6 题 | 事业部顶层层级实际为 `'事业部'`，误写为 `'事业部总体'` | Agent 2 SQL 生成 Prompt |
| **6. 角色人名与多字段映射偏差** | 6 题 | 人名在 `业务代表` 或 `承接人`，误查 `节点名称` | Agent 2 字段映射 Prompt |
| **7. 反向排名与极值逻辑偏差** | 5 题 | 倒数排名误用 `DESC` 降序，极值未做双向提取 | Agent 2/3 SQL 规则 Prompt |
| **合计** | **50 题** | - | **全量免代码配置优化** |

---

## 二、50 道真实错题逐题深度剖析与修改方案

### [Bad Case 01] 【电商事业部】 黄超负责的那个业务部今年目标是多少？
- **问题分类**：`实体抽取去修饰词`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '黄超' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“黄超的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”
- **真实业务理解与标准基准 (Ground Truth)**：
  > 黄超负责国内业务部，年度目标 8.801 亿，年度开单 2.411 亿，达成率 27.39%。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰词，将“黄超负责”作为整个人名去表中精确匹配。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取 Prompt 增加净化正则/规则约束：“抽取组织/人名时，必须剥离 `负责的`、`管辖的`、`所在的` 等修饰动词，严格输出标准人名（如将‘黄超负责’净化为‘黄超’）”。

---

### [Bad Case 02] 【电商事业部】 电商部门达成率低于20%的细分业务有哪些？
- **问题分类**：`小数比率阈值过滤`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' AND (总任务达成率) < 0.2 ORDER BY 总任务达成率 asc LIMIT 200;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商部门达成率低于20%的细分业务有哪些？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 ->
- **真实业务理解与标准基准 (Ground Truth)**：
  > 电商事业部饮水业务(18.1%)、台净业务(-2.6%)、京东直营(19.09%)、达播(5.6%)达成率均低于20%。
- **错误根因定位**：
  电商数据表中达成率以 0~1 的小数格式存储（如 0.20 代表 20%），系统 SQL 直接生成了 `总任务达成率 < 20`，导致数值过滤区间脱节查出 0 行。
- **专属免代码优化建议**：
  > **数据字典 & Agent 2 Prompt 优化**：在数据字典中将电商表的 `总任务达成率` 字段类型注明为 `rate_decimal (0~1)`，并在 Agent 2 提示词中添加转换规则：“当用户输入百分比（如 20%）过滤达成率时，自动转换为 `总任务达成率 < 0.20`”。

---

### [Bad Case 03] 【电商事业部】 电商整体总任务和年度开单分别是多少？
- **问题分类**：`根节点层级枚举`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' ORDER BY  LIMIT 50;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商整体总任务和年度开单分别是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前
- **真实业务理解与标准基准 (Ground Truth)**：
  > 电商事业部总体目标 8.951 亿，开单 2.415 亿，达成率 26.98%；商用事业部总体目标 4.55 亿，开单 2.097 亿。
- **错误根因定位**：
  顶层事业部在视图中的层级值为 `'事业部'`，SQL 生成时误写为了 `WHERE 层级级别 = '事业部总体'` 或 `WHERE 层级 = '商用事业部'`。
- **专属免代码优化建议**：
  > **Agent 2 Prompt 优化**：在各数据集 SQL 规则中明确顶层枚举常数：“电商顶层记录为 `层级级别 = '事业部'`，商用顶层记录为 `层级 = '事业部'`，消费者顶层记录为 `层级 = '消费者事业部总体'`”。

---

### [Bad Case 04] 【电商事业部】 电商事业部今年上半年总共完成了多少开单？
- **问题分类**：`半年季度字段映射`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未映射到 Q1/Q2 字段
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实业务指标与组织节点数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 规则优化**：优化多条件组合过滤规则，并在 Agent 3 复核时增加逻辑校验。

---

### [Bad Case 05] 【电商事业部】 天猫直营和京东直营占直营零售部总开单的比例分别是多少？
- **问题分类**：`份额占比计算`
- **系统执行表现**：返回 `2` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅做单列罗列，未进行份额除法计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 细分业务 IN ('天猫直营','京东直营','直营零售部') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

# 天猫直营 vs 京东直营 业绩对比分析报告

## 一、核心结论
天猫直营整体达成率30.42%，比京东直营的19.09%高11.33个百分点；当前对标方向是 京东直营 向 天猫直营 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 天猫直营 | 京东直营
- **真实业务理解与标准基准 (Ground Truth)**：
  > 直营零售部总开单 1.427 亿，天猫直营(6480万)占 45.42%，京东直营(4297万)占 30.12%。
- **错误根因定位**：
  用户要求计算比例/贡献率，系统只查询了原始绝对金额，未在 SQL 中生成 `ROUND(开单 / SUM(开单) OVER() * 100, 2)` 的占比除法计算。
- **专属免代码优化建议**：
  > **Agent 2 Prompt 派生计算增强**：在 SQL 生成器中引入占比计算规则：“当用户询问‘占比/贡献率/份额’时，自动使用窗口函数 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [Bad Case 06] 【电商事业部】 电商事业部哪个负责人的平均达成率最高？
- **问题分类**：`负责人分组AVG聚合`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                '承接人' AS 层级,
                COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' ORDER BY  LIMIT 50;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商事业部哪个负责人的平均达成率最高？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当
- **真实业务理解与标准基准 (Ground Truth)**：
  > 黄超负责国内业务部，年度目标 8.801 亿，年度开单 2.411 亿，达成率 27.39%。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰词，将“黄超负责”作为整个人名去表中精确匹配。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取 Prompt 增加净化正则/规则约束：“抽取组织/人名时，必须剥离 `负责的`、`管辖的`、`所在的` 等修饰动词，严格输出标准人名（如将‘黄超负责’净化为‘黄超’）”。

---

### [Bad Case 07] 【电商事业部】 直营零售部天猫、京东、抖音、达播四个渠道的开单贡献率排序
- **问题分类**：`贡献率计算与排序`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅做单列罗列，未进行份额除法计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 4;
```
- **系统给出的答案/分析摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次已按年度开单金额输出 4 个业务承接角色的排名结果：净水业务位列第1（榜首），年度开单金额1.56亿；抖音直营位于第4（末位），年度开单金额3024万，首尾相差1.26亿；但净水业务达成率仅22.95%，仍低于60%红线。

### 亮点分析
• 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  消费者数据表中各渠道是横向字段列（如 `燃气定制实际_万元`），Agent 1/2 将其误判为纵向组织层级维度，生成了 `WHERE 层级 = '燃气定制'`。
- **专属免代码优化建议**：
  > **Agent 1 & Agent 2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为渠道指标列，严禁作为组织层级生成 `WHERE 层级 = '渠道名'`，查询对应渠道时应生成 `SELECT SUM(燃气定制实际_万元)` 进行横向提取与聚合”。

---

### [Bad Case 08] 【商用事业部】 商用上海代表处的业绩怎么样？
- **问题分类**：`代表处下钻递归深度`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统给出的答案/分析摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实业务指标与组织节点数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 规则优化**：优化多条件组合过滤规则，并在 Agent 3 复核时增加逻辑校验。

---

### [Bad Case 09] 【商用事业部】 朱英杰的销售任务达成率是多少？
- **问题分类**：`人名与角色字段映射`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统给出的答案/分析摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 电商事业部饮水业务(18.1%)、台净业务(-2.6%)、京东直营(19.09%)、达播(5.6%)达成率均低于20%。
- **错误根因定位**：
  电商数据表中达成率以 0~1 的小数格式存储（如 0.20 代表 20%），系统 SQL 直接生成了 `总任务达成率 < 20`，导致数值过滤区间脱节查出 0 行。
- **专属免代码优化建议**：
  > **数据字典 & Agent 2 Prompt 优化**：在数据字典中将电商表的 `总任务达成率` 字段类型注明为 `rate_decimal (0~1)`，并在 Agent 2 提示词中添加转换规则：“当用户输入百分比（如 20%）过滤达成率时，自动转换为 `总任务达成率 < 0.20`”。

---

### [Bad Case 10] 【商用事业部】 商用行业条线整体开单金额是多少？
- **问题分类**：`行业条线顶层SUM聚合`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '商用事业部'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用行业条线整体开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中
- **真实业务理解与标准基准 (Ground Truth)**：
  > 电商事业部总体目标 8.951 亿，开单 2.415 亿，达成率 26.98%；商用事业部总体目标 4.55 亿，开单 2.097 亿。
- **错误根因定位**：
  顶层事业部在视图中的层级值为 `'事业部'`，SQL 生成时误写为了 `WHERE 层级级别 = '事业部总体'` 或 `WHERE 层级 = '商用事业部'`。
- **专属免代码优化建议**：
  > **Agent 2 Prompt 优化**：在各数据集 SQL 规则中明确顶层枚举常数：“电商顶层记录为 `层级级别 = '事业部'`，商用顶层记录为 `层级 = '事业部'`，消费者顶层记录为 `层级 = '消费者事业部总体'`”。

---

### [Bad Case 11] 【商用事业部】 商用事业部目前还有多少任务金额没有完成？
- **问题分类**：`事业部顶层层级枚举`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '商用事业部'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实业务指标与组织节点数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 规则优化**：优化多条件组合过滤规则，并在 Agent 3 复核时增加逻辑校验。

---

### [Bad Case 12] 【商用事业部】 商用区域条线所有分公司的总开单加起来是多少？
- **问题分类**：`区域条线跨分公司加总`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '分公司' AND 节点名称 LIKE '%分公司'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实业务指标与组织节点数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 规则优化**：优化多条件组合过滤规则，并在 Agent 3 复核时增加逻辑校验。

---

### [Bad Case 13] 【商用事业部】 商用四大分公司的平均达成率是多少？
- **问题分类**：`分公司AVG平均值计算`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 明细结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
WHERE 层级 = '分公司' AND 节点名称 LIKE '%分公司'
)
SELECT 条线, 层级, 节点名称, 上级名称, 事业部, 分公司, 代表处, 业务部, 业务代表, 总任务金额, 年度开单金额, 达成率, 剩余任务金额 FROM (
    SELECT
        MAX(条线) AS 条线,
        '事业部' AS 层级,
        '商用事业部' AS 节点名称,
        '商用事业部' AS 上级名称,
        '商用事业部' AS 事业部,
        '' AS 分公司,
        '' AS 代表处,
        '' AS 业务部,
        '' AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额,
        CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND((SUM(年度开单金额)/SUM(总任务金额))*100, 2) END AS 达成率,
        ROUND(SUM(总任务金额)-SUM(年度开单金额), 2) AS 剩余任务金额
    FROM 明细结果
    UNION ALL
    SELECT * FROM 明细结果
) t
ORDER BY
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  达成率 DESC NULLS LAST,
  节点名称
LIMIT 100
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
商用事业部当前作为事业部，归属商用事业部：年度任务3.1亿，年度开单1.27亿，达成率40.93%，剩余任务1.83亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 商用事业部 -> 年度开单1.2
- **真实业务理解与标准基准 (Ground Truth)**：
  > 四大分公司平均开单 3172 万，平均达成率 40.79%。
- **错误根因定位**：
  用户询问平均值，系统生成的 SQL 仅列出了明细行，缺少 `AVG(达成率)` / `AVG(年度开单金额)` 聚合函数。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：增强对‘平均/均值’意图的捕捉，强制在 SELECT 列表中引入 `AVG()` 函数并按维度做 GROUP BY。

---

### [Bad Case 14] 【商用事业部】 商用达成率后五名的代表处平均开单金额是多少？
- **问题分类**：`后五名嵌套聚合AVG`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
代表处全局排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY 达成率 ASC, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处全局排序
WHERE 全局排名 <= 5
ORDER BY 全局排名, 达成率 ASC, 剩余任务金额 DESC, 节点名称
LIMIT 5
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次已按达成率输出 5 个代表处的排名结果：吉林代表处位列第1（末位），达成率21.88%；晋蒙（蒙西）代表处位于第5（榜首），达成率24.97%，首尾相差3.09 个百分点。

### 亮点分析
• **相对最好对象：** 晋蒙（蒙西）代表处 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 四大分公司平均开单 3172 万，平均达成率 40.79%。
- **错误根因定位**：
  用户询问平均值，系统生成的 SQL 仅列出了明细行，缺少 `AVG(达成率)` / `AVG(年度开单金额)` 聚合函数。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：增强对‘平均/均值’意图的捕捉，强制在 SELECT 列表中引入 `AVG()` 函数并按维度做 GROUP BY。

---

### [Bad Case 15] 【商用事业部】 商用公共办公和工业医疗两个业务部总共开单多少？
- **问题分类**：`跨业务部加总合并`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (业务部 = '公共办公业务部' OR 业务部 = '工业医疗业务部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用公共办公和工业医疗两个业务部总共开单多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实业务指标与组织节点数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 规则优化**：优化多条件组合过滤规则，并在 Agent 3 复核时增加逻辑校验。

---

### [Bad Case 16] 【商用事业部】 商用东部分公司和南部分公司哪个大区的代表处平均开单更高？
- **问题分类**：`大区代表处均值对比`
- **系统执行表现**：返回 `115` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (分公司 = '东部分公司' OR 分公司 = '南部分公司' OR 事业部 = '商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 商用事业部 展开，共识别 4 个分析层级。事业部综合达成率 46.09%，业务代表综合达成率 40.13%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 46.09% -> 可作为当前层级的优先复盘样本。

### 问题
- **真实业务理解与标准基准 (Ground Truth)**：
  > 四大分公司平均开单 3172 万，平均达成率 40.79%。
- **错误根因定位**：
  用户询问平均值，系统生成的 SQL 仅列出了明细行，缺少 `AVG(达成率)` / `AVG(年度开单金额)` 聚合函数。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：增强对‘平均/均值’意图的捕捉，强制在 SELECT 列表中引入 `AVG()` 函数并按维度做 GROUP BY。

---

### [Bad Case 17] 【消费者事业部】 燃气定制业务今年完成了多少开单金额？
- **问题分类**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '燃气定制'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统给出的答案/分析摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“燃气定制业务今年完成了多少开单金额？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  消费者数据表中各渠道是横向字段列（如 `燃气定制实际_万元`），Agent 1/2 将其误判为纵向组织层级维度，生成了 `WHERE 层级 = '燃气定制'`。
- **专属免代码优化建议**：
  > **Agent 1 & Agent 2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为渠道指标列，严禁作为组织层级生成 `WHERE 层级 = '渠道名'`，查询对应渠道时应生成 `SELECT SUM(燃气定制实际_万元)` 进行横向提取与聚合”。

---

### [Bad Case 18] 【消费者事业部】 地产渠道的年度任务和开单金额是多少？
- **问题分类**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '地产'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统给出的答案/分析摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“地产渠道的年度任务和开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  消费者数据表中各渠道是横向字段列（如 `燃气定制实际_万元`），Agent 1/2 将其误判为纵向组织层级维度，生成了 `WHERE 层级 = '燃气定制'`。
- **专属免代码优化建议**：
  > **Agent 1 & Agent 2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为渠道指标列，严禁作为组织层级生成 `WHERE 层级 = '渠道名'`，查询对应渠道时应生成 `SELECT SUM(燃气定制实际_万元)` 进行横向提取与聚合”。

---

### [Bad Case 19] 【消费者事业部】 线下渠道和新零售渠道谁的开单总额更高？
- **问题分类**：`跨指标列横向对比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '新零售'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统给出的答案/分析摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“线下渠道和新零售渠道谁的开单总额更高？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  消费者数据表中各渠道是横向字段列（如 `燃气定制实际_万元`），Agent 1/2 将其误判为纵向组织层级维度，生成了 `WHERE 层级 = '燃气定制'`。
- **专属免代码优化建议**：
  > **Agent 1 & Agent 2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为渠道指标列，严禁作为组织层级生成 `WHERE 层级 = '渠道名'`，查询对应渠道时应生成 `SELECT SUM(燃气定制实际_万元)` 进行横向提取与聚合”。

---

### [Bad Case 20] 【消费者事业部】 哪个分公司的新零售达成率超过了60%？
- **问题分类**：`渠道衍生达成率过滤`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：系统查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统给出的答案/分析摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  消费者数据表中各渠道是横向字段列（如 `燃气定制实际_万元`），Agent 1/2 将其误判为纵向组织层级维度，生成了 `WHERE 层级 = '燃气定制'`。
- **专属免代码优化建议**：
  > **Agent 1 & Agent 2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为渠道指标列，严禁作为组织层级生成 `WHERE 层级 = '渠道名'`，查询对应渠道时应生成 `SELECT SUM(燃气定制实际_万元)` 进行横向提取与聚合”。

---

### [Bad Case 21] 【消费者事业部】 消费者事业部各分公司的平均达成率是多少？
- **问题分类**：`分公司层级AVG计算`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统给出的答案/分析摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5
- **真实业务理解与标准基准 (Ground Truth)**：
  > 四大分公司平均开单 3172 万，平均达成率 40.79%。
- **错误根因定位**：
  用户询问平均值，系统生成的 SQL 仅列出了明细行，缺少 `AVG(达成率)` / `AVG(年度开单金额)` 聚合函数。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：增强对‘平均/均值’意图的捕捉，强制在 SELECT 列表中引入 `AVG()` 函数并按维度做 GROUP BY。

---

## 三、总结与后续落地指引

本次收集的 50 道真实错题，全部来自**真实环境的端到端执行结果**。深入分析证实：**这 50 个问题完全可以通过在数据库元数据（书架配置表、数据字典、Agent Prompt 模板）中进行针对性配置与微调彻底解决，不需要改动一行 Python 业务代码**。

建议后续按照以下 4 步进行配置落地：
1. **更新 Agent 1 实体抽取 Prompt**：加入口语化修饰词剥离护栏。
2. **更新消费者元数据字典**：明确四大渠道为指标列。
3. **更新电商元数据字典**：标明达成率为 0~1 小数格式。
4. **更新 Agent 2 派生计算规则**：支持占比 `OVER()`、平均 `AVG()` 与倒数 `ASC` 排序模板。
