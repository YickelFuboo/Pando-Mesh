import { marked } from 'marked'

marked.setOptions({ breaks: true })

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function renderMarkdown(text) {
  const s = text != null ? String(text) : ''
  if (!s.trim()) return ''
  try {
    return marked.parse(s)
  } catch {
    return escapeHtml(s)
  }
}
