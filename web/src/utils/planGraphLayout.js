const NODE_W = 104
const NODE_H_MIN = 52
const H_GAP = 24
const V_GAP = 28
const PAD = 10
const REJECT_BASE_GAP = 4
const REJECT_LANE_STEP = 8
const REJECT_LABEL_SPACE = 6
const LABEL_CHARS_PER_LINE = 7
const MAX_LABEL_LINES = 3
const NODE_PAD_TOP = 8
const NODE_PAD_BOTTOM = 22
const STATUS_DOT_R = 4
const STATUS_DOT_H = STATUS_DOT_R * 2
const GAP_AFTER_STATUS = 6
const LABEL_LINE_H = 12
const GAP_BEFORE_AGENT = 5
const AGENT_LINE_H = 10

import { resolveGraphNodeDisplayAgent, resolveNodeVisualType } from './planGraphState.js'
import { END_NODE, normalizeNodeRole, START_NODE } from './planGraphEdit.js'

const PHASE_GROUP_PAD = 8
const PHASE_GROUP_LABEL_H = 18

function resolveLayoutPadding(graphSpec) {
  const hasPhases = (graphSpec?.nodes || []).some((n) => String(n?.phase || '').trim())
  if (!hasPhases) {
    return { padLeft: PAD, padTop: PAD, padRight: PAD, padBottom: PAD }
  }
  return {
    padLeft: PAD + PHASE_GROUP_PAD,
    padTop: PAD + PHASE_GROUP_PAD + PHASE_GROUP_LABEL_H,
    padRight: PAD + PHASE_GROUP_PAD,
    padBottom: PAD,
  }
}

function buildPhaseGroups(layoutNodes, graphSpec, bottomExtent = 0) {
  const phaseByNodeId = new Map()
  for (const raw of graphSpec?.nodes || []) {
    const phase = String(raw?.phase || '').trim()
    if (phase && raw?.id) phaseByNodeId.set(raw.id, phase)
  }
  const grouped = new Map()
  for (const node of layoutNodes) {
    const phase = phaseByNodeId.get(node.id)
    if (!phase) continue
    if (!grouped.has(phase)) grouped.set(phase, [])
    grouped.get(phase).push(node)
  }
  return [...grouped.entries()].map(([phase, nodes]) => {
    const minX = Math.min(...nodes.map((n) => n.x)) - PHASE_GROUP_PAD
    const maxX = Math.max(...nodes.map((n) => n.x + n.w)) + PHASE_GROUP_PAD
    const minY = Math.min(...nodes.map((n) => n.y)) - PHASE_GROUP_PAD - PHASE_GROUP_LABEL_H
    const nodeBottom = Math.max(...nodes.map((n) => n.y + n.h))
    const maxY = Math.max(nodeBottom, bottomExtent) + PHASE_GROUP_PAD
    return {
      phase,
      x: minX,
      y: minY,
      w: maxX - minX,
      h: maxY - minY,
      labelX: minX + 10,
      labelY: minY + 14,
    }
  })
}


/**
 * @param {object|null} graphSpec DirectExecGraph: { nodes, edges, entry }
 * @returns {{ width: number, height: number, nodes: object[], edges: object[] }}
 */
export function buildPlanGraphLayout(graphSpec) {
  if (!graphSpec || !Array.isArray(graphSpec.nodes) || !graphSpec.nodes.length) {
    return { width: 320, height: 80, nodes: [], edges: [], phaseGroups: [] }
  }
  const nodeMap = new Map()
  for (const n of graphSpec.nodes) {
    if (!n?.id) continue
    const fullLabel = n.label || n.id
    const labelLines = wrapLabel(fullLabel, LABEL_CHARS_PER_LINE, MAX_LABEL_LINES)
    nodeMap.set(n.id, {
      id: n.id,
      labelLines,
      fullLabel,
      agentType: resolveGraphNodeDisplayAgent(graphSpec, n.id),
      nodeRole: normalizeNodeRole(n.node_role),
      visualType: resolveNodeVisualType(n),
      h: nodeHeight(labelLines.length),
    })
  }
  const edges = (graphSpec.edges || []).filter(
    (e) => e && e.from !== START_NODE && e.to !== END_NODE && nodeMap.has(e.from) && nodeMap.has(e.to),
  )
  const levelEdges = edges.filter((e) => (e.condition || 'always') !== 'reject')
  const levels = assignLevels(graphSpec.entry, levelEdges, nodeMap)
  const byLevel = new Map()
  for (const [id, level] of levels.entries()) {
    if (!byLevel.has(level)) byLevel.set(level, [])
    byLevel.get(level).push(id)
  }
  const maxLevel = Math.max(0, ...levels.values())
  const padding = resolveLayoutPadding(graphSpec)
  let maxColumnHeight = NODE_H_MIN
  for (let lv = 0; lv <= maxLevel; lv += 1) {
    const row = byLevel.get(lv) || []
    const colH = row.reduce((sum, id) => sum + (nodeMap.get(id)?.h || NODE_H_MIN), 0)
      + Math.max(0, row.length - 1) * V_GAP
    maxColumnHeight = Math.max(maxColumnHeight, colH)
  }
  const width = padding.padLeft + padding.padRight + (maxLevel + 1) * NODE_W + maxLevel * H_GAP
  const rejectEdges = edges.filter((e) => (e.condition || 'always') === 'reject')
  const { laneByEdge, laneCount } = assignRejectLanes(rejectEdges)
  const rejectAreaH = laneCount > 0
    ? REJECT_BASE_GAP + laneCount * REJECT_LANE_STEP + REJECT_LABEL_SPACE
    : 0
  const height = padding.padTop + padding.padBottom + maxColumnHeight + rejectAreaH
  const pos = buildNodePositions(byLevel, maxLevel, nodeMap, maxColumnHeight, padding)
  let maxNodeBottom = 0
  for (const p of pos.values()) {
    maxNodeBottom = Math.max(maxNodeBottom, p.y + p.h)
  }
  const rejectLaneBaseY = maxNodeBottom + REJECT_BASE_GAP
  const layoutNodes = [...nodeMap.keys()].map((id) => {
    const p = pos.get(id)
    const meta = nodeMap.get(id)
    const chrome = buildNodeChrome(p, meta.labelLines.length)
    return {
      id,
      labelLines: meta.labelLines,
      fullLabel: meta.fullLabel,
      agentType: meta.agentType,
      nodeRole: meta.nodeRole,
      visualType: meta.visualType,
      labelLineDy: LABEL_LINE_H,
      ...chrome,
      ...p,
    }
  })
  const layoutEdges = edges.map((e) => {
    const from = pos.get(e.from)
    const to = pos.get(e.to)
    if (!from || !to) return null
    const condition = e.condition || 'always'
    const backward = to.level < from.level || to.x + to.w <= from.x
    const built = backward || condition === 'reject'
      ? buildRejectPath(from, to, rejectLaneBaseY, laneByEdge.get(edgeKey(e)) ?? 0)
      : buildForwardPath(from, to)
    return {
      fromId: e.from,
      toId: e.to,
      condition,
      backward: built.backward,
      path: built.path,
      label: edgeLabel(condition),
      labelX: built.labelX,
      labelY: built.labelY,
    }
  }).filter(Boolean)
  layoutEdges.sort((a, b) => {
    const order = { always: 0, pass: 1, reject: 2 }
    return (order[a.condition] ?? 0) - (order[b.condition] ?? 0)
  })
  let rejectBottomY = maxNodeBottom
  for (const edge of layoutEdges) {
    if (edge.condition === 'reject' && edge.labelY != null) {
      rejectBottomY = Math.max(rejectBottomY, edge.labelY + 6)
    }
  }
  const phaseGroups = buildPhaseGroups(layoutNodes, graphSpec, rejectBottomY)
  const bounds = computeGraphBounds(layoutNodes, layoutEdges, phaseGroups, padding)
  return {
    width: bounds.width,
    height: bounds.height,
    nodes: layoutNodes,
    edges: layoutEdges,
    phaseGroups,
  }
}

function computeGraphBounds(layoutNodes, layoutEdges, phaseGroups, padding) {
  const inset = 4
  let maxX = 0
  let maxY = 0
  let minY = Infinity
  for (const node of layoutNodes) {
    maxX = Math.max(maxX, node.x + node.w)
    maxY = Math.max(maxY, node.y + node.h)
  }
  for (const group of phaseGroups) {
    minY = Math.min(minY, group.y)
    maxX = Math.max(maxX, group.x + group.w)
    maxY = Math.max(maxY, group.y + group.h)
  }
  for (const edge of layoutEdges) {
    if (edge.labelY != null) maxY = Math.max(maxY, edge.labelY + 8)
    if (edge.labelX != null) maxX = Math.max(maxX, edge.labelX + 28)
  }
  const topPad = Number.isFinite(minY) ? Math.max(padding.padTop, inset - minY + padding.padTop) : padding.padTop
  return {
    width: Math.max(padding.padLeft + padding.padRight + NODE_W, maxX + padding.padRight + inset),
    height: Math.max(topPad + padding.padBottom + NODE_H_MIN, maxY + inset + 4),
  }
}

function edgeLabel(condition) {
  if (condition === 'pass') return '通过'
  if (condition === 'reject') return '驳回返工'
  return '顺序'
}

function buildForwardPath(from, to) {
  const x1 = from.x + from.w
  const y1 = from.cy
  const x2 = to.x
  const y2 = to.cy
  const mx = (x1 + x2) / 2
  return {
    backward: false,
    path: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
    labelX: mx,
    labelY: (y1 + y2) / 2 - 4,
  }
}

/** 审查驳回：每条边独立车道，避免多条返工线叠在同一条水平线上 */
function buildRejectPath(from, to, laneBaseY, laneIndex) {
  const x1 = from.cx
  const y1 = from.y + from.h
  const x2 = to.cx
  const y2 = to.y + to.h
  const drop = laneBaseY + laneIndex * REJECT_LANE_STEP
  const labelX = (x1 + x2) / 2
  return {
    backward: true,
    path: `M ${x1} ${y1} L ${x1} ${drop} L ${x2} ${drop} L ${x2} ${y2}`,
    labelX,
    labelY: drop + 6,
  }
}

function edgeKey(e) {
  return `${e.from}->${e.to}:${e.condition || 'always'}`
}

/** 每条驳回边独占一层车道，避免返工关系叠在一起 */
function assignRejectLanes(rejectEdges) {
  const laneByEdge = new Map()
  const sorted = [...rejectEdges].sort((a, b) => {
    const keyA = `${a.from}:${a.to}`
    const keyB = `${b.from}:${b.to}`
    return keyA.localeCompare(keyB, 'zh-CN')
  })
  sorted.forEach((e, i) => {
    laneByEdge.set(edgeKey(e), i)
  })
  return { laneByEdge, laneCount: rejectEdges.length }
}

function buildNodePositions(byLevel, maxLevel, nodeMap, maxColumnHeight, padding) {
  const pos = new Map()
  for (let lv = 0; lv <= maxLevel; lv += 1) {
    const row = byLevel.get(lv) || []
    const colH = row.reduce((sum, id) => sum + (nodeMap.get(id)?.h || NODE_H_MIN), 0)
      + Math.max(0, row.length - 1) * V_GAP
    let y = padding.padTop + (maxColumnHeight - colH) / 2
    row.forEach((id) => {
      const meta = nodeMap.get(id)
      const h = meta?.h || NODE_H_MIN
      const x = padding.padLeft + lv * (NODE_W + H_GAP)
      pos.set(id, { x, y, w: NODE_W, h, cx: x + NODE_W / 2, cy: y + h / 2, level: lv })
      y += h + V_GAP
    })
  }
  return pos
}

function assignLevels(entry, edges, nodeMap) {
  const levels = new Map()
  if (!entry || !nodeMap.has(entry)) return levels
  levels.set(entry, 0)
  const maxIter = Math.max(1, nodeMap.size * nodeMap.size)
  for (let i = 0; i < maxIter; i += 1) {
    let changed = false
    for (const e of edges) {
      if (!nodeMap.has(e.from) || !nodeMap.has(e.to)) continue
      const fromLv = levels.get(e.from)
      if (fromLv == null) continue
      const nextLv = fromLv + 1
      const prev = levels.get(e.to)
      if (prev == null || nextLv > prev) {
        levels.set(e.to, nextLv)
        changed = true
      }
    }
    if (!changed) break
  }
  for (const id of nodeMap.keys()) {
    if (!levels.has(id)) levels.set(id, 0)
  }
  return levels
}

function nodeHeight(lineCount) {
  const lines = Math.max(1, lineCount)
  return Math.max(
    NODE_H_MIN,
    NODE_PAD_TOP + STATUS_DOT_H + GAP_AFTER_STATUS
      + lines * LABEL_LINE_H + GAP_BEFORE_AGENT + AGENT_LINE_H + NODE_PAD_BOTTOM,
  )
}

function buildNodeChrome(p, lineCount) {
  const lines = Math.max(1, lineCount)
  const dotCy = p.y + NODE_PAD_TOP + STATUS_DOT_R
  const labelTop = p.y + NODE_PAD_TOP + STATUS_DOT_H + GAP_AFTER_STATUS
  return {
    statusDot: { cx: p.x + p.w / 2, cy: dotCy, r: STATUS_DOT_R },
    labelY: labelTop + 8,
    labelLineDy: LABEL_LINE_H,
    agentY: labelTop + lines * LABEL_LINE_H + GAP_BEFORE_AGENT + 5,
  }
}

export function wrapLabel(text, maxCharsPerLine = LABEL_CHARS_PER_LINE, maxLines = MAX_LABEL_LINES) {
  const s = String(text || '').trim()
  if (!s) return ['']
  const lines = []
  for (let i = 0; i < s.length && lines.length < maxLines; i += maxCharsPerLine) {
    lines.push(s.slice(i, i + maxCharsPerLine))
  }
  if (s.length > maxCharsPerLine * maxLines) {
    const last = lines[lines.length - 1]
    lines[lines.length - 1] = `${last.slice(0, Math.max(1, maxCharsPerLine - 1))}…`
  }
  return lines
}
