# 消费者数据集 批量测试结果

- 总题数：40
- 链路成功（无 error/exception）：40
- 链路错误：0
- 链路异常：0
- 返回 0 行：8
- 返回行数为空：0
- SQL 为空：0

## 逐题明细

| 题号 | 问题 | 状态 | 行数 | SQL 模式 |
|------|------|------|------|----------|
| 1 | 云贵渝分公司的"总实际_万"是多少？ | success | 9 | SELECT+ORDER BY+WHERE |
| 2 | 哪些城市分公司隶属于"赣闽分公司"？ | success | 8 | SELECT+ORDER BY+WHERE |
| 3 | 查一下"万州城市分公司"的"新零售实际_万"。 | success | 2 | SELECT+ORDER BY+WHERE |
| 4 | 找出"线下实际_万"大于 100 万的分公司。 | success | 0 | SELECT+ORDER BY+WHERE |
| 5 | 筛选出所有"城市分公司"层级的节点。 | success | 83 | SELECT+ORDER BY+WHERE |
| 6 | "燃气定制-地产任务_万"大于 0 的节点有哪些？ | success | 81 | SELECT+ORDER BY+WHERE |
| 7 | 帮我看一下"上海城市分公司"的各项指标。 | success | 0 | SELECT+GROUP BY+ORDER BY+WHERE |
| 8 | 哪些分公司的总达成率已经达到 100%？ | success | 0 | SELECT+ORDER BY+WHERE |
| 9 | 找出上级名称是"消费者事业部"的所有节点。 | success | 83 | SELECT+ORDER BY+WHERE |
| 10 | "豫晋分公司"的"线下任务_万"是多少？ | success | 9 | SELECT+ORDER BY+WHERE |
| 11 | 哪些城市分公司的"新零售实际_万"超过了"线下实际_万"？ | success | 0 | SELECT+ORDER BY+WHERE |
| 12 | 找出"燃气定制-地产实际_万"大于"新零售实际_万"的分公司。 | success | 0 | SELECT+ORDER BY+WHERE |
| 13 | 有哪些节点的"总实际_万"不等于线下、新零售和燃气实际的总和？ | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 14 | 哪些分公司的"新零售任务_万"占"总任务_万"的比例超过了 50%？ | success | 83 | SELECT+ORDER BY+WHERE |
| 15 | 统计线下任务比新零售任务重的城市分公司名单。 | success | 0 | SELECT+GROUP BY+ORDER BY+WHERE |
| 16 | 消费者事业部整体的"线下实际_万"总和是多少？ | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 17 | 统计每个分公司下属城市分公司的"新零售实际_万"总和。 | success | 1 | SELECT+ORDER BY+WHERE |
| 18 | 城市分公司层级的"燃气定制-地产实际_万"平均值是多少？ | success | 0 | SELECT+GROUP BY+ORDER BY+WHERE |
| 19 | 帮我汇总一下各分公司的"总任务_万"和"总实际_万"。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 20 | 线下渠道和新零售渠道，哪个渠道的总实际销售额更高？ | success | 1 | SELECT+ORDER BY+WHERE |
| 21 | 按照上级名称分组，计算各区域的平均总达成率。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 22 | 统计各分公司拥有的城市分公司数量。 | success | 0 | SELECT+GROUP BY+ORDER BY+WHERE |
| 23 | 算出所有分公司的"燃气定制-地产任务_万"总额。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 24 | 新零售实际销售额排名前三的分公司是哪些？ | success | 22 | SELECT+ORDER BY+RANK+WHERE |
| 25 | 哪些分公司的城市分公司平均总实际额低于 50 万？ | success | 69 | SELECT+ORDER BY+WHERE |
| 26 | 燃气定制-地产实际完成额最高的是哪个分公司？ | success | 8 | SELECT+ORDER BY+WHERE |
| 27 | 哪个城市分公司的"总实际_万"最低？ | success | 1 | SELECT+ORDER BY+RANK+WHERE |
| 28 | 找出新零售实际销售额排名前五的城市分公司。 | success | 5 | SELECT+ORDER BY+RANK+WHERE |
| 29 | 总达成率排在后三名的分公司有哪些？ | success | 21 | SELECT+ORDER BY+RANK+WHERE |
| 30 | 线下实际完成最好的前三个城市分公司是谁？ | success | 3 | SELECT+ORDER BY+RANK+WHERE |
| 31 | 找出"线下实际"为0但"新零售实际"大于0的节点。 | success | 81 | SELECT+ORDER BY+WHERE |
| 32 | 哪个分公司下属的城市分公司总实际额差距最大？ | success | 1 | SELECT+ORDER BY+RANK+WHERE |
| 33 | 找出达成率低于平均总达成率的分公司。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 34 | 今年新零售业务谁做得最好？ | success | 81 | SELECT+ORDER BY+WHERE |
| 35 | 还有哪些地方燃气定制业务没有开张？ | success | 81 | SELECT+ORDER BY+WHERE |
| 36 | 线下拖了后腿（达成率低于 50%）的城市有哪些？ | success | 83 | SELECT+ORDER BY+WHERE |
| 37 | 帮我排一下各省分公司的整体业绩。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |
| 38 | 哪些城市新零售完成了指标，但线下没完成？ | success | 81 | SELECT+ORDER BY+WHERE |
| 39 | 燃气定制业务主要集中在哪些分公司？ | success | 1 | SELECT+ORDER BY+WHERE |
| 40 | 算一下各区域线上（新零售）和线下渠道的业绩贡献比例。 | success | 13 | SELECT+GROUP BY+ORDER BY+WHERE |

> 注：本报告仅统计链路执行状态与返回行数，业务正确性需结合 SQL 与预期人工复核。