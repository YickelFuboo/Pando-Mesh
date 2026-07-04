export function requirementStatusColor(status, nodeType) {
  if (nodeType === 'root') return { dot: '#f97316', bg: '#fff7ed', border: '#fed7aa' }
  if (nodeType === 'requirement') {
    const s = String(status || '').toLowerCase()
    if (s === 'decomposed') return { dot: '#3b82f6', bg: '#eff6ff', border: '#bfdbfe' }
    if (s === 'closed') return { dot: '#22c55e', bg: '#f0fdf4', border: '#bbf7d0' }
    if (s === 'analyzing') return { dot: '#f97316', bg: '#fff7ed', border: '#fed7aa' }
    return { dot: '#eab308', bg: '#fefce8', border: '#fde68a' }
  }
  if (nodeType === 'scenario') {
    const s = String(status || '').toLowerCase()
    if (s === 'blocked') return { dot: '#ef4444', bg: '#fef2f2', border: '#fecaca' }
    if (s === 'in_progress') return { dot: '#3b82f6', bg: '#eff6ff', border: '#bfdbfe' }
    if (s === 'modify') return { dot: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' }
    return { dot: '#22c55e', bg: '#f0fdf4', border: '#bbf7d0' }
  }
  if (nodeType === 'architecture') {
    const s = String(status || '').toLowerCase()
    if (s === 'done') return { dot: '#3b82f6', bg: '#eff6ff', border: '#bfdbfe' }
    return { dot: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe' }
  }
  if (nodeType === 'repo') {
    return { dot: '#06b6d4', bg: '#ecfeff', border: '#a5f3fc' }
  }
  return { dot: '#9ca3af', bg: '#f9fafb', border: '#e5e7eb' }
}

export function requirementStatusLabel(status, nodeType) {
  if (nodeType === 'root') return 'ROOT'
  if (nodeType === 'requirement') return String(status || 'IR')
  if (nodeType === 'scenario') return String(status || 'SR')
  if (nodeType === 'architecture') return String(status || 'AR')
  if (nodeType === 'repo') return 'REPO'
  return String(status || '')
}

export function requirementIdFromNode(node) {
  const id = String(node?.id || '').trim()
  if (!id) return ''
  return id.split('::')[0]
}

export function requirementWorkspaceFilePath(node, mdRel = '') {
  if (!node) return ''
  const reqId = requirementIdFromNode(node)
  if (!reqId) return ''
  const md = String(mdRel || node.md || '').trim().replace(/^\/+/, '')
  if (md) return `requirements/${reqId}/${md}`
  if (node.node_type === 'requirement') {
    return `requirements/${reqId}/需求描述.md`
  }
  return ''
}

export function requirementNodeDocs(node) {
  if (!node) return []
  if (Array.isArray(node.docs) && node.docs.length) {
    return node.docs
      .map((item) => ({
        label: String(item.label || '').trim() || String(item.md || '').replace(/\.md$/i, ''),
        md: String(item.md || '').trim(),
      }))
      .filter((item) => item.md)
  }
  const md = String(node.md || '').trim()
  if (md) {
    return [{ label: md.replace(/\.md$/i, ''), md }]
  }
  if (node.node_type === 'requirement') {
    return [{ label: '需求描述', md: '需求描述.md' }]
  }
  return []
}

export function requirementNodeBadge(node) {
  const type = String(node?.node_type || '').toLowerCase()
  if (type === 'requirement') return 'IR'
  if (type === 'scenario') return 'SR'
  if (type === 'architecture') return 'AR'
  if (type === 'repo') return 'REPO'
  return String(node?.level || '文档').toUpperCase()
}

export function isRequirementDocNode(node) {
  if (!node) return false
  return ['requirement', 'scenario', 'architecture', 'repo'].includes(String(node.node_type || ''))
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

export function cloneSubtree(node) {
  if (!node) return null
  return {
    ...node,
    children: (node.children || []).map(cloneSubtree),
  }
}

function virtualTopologyRoot(nodeId, children) {
  return {
    id: `${nodeId}::__topology`,
    name: '',
    level: 'root',
    status: 'root',
    node_type: 'root',
    description: '',
    children,
  }
}

export function buildRequirementDetailTopologyRoot(detailNode, treeRoot) {
  if (!detailNode) return null
  const cloned = cloneSubtree(detailNode)
  const type = String(detailNode.node_type || '')
  const irId = requirementIdFromNode(detailNode)
  const irNode = treeRoot ? findNodeById(treeRoot, irId) : null

  if (type === 'scenario') {
    const linkedArIds = new Set(detailNode.source_arch_changes || [])
    const arNodes = (irNode?.children || [])
      .filter((node) => node.node_type === 'architecture' && linkedArIds.has(node.ar_id))
      .map(cloneSubtree)
    if (!arNodes.length) return cloned
    return virtualTopologyRoot(detailNode.id, [cloned, ...arNodes])
  }

  if (type === 'architecture') {
    const linkedSrIds = new Set(detailNode.source_scenarios || [])
    const srNodes = (irNode?.children || [])
      .filter((node) => node.node_type === 'scenario' && linkedSrIds.has(node.sr_id))
      .map(cloneSubtree)
    if (!srNodes.length) return cloned
    return virtualTopologyRoot(detailNode.id, [...srNodes, cloned])
  }

  if (type === 'repo') {
    const parentAr = (irNode?.children || []).find(
      (node) => node.node_type === 'architecture'
        && (node.children || []).some((child) => child.id === detailNode.id),
    )
    if (!parentAr) return cloned
    return virtualTopologyRoot(detailNode.id, [cloneSubtree(parentAr)])
  }

  return cloned
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

export function flattenRequirementGraph(root) {
  const nodes = []
  const edges = []
  if (!root) return { nodes, edges }

  function walk(node, parentId) {
    nodes.push({ ...node, parentId })
    if (parentId) edges.push({ from: parentId, to: node.id, kind: 'tree' })
    for (const child of node.children || []) walk(child, node.id)
    if (node.node_type === 'scenario') {
      for (const arId of node.source_arch_changes || []) {
        const irPrefix = String(node.id).split('::')[0]
        edges.push({ from: node.id, to: `${irPrefix}::${arId}`, kind: 'link' })
      }
    }
  }
  walk(root, null)
  return { nodes, edges }
}
