import { readNodeOutputDocPaths } from './planGraphEdit.js'
import { findGraphNode } from './planGraphState.js'

function fileBaseName(path) {
  const normalized = String(path || '').replace(/\\/g, '/')
  const parts = normalized.split('/').filter(Boolean)
  const last = parts[parts.length - 1] || ''
  if (last.includes('{*}') || last.includes('{re:')) {
    const parent = parts[parts.length - 2] || ''
    if (parent && !parent.includes('{') && !parent.includes('{re:')) {
      return `${parent}/…`
    }
    return '通配文档'
  }
  return last || normalized || '未命名'
}

function pushItem(items, seen, item) {
  const key = item.id || item.path
  if (!key || seen.has(key)) return
  seen.add(key)
  items.push(item)
}

export function resolveNodeOutputPatterns(graphSpec, nodeId) {
  const node = findGraphNode(graphSpec, nodeId)
  if (!node) return []
  return readNodeOutputDocPaths(node)
}

export function buildDeliverableFileItems(workspaceRefs, outputPatterns) {
  const items = []
  const seen = new Set()
  const outputRefs = (workspaceRefs || []).filter((ref) => ref?.label === '输出')

  for (const ref of outputRefs) {
    if (ref.wildcard) {
      const matches = Array.isArray(ref.matches) ? ref.matches : []
      if (!matches.length) {
        pushItem(items, seen, {
          id: ref.path,
          name: fileBaseName(ref.path),
          path: ref.path,
          resolvedPath: '',
          exists: false,
        })
        continue
      }
      for (const match of matches) {
        const resolvedPath = String(match?.resolved_path || '').trim()
        pushItem(items, seen, {
          id: resolvedPath || ref.path,
          name: fileBaseName(resolvedPath || ref.path),
          path: ref.path,
          resolvedPath,
          exists: true,
          preview: String(match?.preview || ''),
        })
      }
      continue
    }
    if (ref.kind === 'file' && ref.exists) {
      const resolvedPath = String(ref.resolved_path || '').trim()
      pushItem(items, seen, {
        id: resolvedPath || ref.path,
        name: fileBaseName(resolvedPath || ref.path),
        path: ref.path,
        resolvedPath,
        exists: true,
        preview: String(ref.preview || ''),
      })
      continue
    }
    pushItem(items, seen, {
      id: ref.path,
      name: fileBaseName(ref.path),
      path: ref.path,
      resolvedPath: String(ref.resolved_path || '').trim(),
      exists: Boolean(ref.exists),
      preview: String(ref.preview || ''),
    })
  }

  for (const pattern of outputPatterns || []) {
    if (items.some((item) => item.path === pattern)) continue
    pushItem(items, seen, {
      id: pattern,
      name: fileBaseName(pattern),
      path: pattern,
      resolvedPath: '',
      exists: false,
    })
  }
  return items
}
