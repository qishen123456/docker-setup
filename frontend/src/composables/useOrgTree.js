/**
 * useOrgTree — Build hierarchical tree from flat report rows using report_config.
 *
 * Given:
 *   - rows: Array<Object> (flat SQL result rows)
 *   - config: { nameColumn, parentColumn, trackColumn, levelColumn, metrics, levels, ... }
 *
 * Returns:
 *   - tree: computed tree structure
 *   - flatNodes: computed flat node list with depth
 *   - getSignal(node): returns { tone, label } based on signalRules
 *   - groupByTrack(): returns { [trackValue]: nodes[] }
 *   - riskNodes: computed list of nodes below riskThreshold
 */

import { computed } from 'vue'

export function useOrgTree(rows, config) {
  const cfg = computed(() => config.value || config)

  const nameCol = computed(() => cfg.value.nameColumn || '节点名称')
  const parentCol = computed(() => cfg.value.parentColumn || '上级名称')
  const trackCol = computed(() => cfg.value.trackColumn || '条线')
  const levelCol = computed(() => cfg.value.levelColumn || '层级')
  const metrics = computed(() => cfg.value.metrics || [])
  const signalRules = computed(() => cfg.value.signalRules || [])
  const riskThreshold = computed(() => cfg.value.riskThreshold ?? 80)

  // Build node map
  const nodeMap = computed(() => {
    const data = rows.value || rows
    if (!Array.isArray(data)) return {}
    const map = {}
    for (const row of data) {
      const name = row[nameCol.value]
      if (!name) continue
      map[name] = {
        name,
        parent: row[parentCol.value] || null,
        track: row[trackCol.value] || '',
        level: row[levelCol.value] || '',
        raw: row,
        children: [],
        metrics: {},
      }
      for (const m of metrics.value) {
        map[name].metrics[m.key] = row[m.column] ?? null
      }
    }
    return map
  })

  // Build tree
  const tree = computed(() => {
    const map = nodeMap.value
    const roots = []
    for (const node of Object.values(map)) {
      if (node.parent && map[node.parent]) {
        map[node.parent].children.push(node)
      } else {
        roots.push(node)
      }
    }
    return roots
  })

  // Flat list with depth
  const flatNodes = computed(() => {
    const result = []
    function walk(nodes, depth) {
      for (const n of nodes) {
        result.push({ ...n, depth })
        if (n.children.length) walk(n.children, depth + 1)
      }
    }
    walk(tree.value, 0)
    return result
  })

  // Signal evaluation
  function getSignal(node) {
    for (const rule of signalRules.value) {
      const val = node.metrics[rule.key]
      if (val == null) continue
      const numVal = typeof val === 'string' ? parseFloat(val) : val
      if (isNaN(numVal)) continue
      let match = false
      if (rule.op === '>=' && numVal >= rule.value) match = true
      if (rule.op === '<' && numVal < rule.value) match = true
      if (rule.op === '<=' && numVal <= rule.value) match = true
      if (rule.op === '>' && numVal > rule.value) match = true
      if (rule.op === '==' && numVal === rule.value) match = true
      if (match) return { tone: rule.tone, label: rule.label }
    }
    return { tone: 'neutral', label: '' }
  }

  // Group by track
  function groupByTrack() {
    const groups = {}
    for (const node of Object.values(nodeMap.value)) {
      const t = node.track || '未分类'
      if (!groups[t]) groups[t] = []
      groups[t].push(node)
    }
    return groups
  }

  // Risk nodes
  const riskNodes = computed(() => {
    const rateMetric = metrics.value.find(m => m.format === 'percent') || metrics.value.find(m => m.key === 'rate')
    if (!rateMetric) return []
    return Object.values(nodeMap.value).filter(n => {
      const val = n.metrics[rateMetric.key]
      const num = typeof val === 'string' ? parseFloat(val) : val
      return typeof num === 'number' && !isNaN(num) && num < riskThreshold.value
    })
  })

  return {
    tree,
    flatNodes,
    nodeMap,
    getSignal,
    groupByTrack,
    riskNodes,
    metrics,
  }
}
