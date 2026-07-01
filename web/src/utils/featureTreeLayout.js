const NODE_W = 140
const MIN_NODE_H = 50
const H_GAP = 44
const V_GAP = 12
const PAD = 20
const TOP_PAD = 7
const HEADER_H = 14
const TITLE_LH = 11
const STATUS_H = 12
const BOTTOM_PAD = 5

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

function measureNode(node) {
  const idLine = node.level && node.level !== 'root' && node.level !== 'scenario'
    ? node.level
    : (node.node_type === 'scenario' ? 'SCN' : 'ROOT')
  const titleLines = wrapText(node.name || node.id, 11)
  const h = TOP_PAD + HEADER_H + titleLines.length * TITLE_LH + STATUS_H + BOTTOM_PAD
  return { idLine, titleLines, h: Math.max(MIN_NODE_H, h) }
}

function layoutSubtree(root) {
  if (!root) {
    return { width: 320, height: 120, nodes: [], edges: [] }
  }

  const nodes = []
  const edges = []
  const measured = new Map()

  function countLeaves(node) {
    const children = node.children || []
    if (!children.length) return 1
    return children.reduce((sum, child) => sum + countLeaves(child), 0)
  }

  function assign(node, depth, leafCursor) {
    measured.set(node.id, measureNode(node))
    const children = node.children || []
    let nextLeaf = leafCursor
    if (!children.length) {
      node._depth = depth
      node._leaf = leafCursor
      return leafCursor + 1
    }
    for (const child of children) {
      nextLeaf = assign(child, depth + 1, nextLeaf)
      edges.push({ from: node.id, to: child.id })
    }
    node._depth = depth
    node._leaf = (children[0]._leaf + children[children.length - 1]._leaf) / 2
    return nextLeaf
  }

  const leafCount = countLeaves(root)
  assign(root, 0, 0)

  const leafHeights = new Array(leafCount).fill(MIN_NODE_H)
  function collectLeafHeights(node) {
    if (!(node.children || []).length) {
      leafHeights[node._leaf] = measured.get(node.id).h
    } else {
      for (const child of node.children || []) collectLeafHeights(child)
    }
  }
  collectLeafHeights(root)

  const rowStarts = new Array(leafCount)
  let rowY = PAD
  for (let i = 0; i < leafCount; i += 1) {
    rowStarts[i] = rowY
    rowY += leafHeights[i] + V_GAP
  }

  const placed = new Map()

  function placeNode(node) {
    const meta = measured.get(node.id)
    const children = node.children || []
    let y
    if (!children.length) {
      y = rowStarts[node._leaf]
    } else {
      for (const child of children) placeNode(child)
      const centers = children.map((child) => placed.get(child.id).y + placed.get(child.id).h / 2)
      const avgCenter = centers.reduce((sum, v) => sum + v, 0) / centers.length
      y = avgCenter - meta.h / 2
    }
    const x = PAD + node._depth * (NODE_W + H_GAP)
    placed.set(node.id, {
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
      scenarioType: node.scenario_type,
      level: node.level,
      description: node.description,
    })
  }
  placeNode(root)

  for (const [, node] of placed) nodes.push(node)

  const maxDepth = Math.max(0, ...nodes.map((n) => {
    const depth = (n.x - PAD) / (NODE_W + H_GAP)
    return Math.round(depth)
  }))
  const width = PAD * 2 + (maxDepth + 1) * NODE_W + maxDepth * H_GAP
  const height = rowY - V_GAP + PAD

  const layoutEdges = edges.map((edge) => {
    const from = placed.get(edge.from)
    const to = placed.get(edge.to)
    if (!from || !to) return null
    const x1 = from.x + from.w
    const y1 = from.y + from.h / 2
    const x2 = to.x
    const y2 = to.y + to.h / 2
    const mx = (x1 + x2) / 2
    return {
      ...edge,
      path: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
    }
  }).filter(Boolean)

  return {
    width: Math.max(width, 480),
    height: Math.max(height, 240),
    nodes,
    edges: layoutEdges,
  }
}

export function buildFeatureTreeLayout(rootNode) {
  return layoutSubtree(rootNode)
}

export const FEATURE_LAYOUT = {
  NODE_W,
  MIN_NODE_H,
  H_GAP,
  V_GAP,
  PAD,
  TOP_PAD,
  HEADER_H,
  TITLE_LH,
  STATUS_H,
  BOTTOM_PAD,
}
