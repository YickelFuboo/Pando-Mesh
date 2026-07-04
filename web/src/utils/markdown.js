import { marked } from 'marked'
import { encode as encodePlantUml } from 'plantuml-encoder'

marked.setOptions({ breaks: true })

const PLANTUML_LANGS = new Set(['plantuml', 'puml', 'uml'])
const PLANTUML_SERVER = 'https://www.plantuml.com/plantuml/svg'

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/
const HEADING_RE = /^(#{1,6})\s+(.+)$/

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

const META_UI_HIDDEN_KEYS = new Set([
  'feature_path',
  'last_modified_by',
  'intent_source_count',
])

const META_UI_VISIBLE_WITH_NODE = new Set([
  'last_modified',
  'confidence',
])

function normalizeMetaKey(key) {
  return String(key || '').trim().toLowerCase().replace(/\s+/g, '_')
}

export function buildDisplayMetaEntries(meta, { hasNode = false } = {}) {
  return buildMetaEntries(meta).filter((entry) => {
    const key = normalizeMetaKey(entry.key)
    if (META_UI_HIDDEN_KEYS.has(key)) return false
    if (hasNode) {
      if (key === 'name' || key === 'id' || key === 'feature_id') return false
      return META_UI_VISIBLE_WITH_NODE.has(key)
    }
    return true
  })
}

let headingIdSet = new Set()
let headingIdQueue = null

marked.use({
  renderer: {
    heading(token) {
      const inner = this.parser.parseInline(token.tokens)
      const plain = stripInlineMarkdown(token.text || inner)
      let id
      if (headingIdQueue && headingIdQueue.length) {
        id = headingIdQueue.shift()
        headingIdSet.add(id)
      } else {
        id = createHeadingId(plain, headingIdSet)
      }
      return `<h${token.depth} id="${id}">${inner}</h${token.depth}>\n`
    },
    code(token) {
      return renderCodeBlock(token)
    },
  },
})

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function isPlantUmlBlock(lang, text) {
  const normalized = String(lang || '').trim().toLowerCase()
  if (PLANTUML_LANGS.has(normalized)) return true
  return /@startuml/i.test(String(text || ''))
}

function renderPlantUmlHtml(source) {
  const text = String(source || '').trim()
  if (!text) return ''
  try {
    const encoded = encodePlantUml(text)
    const src = `${PLANTUML_SERVER}/${encoded}`
    return (
      `<figure class="pm-plantuml">`
      + `<img class="pm-plantuml-img" src="${src}" alt="PlantUML 时序图" loading="lazy" decoding="async" />`
      + `</figure>\n`
    )
  } catch {
    return `<pre class="pm-plantuml-error"><code>${escapeHtml(text)}</code></pre>\n`
  }
}

function renderCodeBlock(token) {
  const text = token.text || ''
  const lang = token.lang || ''
  if (isPlantUmlBlock(lang, text)) {
    return renderPlantUmlHtml(text)
  }
  const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : ''
  return `<pre><code${langClass}>${escapeHtml(text)}</code></pre>\n`
}

function stripInlineMarkdown(text) {
  return String(text || '')
    .replace(/!\[[^\]]*]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)]\([^)]*\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/\s+#+\s*$/, '')
    .trim()
}

function createHeadingId(text, usedIds = headingIdSet) {
  let base = String(text || '').trim()
  base = base
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  if (!base) base = 'section'
  let id = base
  let index = 1
  while (usedIds.has(id)) {
    id = `${base}-${index}`
    index += 1
  }
  usedIds.add(id)
  return id
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

export function extractMarkdownHeadings(body) {
  const usedIds = new Set()
  const headings = []
  for (const line of String(body || '').split('\n')) {
    const match = line.match(HEADING_RE)
    if (!match) continue
    const level = match[1].length
    const title = stripInlineMarkdown(match[2])
    if (!title) continue
    headings.push({
      level,
      title,
      id: createHeadingId(title, usedIds),
    })
  }
  return headings
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

export function renderMarkdown(text, headingIds = null) {
  const s = text != null ? String(text) : ''
  if (!s.trim()) return ''
  headingIdSet = new Set()
  headingIdQueue = Array.isArray(headingIds) && headingIds.length ? [...headingIds] : null
  try {
    return marked.parse(s)
  } catch {
    return escapeHtml(s)
  } finally {
    headingIdQueue = null
  }
}

export function renderMarkdownDocument(text, metaOverride = null) {
  const parsed = parseMarkdownDocument(text)
  const hasServerMeta = metaOverride && typeof metaOverride === 'object' && Object.keys(metaOverride).length > 0
  const meta = hasServerMeta ? metaOverride : parsed.meta
  const body = hasServerMeta ? String(text || '') : parsed.body
  const headings = extractMarkdownHeadings(body)
  return {
    meta,
    metaEntries: buildMetaEntries(meta),
    body,
    headings,
    html: renderMarkdown(body, headings.map((item) => item.id)),
  }
}
