import { marked } from 'marked'

marked.setOptions({ breaks: true })

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/

const META_LABELS = {
  doc_id: 'Doc ID',
  product_name: '产品名称',
  last_modified: '最后修改',
  last_modified_by: '修改者',
  element_count: '元素数量',
  adr_count: 'ADR 数量',
  intent_source_count: '意图来源数',
  confidence: '置信度',
  feature_id: '特性 ID',
  scenario_id: '场景 ID',
  scenario_type: '场景类型',
  status: '状态',
  title: '标题',
  ir_id: 'IR ID',
  requirement_id: '需求 ID',
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function parseSimpleYamlBlock(block) {
  const meta = {}
  const lines = String(block || '').split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const idx = trimmed.indexOf(':')
    if (idx <= 0) continue
    const key = trimmed.slice(0, idx).trim()
    let value = trimmed.slice(idx + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"'))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    meta[key] = value
  }
  return meta
}

export function parseMarkdownDocument(text) {
  const raw = text != null ? String(text) : ''
  const match = raw.match(FRONTMATTER_RE)
  if (!match) {
    return { meta: {}, body: raw }
  }
  return {
    meta: parseSimpleYamlBlock(match[1]),
    body: match[2] || '',
  }
}

export function formatMetaLabel(key) {
  const name = String(key || '').trim()
  if (!name) return ''
  if (META_LABELS[name]) return META_LABELS[name]
  return name.replace(/_/g, ' ')
}

export function formatMetaValue(value) {
  if (value == null || value === '') return '—'
  if (Array.isArray(value)) {
    return value.map((item) => formatMetaValue(item)).join(', ')
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

export function buildMetaEntries(meta) {
  if (!meta || typeof meta !== 'object') return []
  return Object.entries(meta)
    .filter(([key]) => String(key || '').trim())
    .map(([key, value]) => ({
      key,
      label: formatMetaLabel(key),
      value: formatMetaValue(value),
    }))
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

export function renderMarkdownDocument(text, metaOverride = null) {
  const parsed = parseMarkdownDocument(text)
  const hasServerMeta = metaOverride && typeof metaOverride === 'object' && Object.keys(metaOverride).length > 0
  const meta = hasServerMeta ? metaOverride : parsed.meta
  const body = hasServerMeta ? String(text || '') : parsed.body
  return {
    meta,
    metaEntries: buildMetaEntries(meta),
    body,
    html: renderMarkdown(body),
  }
}
