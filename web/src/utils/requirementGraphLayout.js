const NODE_W = 144
const MIN_NODE_H = 50
const H_GAP = 40
const V_GAP = 12
const PAD = 20
const TOP_PAD = 6
const HEADER_H = 14
const TITLE_BASELINE = 10
const TITLE_LH = 13
const STATUS_GAP = 6
const STATUS_H = 10
const BOTTOM_PAD = 5
const COLUMN_BY_TYPE = {
  requirement: 0,
  scenario: 1,
  architecture: 2,
  repo: 3,
  root: 0,
}

function wrapText(text, maxChars) {
  const raw = String(text || '').trim()
  if (!raw) return ['']
  if (raw.length <= maxChars) return [raw]
  const lines = []
  let rest = raw
  while (rest.length > maxChars && lines.length < 2) {
    lines.push(rest.slice(0, maxChars))
    rest = rest.slice(maxChars)
  }
  if (rest) lines.push(rest.length > maxChars ? `${rest.slice(0, maxChars - 1)}…` : rest)
  return lines.slice(0, 2)
}

function measureTitleBlock(titleLines) {
  if (!titleLines.length) return 0
  return TITLE_BASELINE + Math.max(0, titleLines.length - 1) * TITLE_LH
}

function measureNode(node) {
  const idLine = node.level || node.node_type?.toUpperCase() || ''
  const titleLines = wrapText(node.name || node.id, 14)
  const titleBlock = measureTitleBlock(titleLines)
  const h = TOP_PAD + HEADER_H + titleBlock + STATUS_GAP + STATUS_H + BOTTOM_PAD
  return { idLine, titleLines, h: Math.max(MIN_NODE_H, h) }
}

export function buildRequirementGraphLayout(rootNode) {
  if (!rootNode) {
    return { width: 320, height: 120, nodes: [], edges: [] }
  }

  const flatNodes = []
  const treeEdges = []
  const linkEdges = []

  function walk(node, parentId) {
    if (node.node_type === 'root') {
      for (const child of node.children || []) walk(child, null)
      return
    }
    flatNodes.push(node)
    if (parentId) treeEdges.push({ from: parentId, to: node.id, kind: 'tree' })
    for (const child of node.children || []) walk(child, node.id)
    if (node.node_type === 'scenario') {
      for (const arId of node.source_arch_changes || []) {
        const irPrefix = String(node.id).split('::')[0]
        linkEdges.push({ from: node.id, to: `${irPrefix}::${arId}`, kind: 'link' })
      }
    }
  }
  walk(rootNode, null)

  const byColumn = new Map()
  for (const node of flatNodes) {
    const col = COLUMN_BY_TYPE[node.node_type] ?? 1
    if (!byColumn.has(col)) byColumn.set(col, [])
    byColumn.get(col).push(node)
  }

  const columnHeights = []
  for (const colNodes of byColumn.values()) {
    const colH = colNodes.reduce((sum, node) => sum + measureNode(node).h, 0)
      + Math.max(0, colNodes.length - 1) * V_GAP
    columnHeights.push(colH)
  }
  const maxColH = Math.max(MIN_NODE_H, ...columnHeights, 0)

  const layoutNodes = []
  for (const [col, colNodes] of byColumn.entries()) {
    const measuredCol = colNodes.map((node) => ({ node, meta: measureNode(node) }))
    const colH = measuredCol.reduce((sum, item) => sum + item.meta.h, 0)
      + Math.max(0, measuredCol.length - 1) * V_GAP
    let y = PAD + Math.max(0, (maxColH - colH) / 2)
    measuredCol.forEach(({ node, meta }) => {
      const x = PAD + col * (NODE_W + H_GAP)
      layoutNodes.push({
        id: node.id,
        x,
        y,
        w: NODE_W,
        h: meta.h,
        cx: x + NODE_W / 2,
        idLine: meta.idLine,
        titleLines: meta.titleLines,
        status: node.status,
        nodeType: node.node_type,
        description: node.description,
      })
      y += meta.h + V_GAP
    })
  }

  function edgePath(fromId, toId) {
    const from = layoutNodes.find((n) => n.id === fromId)
    const to = layoutNodes.find((n) => n.id === toId)
    if (!from || !to) return null
    const x1 = from.x + from.w
    const y1 = from.y + from.h / 2
    const x2 = to.x
    const y2 = to.y + to.h / 2
    const mx = (x1 + x2) / 2
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`
  }

  const layoutEdges = [...treeEdges, ...linkEdges]
    .map((edge) => {
      const path = edgePath(edge.from, edge.to)
      if (!path) return null
      return { ...edge, path }
    })
    .filter(Boolean)

  const maxCol = Math.max(0, ...layoutNodes.map((n) => n.x))
  const maxRow = Math.max(0, ...layoutNodes.map((n) => n.y + n.h))
  return {
    width: Math.max(maxCol + NODE_W + PAD, 560),
    height: Math.max(maxRow + PAD, 260),
    nodes: layoutNodes,
    edges: layoutEdges,
  }
}

export const REQUIREMENT_LAYOUT = {
  NODE_W,
  MIN_NODE_H,
  TOP_PAD,
  HEADER_H,
  TITLE_BASELINE,
  TITLE_LH,
  STATUS_GAP,
  STATUS_H,
  BOTTOM_PAD,
}
