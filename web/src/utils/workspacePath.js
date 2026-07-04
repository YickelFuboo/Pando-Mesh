export function normalizeWorkspaceRelativePath(path) {
  return String(path || '').trim().replace(/\\/g, '/')
}

export function workspacePathBasename(path) {
  const normalized = normalizeWorkspaceRelativePath(path)
  const index = normalized.lastIndexOf('/')
  return index >= 0 ? normalized.slice(index + 1) : normalized
}

export function workspaceFileDisplayPath(data, fallback = '') {
  return normalizeWorkspaceRelativePath(data?.path || fallback)
}
