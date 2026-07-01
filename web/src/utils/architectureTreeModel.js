export const ARCH_ROOT_ID = 'architectures_root'

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

export function collectViewElements(viewNode) {
  if (!viewNode || viewNode.node_type !== 'view') return []
  return (viewNode.children || []).filter((child) => child.node_type === 'element')
}

export function flattenElements(root) {
  const rows = []
  function walk(node) {
    if (node?.node_type === 'element') rows.push(node)
    for (const child of node.children || []) walk(child)
  }
  for (const child of root?.children || []) walk(child)
  return rows
}

export function normalizeElementRow(node) {
  const elementId = String(node?.element_id || node?.id?.split('::').pop() || '').trim()
  return {
    id: elementId,
    element_id: elementId,
    name: node?.name || elementId,
    depends_on: node?.depends_on || [],
    depended_by: node?.depended_by || [],
    element_type: node?.element_type || '',
    confidence: node?.confidence || '',
    repo_path: node?.repo_path || '',
  }
}

export function elementWorkspaceFilePath(node) {
  const rel = String(node?.spec_path || node?.path || '').trim().replace(/^\/+/, '')
  if (!rel) return ''
  return rel.startsWith('architectures/') ? rel : `architectures/${rel}`
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

export function isArchitectureRootNode(node) {
  return node?.node_type === 'root' || node?.id === ARCH_ROOT_ID
}

export function architectureDocFilePath(node) {
  if (!node) return ''
  const rel = String(node.spec_path || node.path || '').trim().replace(/^\/+/, '')
  if (!rel || rel.endsWith('/')) return ''
  return rel.startsWith('architectures/') ? rel : `architectures/${rel}`
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

export function elementStatusColor(node) {
  const confidence = String(node?.confidence || '').toLowerCase()
  if (confidence === 'high') return { dot: '#3b82f6', bg: '#eff6ff', border: '#bfdbfe' }
  if (confidence === 'medium') return { dot: '#f97316', bg: '#fff7ed', border: '#fed7aa' }
  if (confidence === 'low') return { dot: '#eab308', bg: '#fefce8', border: '#fde68a' }
  return { dot: '#6366f1', bg: '#eef2ff', border: '#c7d2fe' }
}

export function elementStatusLabel(node) {
  const confidence = String(node?.confidence || '').trim()
  if (confidence) return confidence
  const type = String(node?.element_type || node?.elementType || '').trim()
  return type || 'element'
}
