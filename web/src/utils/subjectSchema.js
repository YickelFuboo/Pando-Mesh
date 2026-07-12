export const SUBJECT_TYPE_WORKSPACE = 'workspace'
export const SUBJECT_TYPE_FEATURE = 'feature'
export const SUBJECT_TYPE_ARCH_ELEMENT = 'arch_element'
export const SUBJECT_TYPE_IR = 'ir'
export const SUBJECT_TYPE_SR = 'sr'
export const SUBJECT_TYPE_AR = 'ar'
export const SUBJECT_TYPE_REPO = 'repo'

export const ALL_SUBJECT_TYPE_OPTIONS = [
  { value: SUBJECT_TYPE_WORKSPACE, label: 'Workspace' },
  { value: SUBJECT_TYPE_FEATURE, label: '特性' },
  { value: SUBJECT_TYPE_ARCH_ELEMENT, label: '架构元素' },
  { value: SUBJECT_TYPE_IR, label: '需求 IR' },
  { value: SUBJECT_TYPE_SR, label: '需求 SR' },
  { value: SUBJECT_TYPE_AR, label: '需求 AR' },
  { value: SUBJECT_TYPE_REPO, label: '代码仓' },
]

const SUBJECT_TYPE_SPECS = {
  [SUBJECT_TYPE_WORKSPACE]: { kind: 'workspace', granularity: 'workspace' },
  [SUBJECT_TYPE_FEATURE]: { kind: 'feature', granularity: 'feature' },
  [SUBJECT_TYPE_ARCH_ELEMENT]: { kind: 'arch_element', granularity: 'arch_element' },
  [SUBJECT_TYPE_IR]: { kind: 'requirement', granularity: 'ir' },
  [SUBJECT_TYPE_SR]: { kind: 'requirement', granularity: 'sr' },
  [SUBJECT_TYPE_AR]: { kind: 'requirement', granularity: 'ar' },
  [SUBJECT_TYPE_REPO]: { kind: 'repo', granularity: 'repo' },
}

const GRANULARITY_LABELS = {
  workspace: '整库',
  feature: '特性',
  arch_element: '架构元素',
  ir: '需求单',
  sr: '场景 SR',
  ar: '架构 AR',
  repo: '代码仓',
}

export function normalizeSubjectType(value) {
  const key = String(value || '').trim().toLowerCase()
  if (SUBJECT_TYPE_SPECS[key]) return key
  if (key === 'requirement') return SUBJECT_TYPE_IR
  return SUBJECT_TYPE_IR
}

export function subjectTypeLabel(subjectType) {
  const item = ALL_SUBJECT_TYPE_OPTIONS.find((opt) => opt.value === normalizeSubjectType(subjectType))
  return item?.label || subjectType || '作业对象'
}

export function subjectTypeSpec(subjectType) {
  return { ...SUBJECT_TYPE_SPECS[normalizeSubjectType(subjectType)] }
}

export function resolveTemplateSubjectSchema(template) {
  const explicit = template?.subject_schema
  if (explicit && String(explicit.kind || '').trim()) {
    const kind = String(explicit.kind || 'requirement').trim().toLowerCase()
    const granularity = String(explicit.granularity || 'ir').trim().toLowerCase()
    return {
      kind,
      granularity,
      subject_type: schemaToSubjectType(kind, granularity),
      required_placeholders: Array.isArray(explicit.required_placeholders) ? explicit.required_placeholders : [],
      auto_expand: Boolean(explicit.auto_expand),
    }
  }
  const goal = String(template?.user_goal || '')
  if (goal.includes('{workspace}') && !goal.includes('{requirement_id}')) {
    return { kind: 'workspace', granularity: 'workspace', subject_type: SUBJECT_TYPE_WORKSPACE, required_placeholders: [], auto_expand: false }
  }
  let granularity = 'ir'
  if (goal.includes('{repo_id}')) return { kind: 'repo', granularity: 'repo', subject_type: SUBJECT_TYPE_REPO, required_placeholders: [], auto_expand: false }
  if (goal.includes('{sr_id}')) granularity = 'sr'
  else if (goal.includes('{ar_id}')) granularity = 'ar'
  return {
    kind: 'requirement',
    granularity,
    subject_type: schemaToSubjectType('requirement', granularity),
    required_placeholders: [],
    auto_expand: false,
  }
}

function schemaToSubjectType(kind, granularity) {
  for (const [subjectType, spec] of Object.entries(SUBJECT_TYPE_SPECS)) {
    if (spec.kind === kind && spec.granularity === granularity) {
      return subjectType
    }
  }
  if (kind === 'workspace') return SUBJECT_TYPE_WORKSPACE
  if (kind === 'feature') return SUBJECT_TYPE_FEATURE
  if (kind === 'arch_element') return SUBJECT_TYPE_ARCH_ELEMENT
  if (kind === 'repo') return SUBJECT_TYPE_REPO
  return SUBJECT_TYPE_IR
}

export function granularityLabel(granularity) {
  return GRANULARITY_LABELS[granularity] || granularity || ''
}

export function filterTemplatesBySubjectType(templates, subjectType) {
  const type = normalizeSubjectType(subjectType)
  return (templates || []).filter((tpl) => resolveTemplateSubjectSchema(tpl).subject_type === type)
}

export function findTemplateById(templates, templateId) {
  return (templates || []).find((item) => item.template_id === templateId) || null
}

export function objectSessionKey(item) {
  return String(item?.object_id || item?.subject_id || '').trim()
}

export function objectMatchesWorkflow(item, workflow) {
  if (!item || !workflow) return false
  return (
    String(workflow.subject_kind || '') === String(item.subject_kind || '')
    && String(workflow.subject_granularity || '') === String(item.subject_granularity || '')
    && String(workflow.subject_id || '') === String(item.subject_id || '')
  )
}
