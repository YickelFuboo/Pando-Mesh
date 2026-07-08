const NODE_W = 122
const NODE_H_MIN = 54
const H_GAP = 28
const V_GAP = 24
const PAD = 12
const REJECT_BASE_GAP = 3
const REJECT_LANE_STEP = 5
const REJECT_LABEL_SPACE = 4
const LABEL_CHARS_PER_LINE = 8
const MAX_LABEL_LINES = 3
const STANDARD_LABEL_LINES = 2
const NODE_PAD_TOP = 5
const NODE_PAD_BOTTOM = 4
const NODE_ACTION_ZONE = 26
const STATUS_DOT_R = 4
const STATUS_DOT_H = STATUS_DOT_R * 2
const GAP_AFTER_STATUS = 3
const LABEL_LINE_H = 12
const GAP_BEFORE_AGENT = 3
const AGENT_LINE_H = 9
const BRANCH_ROW_GAP = 24

const DEFAULT_LAYOUT = Object.freeze({
  nodeW: NODE_W,
  nodeHMin: NODE_H_MIN,
  labelLineH: LABEL_LINE_H,
})

const COMFORTABLE_LAYOUT = Object.freeze({
  nodeW: 126,
  nodeHMin: 58,
  labelLineH: 13,
})

let activeLayout = DEFAULT_LAYOUT

function resolveActiveLayout(size = 'default') {
  return size === 'comfortable' ? COMFORTABLE_LAYOUT : DEFAULT_LAYOUT
}

import { resolveGraphNodeDisplayAgent, resolveNodeVisualType } from './planGraphState.js'
import { END_NODE, normalizeNodeRole, START_NODE } from './planGraphEdit.js'

const PHASE_GROUP_PAD = 10
const PHASE_GROUP_LABEL_H = 20

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
export function buildPlanGraphLayout(graphSpec, options = {}) {
  activeLayout = resolveActiveLayout(options?.size)
  if (!graphSpec || !Array.isArray(graphSpec.nodes) || !graphSpec.nodes.length) {
    return { width: 320, height: 80, nodes: [], edges: [], phaseGroups: [] }
  }
  const nodeMap = new Map()
  for (const n of graphSpec.nodes) {
    if (!n?.id) continue
    const fullLabel = n.label || n.id
    const labelLines = wrapLabel(fullLabel, LABEL_CHARS_PER_LINE, MAX_LABEL_LINES)
    const nodeRole = normalizeNodeRole(n.node_role)
    const visualType = resolveNodeVisualType(n)
    nodeMap.set(n.id, {
      id: n.id,
      labelLines,
      fullLabel,
      agentType: resolveGraphNodeDisplayAgent(graphSpec, n.id),
      nodeRole,
      visualType,
      h: nodeHeight(labelLines.length),
    })
  }
  const edges = (graphSpec.edges || []).filter(
    (e) => e && e.from !== START_NODE && e.to !== END_NODE && nodeMap.has(e.from) && nodeMap.has(e.to),
  )
  const levelEdges = edges.filter((e) => (e.condition || 'always') !== 'reject')
  const levels = assignLevels(graphSpec.entry, levelEdges, nodeMap)
  const { branchRows, forkRegions } = assignForkBranchRows(levels, levelEdges, nodeMap)
  const byLevel = new Map()
  for (const [id, level] of levels.entries()) {
    if (!byLevel.has(level)) byLevel.set(level, [])
    byLevel.get(level).push(id)
  }
  const maxLevel = Math.max(0, ...levels.values())
  const padding = resolveLayoutPadding(graphSpec)
  const metrics = computeLayoutMetrics(nodeMap, branchRows, forkRegions)
  const width = padding.padLeft + padding.padRight + (maxLevel + 1) * activeLayout.nodeW + maxLevel * H_GAP
  const pos = buildGraphPositions({
    byLevel,
    maxLevel,
    nodeMap,
    levels,
    branchRows,
    forkRegions,
    padding,
    metrics,
  })
  const rejectEdges = edges.filter((e) => (e.condition || 'always') === 'reject')
  const { laneByEdge } = assignRejectLanes(rejectEdges, pos)
  let maxNodeBottom = 0
  for (const p of pos.values()) {
    maxNodeBottom = Math.max(maxNodeBottom, p.y + p.h)
  }
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
      labelLineDy: activeLayout.labelLineH,
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
      ? buildRejectPath(from, to, laneByEdge.get(edgeKey(e)) ?? 0)
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
      rejectBottomY = Math.max(rejectBottomY, edge.labelY + 4)
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
    width: Math.max(padding.padLeft + padding.padRight + activeLayout.nodeW, maxX + padding.padRight + inset),
    height: Math.max(topPad + padding.padBottom + activeLayout.nodeHMin, maxY + inset + 4),
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

function buildRejectPath(from, to, laneIndex) {
  const x1 = from.cx
  const y1 = from.y + from.h
  const x2 = to.cx
  const y2 = to.y + to.h
  const drop = y1 + REJECT_BASE_GAP + laneIndex * REJECT_LANE_STEP
  const labelX = (x1 + x2) / 2
  return {
    backward: true,
    path: `M ${x1} ${y1} L ${x1} ${drop} L ${x2} ${drop} L ${x2} ${y2}`,
    labelX,
    labelY: drop + 3,
  }
}

function rejectEdgeSpanFromPos(edge, pos) {
  const from = pos.get(edge.from)
  const to = pos.get(edge.to)
  if (!from || !to) return { left: 0, right: 0, dropKey: 0 }
  const x1 = from.cx
  const x2 = to.cx
  const dropKey = Math.round(from.y + from.h)
  return {
    left: Math.min(x1, x2),
    right: Math.max(x1, x2),
    dropKey,
  }
}

function edgeKey(e) {
  return `${e.from}->${e.to}:${e.condition || 'always'}`
}

function assignRejectLanes(rejectEdges, pos) {
  const laneByEdge = new Map()
  const laneRangesByDrop = new Map()
  const sorted = [...rejectEdges].sort((a, b) => {
    const spanA = rejectEdgeSpanFromPos(a, pos)
    const spanB = rejectEdgeSpanFromPos(b, pos)
    if (spanA.dropKey !== spanB.dropKey) return spanA.dropKey - spanB.dropKey
    if (spanA.left !== spanB.left) return spanA.left - spanB.left
    const keyA = `${a.from}:${a.to}`
    const keyB = `${b.from}:${b.to}`
    return keyA.localeCompare(keyB, 'zh-CN')
  })
  for (const edge of sorted) {
    const span = rejectEdgeSpanFromPos(edge, pos)
    if (!laneRangesByDrop.has(span.dropKey)) {
      laneRangesByDrop.set(span.dropKey, [])
    }
    const laneRanges = laneRangesByDrop.get(span.dropKey)
    let laneIndex = laneRanges.findIndex(
      (range) => range.right <= span.left || range.left >= span.right,
    )
    if (laneIndex < 0) {
      laneIndex = laneRanges.length
      laneRanges.push({ left: span.left, right: span.right })
    } else {
      laneRanges[laneIndex] = {
        left: Math.min(laneRanges[laneIndex].left, span.left),
        right: Math.max(laneRanges[laneIndex].right, span.right),
      }
    }
    laneByEdge.set(edgeKey(edge), laneIndex)
  }
  return { laneByEdge }
}

function nodeLayoutLines(lineCount) {
  const lines = Math.max(1, Math.min(lineCount, MAX_LABEL_LINES))
  if (lines <= STANDARD_LABEL_LINES) return STANDARD_LABEL_LINES
  return lines
}

function nodeHeight(lineCount) {
  const layoutLines = nodeLayoutLines(lineCount)
  return Math.max(
    activeLayout.nodeHMin,
    NODE_PAD_TOP + STATUS_DOT_H + GAP_AFTER_STATUS
      + layoutLines * activeLayout.labelLineH + GAP_BEFORE_AGENT + AGENT_LINE_H
      + NODE_ACTION_ZONE + NODE_PAD_BOTTOM,
  )
}

function buildNodeChrome(p, lineCount) {
  const displayLines = Math.max(1, Math.min(lineCount, MAX_LABEL_LINES))
  const layoutLines = nodeLayoutLines(lineCount)
  const lineH = activeLayout.labelLineH
  const dotCy = p.y + NODE_PAD_TOP + STATUS_DOT_R
  const labelTop = p.y + NODE_PAD_TOP + STATUS_DOT_H + GAP_AFTER_STATUS
  const labelBlockH = layoutLines * lineH
  const displayBlockH = displayLines * lineH
  const labelYOffset = Math.max(0, (labelBlockH - displayBlockH) / 2)
  const textOffset = 5
  return {
    statusDot: { cx: p.x + p.w / 2, cy: dotCy, r: STATUS_DOT_R },
    labelY: labelTop + textOffset + labelYOffset,
    labelLineDy: lineH,
    agentY: labelTop + labelBlockH + GAP_BEFORE_AGENT + textOffset,
  }
}

function computeLayoutMetrics(nodeMap, branchRows, forkRegions) {
  let mainBandHeight = activeLayout.nodeHMin
  for (const [id, meta] of nodeMap) {
    if (branchRows.has(id)) continue
    mainBandHeight = Math.max(mainBandHeight, meta?.h || activeLayout.nodeHMin)
  }
  const branchRowCount = branchRows.size > 0
    ? Math.max(...branchRows.values()) + 1
    : 0
  const branchRowHeights = branchRowCount > 0
    ? Array.from({ length: branchRowCount }, () => activeLayout.nodeHMin)
    : []
  if (branchRowCount > 0) {
    for (const [id, rowIndex] of branchRows) {
      branchRowHeights[rowIndex] = Math.max(branchRowHeights[rowIndex], nodeMap.get(id)?.h || activeLayout.nodeHMin)
    }
  }
  const branchBandHeight = branchRowCount > 0
    ? branchRowHeights.reduce((sum, h) => sum + h, 0) + Math.max(0, branchRowCount - 1) * BRANCH_ROW_GAP
    : 0
  const extraBranchBelow = branchRowCount > 1
    ? branchRowHeights.slice(1).reduce((sum, h) => sum + h, 0) + (branchRowCount - 1) * BRANCH_ROW_GAP
    : 0
  const totalHeight = mainBandHeight + extraBranchBelow
  return {
    mainBandHeight,
    branchRowHeights,
    branchBandHeight,
    branchRowCount,
    totalHeight,
    forkRegions,
  }
}

function resolveBranchRowTops(mainFlowTop, mainBandHeight, branchRowHeights) {
  if (!branchRowHeights.length) return []
  const tops = []
  tops[0] = mainFlowTop + (mainBandHeight - branchRowHeights[0]) / 2
  for (let i = 1; i < branchRowHeights.length; i += 1) {
    tops[i] = tops[i - 1] + branchRowHeights[i - 1] + BRANCH_ROW_GAP
  }
  return tops
}

function buildGraphPositions({
  byLevel,
  maxLevel,
  nodeMap,
  levels,
  branchRows,
  forkRegions,
  padding,
  metrics,
}) {
  const pos = new Map()
  const mainFlowTop = padding.padTop
  const mainRowCy = mainFlowTop + metrics.mainBandHeight / 2
  const branchRowTops = metrics.branchRowCount > 0
    ? resolveBranchRowTops(mainFlowTop, metrics.mainBandHeight, metrics.branchRowHeights)
    : []

  for (let lv = 0; lv <= maxLevel; lv += 1) {
    const row = (byLevel.get(lv) || []).slice().sort((a, b) => a.localeCompare(b, 'zh-CN'))
    const branchNodes = row.filter((id) => branchRows.has(id))
    const spineNodes = row.filter((id) => !branchRows.has(id))

    for (const id of branchNodes) {
      const meta = nodeMap.get(id)
      const h = meta?.h || activeLayout.nodeHMin
      const rowIndex = branchRows.get(id) ?? 0
      const rowH = metrics.branchRowHeights[rowIndex] || activeLayout.nodeHMin
      const x = padding.padLeft + lv * (activeLayout.nodeW + H_GAP)
      const y = (branchRowTops[rowIndex] ?? mainFlowTop) + (rowH - h) / 2
      pos.set(id, {
        x,
        y,
        w: activeLayout.nodeW,
        h,
        cx: x + activeLayout.nodeW / 2,
        cy: y + h / 2,
        level: levels.get(id) ?? lv,
      })
    }

    if (!spineNodes.length) continue

    const stackH = spineNodes.reduce((sum, id) => sum + (nodeMap.get(id)?.h || activeLayout.nodeHMin), 0)
      + Math.max(0, spineNodes.length - 1) * V_GAP
    let y = mainRowCy - stackH / 2

    spineNodes.forEach((id) => {
      const meta = nodeMap.get(id)
      const h = meta?.h || activeLayout.nodeHMin
      const x = padding.padLeft + lv * (activeLayout.nodeW + H_GAP)
      const nodeY = mainRowCy - h / 2
      pos.set(id, {
        x,
        y: nodeY,
        w: activeLayout.nodeW,
        h,
        cx: x + activeLayout.nodeW / 2,
        cy: nodeY + h / 2,
        level: levels.get(id) ?? lv,
      })
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

function outgoingAlwaysTargets(id, edges) {
  return edges
    .filter((e) => e.from === id && (e.condition || 'always') !== 'reject')
    .map((e) => e.to)
}

function isForkSplitNode(id, edges, nodeMap) {
  const meta = nodeMap.get(id)
  if (meta?.visualType !== 'fork_gate') return false
  const ins = edges.filter((e) => e.to === id && (e.condition || 'always') !== 'reject')
  const outs = outgoingAlwaysTargets(id, edges)
  return ins.length === 1 && outs.length > 1
}

function findDirectMergeNode(children, edges) {
  const counts = new Map()
  for (const cid of children) {
    for (const to of outgoingAlwaysTargets(cid, edges)) {
      counts.set(to, (counts.get(to) || 0) + 1)
    }
  }
  for (const [mid, count] of counts) {
    if (count === children.length) return mid
  }
  return null
}

function isForkMergeNode(id, edges, nodeMap) {
  const meta = nodeMap.get(id)
  if (meta?.visualType !== 'fork_gate') return false
  const ins = edges.filter((e) => e.to === id && (e.condition || 'always') !== 'reject')
  const outs = outgoingAlwaysTargets(id, edges)
  return ins.length > 1 && outs.length === 1
}

function collectReachable(startId, edges, nodeMap) {
  const seen = new Set()
  const queue = [startId]
  while (queue.length) {
    const id = queue.shift()
    if (seen.has(id)) continue
    seen.add(id)
    for (const to of outgoingAlwaysTargets(id, edges)) {
      if (nodeMap.has(to)) queue.push(to)
    }
  }
  return seen
}

function findBranchMergeNode(children, edges, nodeMap) {
  const direct = findDirectMergeNode(children, edges)
  if (direct) return direct
  if (!children.length) return null
  const reachableSets = children.map((cid) => collectReachable(cid, edges, nodeMap))
  let common = [...reachableSets[0]]
  for (let i = 1; i < reachableSets.length; i += 1) {
    const set = reachableSets[i]
    common = common.filter((id) => set.has(id))
  }
  const mergeCandidates = common
    .filter((id) => isForkMergeNode(id, edges, nodeMap))
    .sort((a, b) => a.localeCompare(b, 'zh-CN'))
  return mergeCandidates[0] || null
}

function collectBranchDescendants(startId, mergeId, edges, nodeMap) {
  const into = new Set()
  const queue = [startId]
  while (queue.length) {
    const id = queue.shift()
    if (into.has(id)) continue
    into.add(id)
    for (const to of outgoingAlwaysTargets(id, edges)) {
      if (to === mergeId || !nodeMap.has(to)) continue
      queue.push(to)
    }
  }
  return into
}

/** fork 分裂：各分支占独立行，分支内仍按拓扑层级横向展开；不修改 level，仅分配 branchRows */
function assignForkBranchRows(levels, edges, nodeMap) {
  const branchRows = new Map()
  const forkRegions = []
  const forkIds = [...nodeMap.keys()]
    .filter((id) => isForkSplitNode(id, edges, nodeMap))
    .sort((a, b) => {
      const la = levels.get(a) ?? 0
      const lb = levels.get(b) ?? 0
      if (la !== lb) return la - lb
      return a.localeCompare(b, 'zh-CN')
    })

  for (const forkId of forkIds) {
    const children = outgoingAlwaysTargets(forkId, edges)
      .sort((a, b) => a.localeCompare(b, 'zh-CN'))
    if (children.length <= 1) continue

    const mergeId = findBranchMergeNode(children, edges, nodeMap)
    const regionIds = new Set([forkId])
    if (mergeId) regionIds.add(mergeId)

    children.forEach((cid, branchIndex) => {
      branchRows.set(cid, branchIndex)
      regionIds.add(cid)
      for (const did of collectBranchDescendants(cid, mergeId, edges, nodeMap)) {
        branchRows.set(did, branchIndex)
        regionIds.add(did)
      }
    })

    forkRegions.push({
      forkId,
      mergeId,
      regionIds,
      branchCount: children.length,
    })
  }
  return { branchRows, forkRegions }
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
