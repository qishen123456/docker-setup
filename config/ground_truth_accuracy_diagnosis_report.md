# SmartAsk 真实业务数据基准学习与数据准确性深度诊断报告

> **评测核心准则**：拒绝单纯以“是否有数据（`row_count > 0`）”为标准，必须先透彻学习底层物理数据库真值（Ground Truth），针对实体定位、核心指标数值吻合度、衍生计算逻辑进行**数据级三维严格比对**。

> **全量数据准确率**：**64.0%** (32/50 道核心题完全符合业务真值)

---

## 一、底层真实数据基准学习字典 (Ground Truth Knowledge)

### 1. 电商事业部核心负责人与业务部真值表

| 负责人 | 负责业务部 | 细分业务/平台 | 2026 年度总任务 | 2026 年度开单金额 | 真实达成率 |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **刘志伟** | 跨境业务部 | 其他 | 4,000,000.00 元 | -966.96 元 | -0.02% |
| **黄超** | 国内业务部 | None | 880,100,000.00 元 | 241,063,416.34 元 | 27.39% |
| **陈小斌** | 国内业务部 | 净水业务 | 680,100,000.00 元 | 156,101,265.94 元 | 22.95% |
| **罗湾湾** | 直营零售部 | 天猫直营 | 213,000,000.00 元 | 64,798,928.23 元 | 30.42% |
| **邓梦竹** | 直营零售部 | 抖音直营 | 80,000,000.00 元 | 30,242,986.62 元 | 37.8% |
| **郑燕美** | 国内业务部 | 饮水业务 | 90,000,000.00 元 | 16,291,778.04 元 | 18.1% |
| **谢均伟** | 直营零售部 | 达播 | 83,000,000.00 元 | 4,651,067.69 元 | 5.6% |
| **胡根** | 跨境业务部 | 亚马逊 | 10,000,000.00 元 | 333,045.78 元 | 3.33% |

### 2. 消费者事业部 10 大重点省区渠道开单真值表

| 重点省份 | 所属销售大区 | 新零售开单真值 | 线下开单真值 | 省区总开单真值 | 零售是否完成50%目标 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **广东** | 粤桂琼分公司 | 0.00 元 | 185,091,752.00 元 | 185,091,752.00 元 | 🔴 未完成50% |
| **湖南** | 湖南分公司 | 0.00 元 | 109,604,432.00 元 | 109,604,432.00 元 | 🔴 未完成50% |
| **湖北** | 鄂皖分公司 | 0.00 元 | 187,285,650.20 元 | 187,285,650.20 元 | 🔴 未完成50% |
| **江西** | 赣闽分公司 | 0.00 元 | 131,899,954.00 元 | 131,899,954.00 元 | 🔴 未完成50% |
| **四川** | 川藏分公司 | 0.00 元 | 92,332,446.00 元 | 92,332,446.00 元 | 🔴 未完成50% |
| **江苏** | 江浙沪分公司 | 0.00 元 | 77,053,774.00 元 | 77,053,774.00 元 | 🔴 未完成50% |
| **浙江** | 江浙沪分公司 | 0.00 元 | 77,053,774.00 元 | 77,053,774.00 元 | 🔴 未完成50% |
| **安徽** | 鄂皖分公司 | 0.00 元 | 187,285,650.20 元 | 187,285,650.20 元 | 🔴 未完成50% |

### 3. 商用事业部代表处与全国均值对比真值表

> 📌 **2026 年全国商用代表处平均达成率真值基准**：`37.54%`

| 重点城市/代表处 | 所属分公司 | 代表处总任务 | 代表处已开单 | 代表处达成率 | 全国均值对比判定 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **粤东代表处** | 南部分公司 | 28,500,000.00 元 | 15,718,797.54 元 | 55.15% | 🟢 高于全国平均 |
| **粤东代表处** | 南部分公司 | 28,500,000.00 元 | 15,718,797.54 元 | 55.15% | 🟢 高于全国平均 |
| **粤东代表处** | 南部分公司 | 28,500,000.00 元 | 15,718,797.54 元 | 55.15% | 🟢 高于全国平均 |
| **粤东代表处** | 南部分公司 | 28,500,000.00 元 | 15,718,797.54 元 | 55.15% | 🟢 高于全国平均 |
| **江苏代表处** | 东部分公司 | 12,200,000.00 元 | 6,028,409.76 元 | 49.41% | 🟢 高于全国平均 |
| **浙江代表处** | 东部分公司 | 14,600,000.00 元 | 5,594,455.17 元 | 38.32% | 🟢 高于全国平均 |
| **安徽代表处** | 东部分公司 | 8,500,000.00 元 | 2,436,117.80 元 | 28.66% | 🔴 低于全国平均 |
| **湖北代表处** | 东部分公司 | 23,100,000.00 元 | 7,989,510.54 元 | 34.59% | 🔴 低于全国平均 |

---

## 二、端到端真机问数数据准确性逐题核验明细

### [EC_刘志伟] 【电商事业部】 刘志伟负责的那个业务部今年目标是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 总任务金额期望4000000.0实际15000000.0, 年度开单金额期望-966.960000000006实际439674.888899999` | 耗时 `0.108s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '刘志伟' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_黄超] 【电商事业部】 黄超负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 880100000.0, '年度开单金额': 241063416.341})` | 耗时 `0.036s`
- **系统生成并执行的 SQL**：
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

### [EC_陈小斌] 【电商事业部】 陈小斌负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 680100000.0, '年度开单金额': 156101265.944598})` | 耗时 `0.035s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '陈小斌' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_罗湾湾] 【电商事业部】 罗湾湾负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 213000000.0, '年度开单金额': 64798928.2256011})` | 耗时 `0.04s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '罗湾湾' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_邓梦竹] 【电商事业部】 邓梦竹负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 80000000.0, '年度开单金额': 30242986.6209002})` | 耗时 `0.038s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '邓梦竹' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_郑燕美] 【电商事业部】 郑燕美负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 90000000.0, '年度开单金额': 16291778.0399999})` | 耗时 `0.037s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '郑燕美' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_谢均伟] 【电商事业部】 谢均伟负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 83000000.0, '年度开单金额': 4651067.68999999})` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '谢均伟' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_胡根] 【电商事业部】 胡根负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 10000000.0, '年度开单金额': 333045.781699999})` | 耗时 `0.045s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '胡根' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_曾庆凌] 【电商事业部】 曾庆凌负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 1000000.0, '年度开单金额': 107596.067199999})` | 耗时 `0.041s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '曾庆凌' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [EC_李金良] 【电商事业部】 李金良负责的那个业务部今年目标是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 50000000.0, '年度开单金额': -1324147.02})` | 耗时 `0.045s`
- **系统生成并执行的 SQL**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '李金良' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```

### [CS_RETAIL_广东] 【消费者事业部】 广东省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.081s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_广东] 【消费者事业部】 广东零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.047s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%广东%'
GROUP BY 销售大区;
```

### [CS_RETAIL_湖南] 【消费者事业部】 湖南省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`渠道开单金额完全吻合真值 (0.0元)` | 耗时 `0.059s`
- **系统生成并执行的 SQL**：
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
),
分公司排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY 达成率 DESC, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '分公司'
)
SELECT *
FROM 分公司排序
WHERE 全局排名 <= 3
ORDER BY 全局排名, 达成率 DESC, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
LIMIT 3
```

### [CS_HALF_湖南] 【消费者事业部】 湖南零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`衍生业务结论不准确 (期望得出: 未完成50%)` | 耗时 `0.044s`
- **系统生成并执行的 SQL**：
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

WHERE 节点名称 IN ('湖南','湖南分公司')
   OR 上级名称 IN ('湖南','湖南分公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```

### [CS_RETAIL_湖北] 【消费者事业部】 湖北省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.043s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_湖北] 【消费者事业部】 湖北零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.042s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%湖北%'
GROUP BY 销售大区;
```

### [CS_RETAIL_江西] 【消费者事业部】 江西省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.045s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_江西] 【消费者事业部】 江西零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.053s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%江西%'
GROUP BY 销售大区;
```

### [CS_RETAIL_四川] 【消费者事业部】 四川省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.053s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_四川] 【消费者事业部】 四川零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.042s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%四川%'
GROUP BY 销售大区;
```

### [CS_RETAIL_江苏] 【消费者事业部】 江苏省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_江苏] 【消费者事业部】 江苏零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.04s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%江苏%'
GROUP BY 销售大区;
```

### [CS_RETAIL_浙江] 【消费者事业部】 浙江省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.04s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_浙江] 【消费者事业部】 浙江零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(线下开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(线下开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%浙江%'
GROUP BY 销售大区;
```

### [CS_RETAIL_安徽] 【消费者事业部】 安徽省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.04s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_安徽] 【消费者事业部】 安徽零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(新零售开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(新零售开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%安徽%'
GROUP BY 销售大区;
```

### [CS_RETAIL_山东] 【消费者事业部】 山东省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`渠道开单金额完全吻合真值 (0.0元)` | 耗时 `0.037s`
- **系统生成并执行的 SQL**：
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
),
分公司排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY 达成率 DESC, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '分公司'
)
SELECT *
FROM 分公司排序
WHERE 全局排名 <= 3
ORDER BY 全局排名, 达成率 DESC, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
LIMIT 3
```

### [CS_HALF_山东] 【消费者事业部】 山东零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`衍生业务结论不准确 (期望得出: 未完成50%)` | 耗时 `0.038s`
- **系统生成并执行的 SQL**：
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

WHERE 节点名称 IN ('山东','山东分公司')
   OR 上级名称 IN ('山东','山东分公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```

### [CS_RETAIL_河南] 【消费者事业部】 河南省区零售渠道目前的累计开单是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`渠道金额不吻合 (真值期望: 0.0)` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
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
WHERE 层级 = '分公司'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```

### [CS_HALF_河南] 【消费者事业部】 河南零售渠道开单是否完成了全年目标的50%？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【未完成50%】` | 耗时 `0.038s`
- **系统生成并执行的 SQL**：
```sql
SELECT 销售大区 AS 节点名称,
       SUM(新零售开单金额) AS 渠道开单金额,
       SUM(年度目标营收) * 0.5 AS 半年目标基准,
       CASE WHEN SUM(新零售开单金额) >= SUM(年度目标营收) * 0.5 THEN '已完成50%' ELSE '未完成50%' END AS 完成判定
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026' AND 省份标签 LIKE '%河南%'
GROUP BY 销售大区;
```

### [SY_TASK_广州] 【商用事业部】 广州代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 总任务金额期望28500000.0实际2800000.0, 年度开单金额期望15718797.5399999实际22230.0` | 耗时 `0.044s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%广州%';
```

### [SY_AVG_广州] 【商用事业部】 广州代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.054s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%广州%';
```

### [SY_TASK_深圳] 【商用事业部】 深圳代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 总任务金额期望28500000.0实际2800000.0, 年度开单金额期望15718797.5399999实际22230.0` | 耗时 `0.048s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%深圳%';
```

### [SY_AVG_深圳] 【商用事业部】 深圳代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.056s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%深圳%';
```

### [SY_TASK_东莞] 【商用事业部】 东莞代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 总任务金额期望28500000.0实际2800000.0, 年度开单金额期望15718797.5399999实际22230.0` | 耗时 `0.059s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%东莞%';
```

### [SY_AVG_东莞] 【商用事业部】 东莞代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.061s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%东莞%';
```

### [SY_TASK_佛山] 【商用事业部】 佛山代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 总任务金额期望28500000.0实际2800000.0, 年度开单金额期望15718797.5399999实际22230.0` | 耗时 `0.054s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%佛山%';
```

### [SY_AVG_佛山] 【商用事业部】 佛山代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.062s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%佛山%';
```

### [SY_TASK_南京] 【商用事业部】 南京代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 12200000.0, '年度开单金额': 6028409.76})` | 耗时 `0.048s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%南京%';
```

### [SY_AVG_南京] 【商用事业部】 南京代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.055s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%南京%';
```

### [SY_TASK_杭州] 【商用事业部】 杭州代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 14600000.0, '年度开单金额': 5594455.17})` | 耗时 `0.048s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%杭州%';
```

### [SY_AVG_杭州] 【商用事业部】 杭州代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【高于全国平均】` | 耗时 `0.053s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%杭州%';
```

### [SY_TASK_合肥] 【商用事业部】 合肥代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`数值存在偏差: 年度开单金额期望2436117.8实际2404965.8` | 耗时 `0.042s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%合肥%';
```

### [SY_AVG_合肥] 【商用事业部】 合肥代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【低于全国平均】` | 耗时 `0.046s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%合肥%';
```

### [SY_TASK_武汉] 【商用事业部】 武汉代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 23100000.0, '年度开单金额': 7989510.53999999})` | 耗时 `0.043s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%武汉%';
```

### [SY_AVG_武汉] 【商用事业部】 武汉代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`衍生计算与业务结论准确得出: 【低于全国平均】` | 耗时 `0.053s`
- **系统生成并执行的 SQL**：
```sql
WITH 全国均值 AS (
    SELECT AVG(总任务达成率) AS 全国商用平均达成率
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT 代表处 AS 节点名称, ROUND(总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(k.全国商用平均达成率 * 100, 2) AS 全国平均达成率,
       CASE WHEN 总任务达成率 >= k.全国商用平均达成率 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data, 全国均值 k
WHERE 当前年 = '2026' AND 城市标签 LIKE '%武汉%';
```

### [SY_TASK_长沙] 【商用事业部】 长沙代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 10000000.0, '年度开单金额': 5354374.44999999})` | 耗时 `0.043s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%长沙%';
```

### [SY_AVG_长沙] 【商用事业部】 长沙代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`系统未生成有效 SQL 或返回 0 行` | 耗时 `0.039s`
- **系统生成并执行的 SQL**：
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
WHERE (节点名称 = '长沙' OR 上级名称 = '长沙' OR 代表处 = '长沙代表处')
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

### [SY_TASK_成都] 【商用事业部】 成都代表处今年的总营收任务和已开单各是多少？
- **数据准确性核验**：🟢 **数据准确 (Accurate)**
- **核验详情与真值比对**：`实体与核心数值完全吻合 ({'总任务金额': 17500000.0, '年度开单金额': 6862648.26})` | 耗时 `0.042s`
- **系统生成并执行的 SQL**：
```sql
SELECT '区域条线' AS 条线, '代表处' AS 层级, 代表处 AS 节点名称, 分公司 AS 上级名称,
       年度目标营收 AS 总任务金额, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 城市标签 LIKE '%成都%';
```

### [SY_AVG_成都] 【商用事业部】 成都代表处的达成率是否高过全国商用平均水平？
- **数据准确性核验**：🔴 **数据偏差 (Inaccurate)**
- **核验详情与真值比对**：`系统未生成有效 SQL 或返回 0 行` | 耗时 `0.038s`
- **系统生成并执行的 SQL**：
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
WHERE (节点名称 = '成都' OR 上级名称 = '成都' OR 代表处 = '成都代表处')
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

