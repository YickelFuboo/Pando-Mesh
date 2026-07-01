const NODE_W = 132
const MIN_NODE_H = 46
const H_GAP = 52
const V_GAP = 14
const PAD = 24

function wrapText(text, maxChars) {
  const raw = String(text || '').trim()
  if (!raw) return ['']
  if (raw.length <= maxChars) return [raw]
  return [raw.slice(0, maxChars), `${raw.slice(maxChars, maxChars * 2 - 1)}…`]
}

function computeDepths(elements) {
  const ids = new Set(elements.map((item) => item.element_id))
  const byId = Object.fromEntries(elements.map((item) => [item.element_id, item]))
  const depths = {}
  function depth(id, visiting = new Set()) {
    if (depths[id] !== undefined) return depths[id]
    if (visiting.has(id)) return 0
    visiting.add(id)
    const deps = (byId[id]?.depends_on || []).filter((dep) => ids.has(dep) && dep !== id)
    depths[id] = deps.length ? 1 + Math.max(...deps.map((dep) => depth(dep, visiting))) : 0
    return depths[id]
  }
  for (const item of elements) depth(item.element_id)
  return depths
}

export function buildArchitectureDepLayout(elements, focusElementId = '') {
  if (!elements?.length) {
    return { width: 480, height: 240, nodes: [], edges: [] }
  }

  let subset = elements
  if (focusElementId) {
    const byId = Object.fromEntries(elements.map((item) => [item.element_id, item]))
    const focus = byId[focusElementId]
    if (focus) {
      const ids = new Set([focusElementId])
      for (const dep of focus.depends_on || []) if (byId[dep]) ids.add(dep)
      for (const dep of focus.depended_by || []) if (byId[dep]) ids.add(dep)
      subset = elements.filter((item) => ids.has(item.element_id))
    }
  }

  const depths = computeDepths(subset)
  const columns = {}
  for (const item of subset) {
    const col = depths[item.element_id] || 0
    if (!columns[col]) columns[col] = []
    columns[col].push(item)
  }
  Object.values(columns).forEach((col) => {
    col.sort((a, b) => String(a.name || a.element_id).localeCompare(String(b.name || b.element_id)))
  })

  const colKeys = Object.keys(columns).map(Number).sort((a, b) => a - b)
  const nodes = []
  const edges = []
  const nodeMap = {}
  let maxColHeight = 0

  for (const col of colKeys) {
    const colItems = columns[col]
    const colHeight = colItems.length * MIN_NODE_H + Math.max(0, colItems.length - 1) * V_GAP
    maxColHeight = Math.max(maxColHeight, colHeight)
  }

  for (const col of colKeys) {
    const colItems = columns[col]
    const colHeight = colItems.length * MIN_NODE_H + Math.max(0, colItems.length - 1) * V_GAP
    const yOffset = PAD + Math.max(0, (maxColHeight - colHeight) / 2)
    colItems.forEach((item, index) => {
      const titleLines = wrapText(item.name || item.element_id, 11)
      const h = MIN_NODE_H + (titleLines.length > 1 ? 12 : 0)
      const x = PAD + col * (NODE_W + H_GAP)
      const y = yOffset + index * (MIN_NODE_H + V_GAP)
      const node = {
        id: item.element_id,
        x,
        y,
        w: NODE_W,
        h,
        titleLines,
        elementType: item.element_type,
        confidence: item.confidence,
        repoPath: item.repo_path,
      }
      nodes.push(node)
      nodeMap[item.element_id] = node
    })
  }

  const ids = new Set(subset.map((item) => item.element_id))
  for (const item of subset) {
    for (const dep of item.depends_on || []) {
      if (!ids.has(dep) || dep === item.element_id) continue
      const from = nodeMap[dep]
      const to = nodeMap[item.element_id]
      if (!from || !to) continue
      const x1 = from.x + from.w
      const y1 = from.y + from.h / 2
      const x2 = to.x
      const y2 = to.y + to.h / 2
      const mx = (x1 + x2) / 2
      edges.push({
        from: dep,
        to: item.element_id,
        path: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
      })
    }
  }

  const maxDepth = colKeys.length ? Math.max(...colKeys) : 0
  const width = PAD * 2 + (maxDepth + 1) * NODE_W + maxDepth * H_GAP
  const height = PAD * 2 + maxColHeight

  return {
    width: Math.max(width, 480),
    height: Math.max(height, 240),
    nodes,
    edges,
  }
}
