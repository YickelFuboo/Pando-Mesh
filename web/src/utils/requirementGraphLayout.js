const NODE_W = 108
const NODE_H = 40
const H_GAP = 40
const V_GAP = 10
const PAD = 20
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
  return [raw.slice(0, maxChars), raw.length > maxChars * 2 ? `${raw.slice(maxChars, maxChars * 2 - 1)}…` : raw.slice(maxChars)]
}

export function buildRequirementGraphLayout(rootNode) {
  if (!rootNode) {
    return { width: 320, height: 120, nodes: [], edges: [] }
  }

  const flatNodes = []
  const treeEdges = []
  const linkEdges = []

  function walk(node, parentId) {
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

  const layoutNodes = []
  let maxRows = 1
  for (const [, colNodes] of byColumn.entries()) {
    maxRows = Math.max(maxRows, colNodes.length)
  }

  for (const [col, colNodes] of byColumn.entries()) {
    const colH = colNodes.length * NODE_H + Math.max(0, colNodes.length - 1) * V_GAP
    const startY = PAD + Math.max(0, (maxRows * (NODE_H + V_GAP) - V_GAP - colH) / 2)
    colNodes.forEach((node, index) => {
      const x = PAD + col * (NODE_W + H_GAP)
      const y = startY + index * (NODE_H + V_GAP)
      const idLine = node.level || node.node_type?.toUpperCase() || ''
      layoutNodes.push({
        id: node.id,
        x,
        y,
        w: NODE_W,
        h: NODE_H,
        cx: x + NODE_W / 2,
        idLine,
        titleLines: wrapText(node.name || node.id, 10),
        status: node.status,
        nodeType: node.node_type,
        description: node.description,
      })
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
    width: Math.max(maxCol + NODE_W + PAD, 520),
    height: Math.max(maxRow + PAD, 240),
    nodes: layoutNodes,
    edges: layoutEdges,
  }
}
