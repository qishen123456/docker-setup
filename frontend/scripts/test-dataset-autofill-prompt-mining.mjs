import assert from 'node:assert/strict'

import {
  dedupeGoldenSqlSamples,
  extractSqlSamplesFromPrompts,
  mergeAutofillCollection,
} from '../src/utils/datasetAutofillPromptMining.js'

const datasetName = '消费者事业部测试数据集'
const maintainedPrompts = [
  {
    agent_no: 2,
    prompt_key: 'default',
    prompt_content: `
你是 Agent2。
问题：消费者事业部本月 GMV 是多少？
\`\`\`sql
WITH base AS (
  SELECT dept_name, gmv
  FROM consumer_orders
)
SELECT SUM(gmv) AS "GMV"
FROM base;
\`\`\`

问题：消费者事业部各渠道订单排名如何？
SELECT channel_name AS "渠道", SUM(order_amount) AS "订单金额"
FROM consumer_orders
GROUP BY channel_name
ORDER BY "订单金额" DESC
LIMIT 20;
`,
  },
  {
    agent_no: 4,
    prompt_key: 'default',
    prompt_content: `
报告逻辑必须先讲整体，再讲渠道。
问题：消费者事业部复购率怎么看？
\`\`\`sql
SELECT member_level AS "会员等级", AVG(repurchase_rate) AS "复购率"
FROM consumer_members
GROUP BY member_level;
\`\`\`
`,
  },
]

const samples = extractSqlSamplesFromPrompts(maintainedPrompts, datasetName)
assert.equal(samples.length, 3)
assert.equal(samples[0].question, '消费者事业部本月 GMV 是多少？')
assert.equal(samples[0].quality_score, 96)
assert.match(samples[1].sql_text, /ORDER BY "订单金额" DESC/)
assert.deepEqual(samples[2].tags.slice(0, 2), [datasetName, 'Agent4'])

const deduped = dedupeGoldenSqlSamples([...samples, { ...samples[0] }])
assert.equal(deduped.length, 3)

const collection = [
  { agent_no: 2, prompt_key: 'default', prompt_content: '人工维护 Agent2，不应被覆盖', is_active: true },
]
mergeAutofillCollection(
  collection,
  [
    { agent_no: 2, prompt_key: 'default', prompt_content: '自动生成 Agent2', is_active: true },
    { agent_no: 3, prompt_key: 'default', prompt_content: '自动生成 Agent3', is_active: true },
  ],
  item => `${item.agent_no}|${item.prompt_key}`,
  { preservePromptContent: true },
)
assert.equal(collection.length, 2)
assert.equal(collection[0].prompt_content, '人工维护 Agent2，不应被覆盖')
assert.equal(collection[1].prompt_content, '自动生成 Agent3')

console.log('dataset autofill prompt mining test passed')
