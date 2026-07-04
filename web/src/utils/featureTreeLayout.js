const NODE_W = 128
const MIN_NODE_H = 44
const H_GAP = 40
const V_GAP = 10
const PAD = 20
const TOP_PAD = 6
const HEADER_H = 11
const TITLE_LH = 9
const STATUS_H = 10
const BOTTOM_PAD = 4

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
  const titleLines = wrapText(node.name || node.id, 13)
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

function measureArchNode(element) {
  const idLine = String(element.element_id || '').toUpperCase() || 'NF'
  const titleLines = wrapText(element.name || element.element_id, 13)
  const h = TOP_PAD + HEADER_H + titleLines.length * TITLE_LH + STATUS_H + BOTTOM_PAD
  return { idLine, titleLines, h: Math.max(MIN_NODE_H, h) }
}

function collectFeatureArchLinks(rootNode) {
  const featureArchLinks = []
  const archElements = new Map()

  function walk(node) {
    if (node?.node_type === 'feature') {
      for (const ref of node.architecture_refs || []) {
        const elementId = String(ref?.element_id || '').trim()
        if (!elementId) continue
        if (!archElements.has(elementId)) {
          archElements.set(elementId, {
            element_id: elementId,
            name: ref.name || elementId.toUpperCase(),
            path: ref.path || '',
            role: ref.role || '',
          })
        }
        featureArchLinks.push({ from: node.id, to: elementId, kind: 'arch' })
      }
    }
    for (const child of node.children || []) walk(child)
  }
  walk(rootNode)
  return { featureArchLinks, archElements }
}

export function buildFeatureTopologyLayout(rootNode, archNameMap = {}) {
  const base = buildFeatureTreeLayout(rootNode)
  const { featureArchLinks, archElements } = collectFeatureArchLinks(rootNode)
  if (!archElements.size) return base

  for (const [elementId, element] of archElements) {
    const mappedName = archNameMap[elementId]
    if (mappedName) element.name = mappedName
  }

  const nodeById = Object.fromEntries(base.nodes.map((node) => [node.id, node]))
  const maxDepth = Math.max(
    0,
    ...base.nodes.map((node) => Math.round((node.x - PAD) / (NODE_W + H_GAP))),
  )
  const archColX = PAD + (maxDepth + 1) * (NODE_W + H_GAP)

  const archNodesToPlace = [...archElements.entries()].map(([elementId, element]) => {
    const sources = featureArchLinks
      .filter((link) => link.to === elementId)
      .map((link) => nodeById[link.from])
      .filter(Boolean)
    const centerY = sources.length
      ? sources.reduce((sum, node) => sum + node.y + node.h / 2, 0) / sources.length
      : PAD + MIN_NODE_H / 2
    return { elementId, element, centerY }
  })
  archNodesToPlace.sort((a, b) => a.centerY - b.centerY)

  const archLayoutNodes = []
  let nextArchY = PAD
  for (const item of archNodesToPlace) {
    const meta = measureArchNode(item.element)
    const y = Math.max(item.centerY - meta.h / 2, nextArchY)
    const layoutId = `arch::${item.elementId}`
    archLayoutNodes.push({
      id: layoutId,
      x: archColX,
      y,
      w: NODE_W,
      h: meta.h,
      cx: archColX + NODE_W / 2,
      idLine: meta.idLine,
      titleLines: meta.titleLines,
      status: item.element.role || 'element',
      nodeType: 'element',
      elementId: item.elementId,
      description: item.element.path,
      level: 'NF',
    })
    nextArchY = y + meta.h + V_GAP
    nodeById[layoutId] = archLayoutNodes[archLayoutNodes.length - 1]
  }

  const archEdges = featureArchLinks.map((link) => {
    const from = nodeById[link.from]
    const to = nodeById[`arch::${link.to}`]
    if (!from || !to) return null
    const x1 = from.x + from.w
    const y1 = from.y + from.h / 2
    const x2 = to.x
    const y2 = to.y + to.h / 2
    const mx = (x1 + x2) / 2
    return {
      ...link,
      path: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
    }
  }).filter(Boolean)

  const allNodes = [...base.nodes, ...archLayoutNodes]
  const width = Math.max(
    base.width,
    archColX + NODE_W + PAD,
  )
  const maxNodeBottom = Math.max(...allNodes.map((node) => node.y + node.h))
  const height = Math.max(base.height, maxNodeBottom + PAD)

  return {
    width: Math.max(width, 480),
    height: Math.max(height, 240),
    nodes: allNodes,
    edges: [...base.edges, ...archEdges],
  }
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
