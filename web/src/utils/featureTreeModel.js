export function statusColor(status, nodeType, scenarioType) {
  if (nodeType === 'root') return { dot: '#f97316', bg: '#fff7ed', border: '#fed7aa' }
  if (nodeType === 'scenario') {
    return { dot: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe' }
  }
  const s = String(status || '').toLowerCase()
  if (s === 'implemented') return { dot: '#3b82f6', bg: '#eff6ff', border: '#bfdbfe' }
  if (s === 'partial') return { dot: '#f97316', bg: '#fff7ed', border: '#fed7aa' }
  if (s === 'planned') return { dot: '#eab308', bg: '#fefce8', border: '#fde68a' }
  return { dot: '#9ca3af', bg: '#f9fafb', border: '#e5e7eb' }
}

export function statusLabel(status, nodeType, scenarioType) {
  if (nodeType === 'root') return 'ROOT'
  if (nodeType === 'scenario') {
    const st = String(scenarioType || '').trim()
    return st || '场景'
  }
  const map = {
    implemented: '已实现',
    partial: '部分实现',
    planned: '已规划',
  }
  return map[String(status || '').toLowerCase()] || status || ''
}

export function findNodeById(root, nodeId) {
  if (!root || !nodeId) return null
  if (root.id === nodeId) return root
  for (const child of root.children || []) {
    const found = findNodeById(child, nodeId)
    if (found) return found
  }
  return null
}

export function findParentNode(root, nodeId) {
  if (!root || !nodeId) return null
  for (const child of root.children || []) {
    if (child.id === nodeId) return root
    const found = findParentNode(child, nodeId)
    if (found) return found
  }
  return null
}

export function scenarioWorkspaceFilePath(node) {
  const rel = String(node?.path || '').trim().replace(/^\/+/, '')
  if (!rel) return ''
  return rel.startsWith('features/') ? rel : `features/${rel}`
}

export function isFeatureLeafNode(node) {
  if (!node || node.node_type !== 'feature') return false
  const children = node.children || []
  if (!children.length) return true
  return children.every((child) => child.node_type === 'scenario')
}

export function isFeatureBranchNode(node) {
  if (!node || node.node_type !== 'feature') return false
  return !isFeatureLeafNode(node)
}

export function featureSpecWorkspaceFilePath(node) {
  if (!node?.path) return ''
  const spec = String(node.spec_path || 'spec.md').trim().replace(/^\/+/, '')
  const dir = String(node.path).replace(/\/feature\.yaml$/i, '').replace(/\\/g, '/')
  const rel = `${dir}/${spec}`.replace(/\/+/g, '/')
  return rel.startsWith('features/') ? rel : `features/${rel}`
}

export function cloneSubtree(node) {
  if (!node) return null
  return {
    ...node,
    children: (node.children || []).map(cloneSubtree),
  }
}

export function buildFeatureOverviewRoot(root) {
  if (!root) return null
  return {
    ...root,
    children: (root.children || []).map((child) => ({
      ...child,
      children: [],
    })),
  }
}

export function flattenTree(node, parentId = null, rows = []) {
  if (!node) return rows
  rows.push({ ...node, parentId })
  for (const child of node.children || []) {
    flattenTree(child, node.id, rows)
  }
  return rows
}

export function collectExpandIds(root, maxDepth = 2) {
  const ids = new Set()
  function walk(node, depth) {
    if (!node?.id) return
    if (depth <= maxDepth) ids.add(node.id)
    for (const child of node.children || []) walk(child, depth + 1)
  }
  walk(root, 0)
  return ids
}

export function collectExpandIdsFromChildren(root, maxDepth = 2) {
  const ids = new Set()
  function walk(node, depth) {
    if (!node?.id) return
    if (depth <= maxDepth) ids.add(node.id)
    for (const child of node.children || []) walk(child, depth + 1)
  }
  for (const child of root?.children || []) walk(child, 0)
  return ids
}
