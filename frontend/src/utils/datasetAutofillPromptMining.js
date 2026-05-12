const SQL_START_RE = /^(with|select)\b/i
const SQL_SHAPE_RE = /\bfrom\b/i

export const normalizeSqlText = (value = '') => String(value || '')
  .replace(/```(?:sql)?/gi, '')
  .replace(/```/g, '')
  .trim()
  .replace(/;+\s*$/, '')
  .trim()

const looksLikeReadOnlySql = (value = '') => {
  const sql = normalizeSqlText(value)
  return SQL_START_RE.test(sql) && SQL_SHAPE_RE.test(sql) && sql.length >= 40
}

const inferQuestionFromPrefix = (prefix = '', fallback = '') => {
  const tail = String(prefix || '').slice(-520)
  const patterns = [
    /(?:问题|业务问题|用户问题|问法|场景)\s*[:：]\s*([^\n；;。]+)/gi,
    /(?:question|case)\s*[:：]\s*([^\n；;。]+)/gi,
  ]
  for (const pattern of patterns) {
    const matches = [...tail.matchAll(pattern)]
    const hit = matches[matches.length - 1]?.[1]?.trim()
    if (hit) return hit
  }
  return fallback
}

const collectFencedSqlBlocks = (content = '') => {
  const blocks = []
  const regex = /```(?:sql|postgresql|pgsql)?\s*([\s\S]*?)```/gi
  let match
  while ((match = regex.exec(content)) !== null) {
    const sql = normalizeSqlText(match[1])
    if (!looksLikeReadOnlySql(sql)) continue
    blocks.push({
      sql,
      index: match.index,
    })
  }
  return blocks
}

const collectPlainSqlBlocks = (content = '') => {
  const blocks = []
  const lines = String(content || '').split(/\r?\n/)
  let offset = 0
  let startIndex = -1
  let buffer = []

  const flush = () => {
    const sql = normalizeSqlText(buffer.join('\n'))
    if (looksLikeReadOnlySql(sql)) {
      blocks.push({ sql, index: startIndex >= 0 ? startIndex : 0 })
    }
    startIndex = -1
    buffer = []
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (startIndex < 0 && SQL_START_RE.test(trimmed)) {
      startIndex = offset
      buffer = [line]
    } else if (startIndex >= 0) {
      buffer.push(line)
    }

    if (startIndex >= 0 && (/;\s*$/.test(trimmed) || (buffer.length >= 8 && !trimmed))) {
      flush()
    }
    offset += line.length + 1
  }

  if (startIndex >= 0) flush()
  return blocks
}

const makeSample = ({ sql, content, index, datasetName, agentNo, sampleIndex }) => {
  const fallbackQuestion = `${datasetName || '当前数据集'}样例 SQL ${sampleIndex}`
  return {
    intent_type: 'prompt_example',
    question: inferQuestionFromPrefix(content.slice(0, index), fallbackQuestion),
    sql_text: sql,
    tags: [datasetName || '当前数据集', `Agent${agentNo}`, 'Prompt样例SQL'],
    quality_score: agentNo === 2 ? 96 : 92,
    is_active: true,
  }
}

export const extractSqlSamplesFromPrompts = (agentPrompts = [], datasetName = '当前数据集') => {
  const samples = []
  const seen = new Set()
  ;(agentPrompts || []).forEach((prompt) => {
    const agentNo = Number(prompt?.agent_no || 0)
    if (![2, 4].includes(agentNo)) return
    const content = String(prompt?.prompt_content || '')
    if (!content.trim()) return
    const blocks = [
      ...collectFencedSqlBlocks(content),
      ...collectPlainSqlBlocks(content),
    ]
    blocks.forEach((block) => {
      const key = normalizeSqlText(block.sql).toLowerCase()
      if (!key || seen.has(key)) return
      seen.add(key)
      samples.push(makeSample({
        sql: block.sql,
        content,
        index: block.index,
        datasetName,
        agentNo,
        sampleIndex: samples.length + 1,
      }))
    })
  })
  return samples
}

export const dedupeGoldenSqlSamples = (samples = []) => {
  const seen = new Set()
  return (samples || []).filter((sample) => {
    const question = String(sample?.question || '').trim()
    const sql = normalizeSqlText(sample?.sql_text || '')
    if (!question || !sql) return false
    const key = `${question}::${sql.toLowerCase()}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export const mergeAutofillCollection = (list, items, keyFn, options = {}) => {
  ;(items || []).forEach((item) => {
    const key = keyFn(item)
    const index = list.findIndex(existing => keyFn(existing) === key)
    const copy = JSON.parse(JSON.stringify(item))
    if (index >= 0) {
      const existing = list[index]
      const shouldPreservePrompt = options.preservePromptContent
        && String(existing?.prompt_content || '').trim()
      const shouldPreserveExisting = options.preserveExisting || shouldPreservePrompt
      list[index] = shouldPreserveExisting ? { ...copy, ...existing } : { ...existing, ...copy }
    } else {
      list.push(copy)
    }
  })
}
