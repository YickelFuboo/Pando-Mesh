export const DEFAULT_CLI_HISTORY_CONFIG = {
  config_dir: '~/.claude',
}

export function extractSessionConfig(agent) {
  return agent?.session_config && typeof agent.session_config === 'object'
    ? agent.session_config
    : {}
}

export function extractHistoryConfig(agent) {
  const raw = agent?.history_config && typeof agent.history_config === 'object'
    ? agent.history_config
    : {}
  return normalizeHistoryConfig(raw)
}

export function normalizeHistoryConfig(raw) {
  const configDir = String(raw?.config_dir ?? '').trim()
  return {
    config_dir: configDir || DEFAULT_CLI_HISTORY_CONFIG.config_dir,
  }
}

export function historyConfigFromForm(form) {
  return normalizeHistoryConfig({ config_dir: form.history_config_dir })
}

export function applyHistoryFieldsToForm(form, historyConfig) {
  const normalized = normalizeHistoryConfig(historyConfig)
  form.history_config_dir = normalized.config_dir
  form.history_config_text = JSON.stringify(normalized, null, 2)
}
export function stripSessionFromExecutorTemplate(executorTemplate) {
  const kind = String(executorTemplate?.kind || '').toLowerCase()
  if (kind !== 'cli') {
    return executorTemplate || {}
  }
  const next = JSON.parse(JSON.stringify(executorTemplate || {}))
  if (next.cli && typeof next.cli === 'object' && 'session' in next.cli) {
    const cli = { ...next.cli }
    delete cli.session
    next.cli = cli
  }
  return next
}

export function mergeCliSessionIntoExecutor(executorTemplate, sessionConfig, historyConfig) {
  const kind = String(executorTemplate?.kind || '').toLowerCase()
  if (kind !== 'cli') {
    return executorTemplate
  }
  const next = JSON.parse(JSON.stringify(executorTemplate || {}))
  if (!next.cli) {
    next.cli = {}
  }
  const session = { ...(next.cli.session || {}), ...(sessionConfig || {}) }
  const history = normalizeHistoryConfig(historyConfig)
  session.history = history
  next.cli.session = session
  return next
}

export function buildAgentPayload(form, { mergeSession = true } = {}) {
  const sessionConfig = JSON.parse(form.session_config_text || '{}')
  const historyConfig = historyConfigFromForm(form)
  let executorTemplate = JSON.parse(form.executor_template_text || '{}')
  if (mergeSession) {
    executorTemplate = mergeCliSessionIntoExecutor(executorTemplate, sessionConfig, historyConfig)
  }
  return {
    name: String(form.name || '').trim(),
    kind: form.kind,
    description: String(form.description || '').trim(),
    executor_template: executorTemplate,
    session_config: sessionConfig,
    history_config: historyConfig,
    enabled: form.enabled !== false,
  }
}

export function fillAgentForm(form, agent) {
  form.agent_id = agent.agent_id || ''
  form.name = agent.name || ''
  form.kind = agent.kind || 'native'
  form.description = agent.description || ''
  const executor = agent.executor_template || {}
  form.executor_template_text = JSON.stringify(stripSessionFromExecutorTemplate(executor), null, 2)
  form.session_config_text = JSON.stringify(extractSessionConfig(agent), null, 2)
  applyHistoryFieldsToForm(form, extractHistoryConfig(agent))
  form.enabled = agent.enabled !== false
}

export function applyKindDefaultsToForm(form, defaults) {
  const executor = defaults.executor_template || {}
  form.executor_template_text = JSON.stringify(stripSessionFromExecutorTemplate(executor), null, 2)
  form.session_config_text = JSON.stringify(defaults.session_config || {}, null, 2)
  applyHistoryFieldsToForm(form, defaults.history_config || DEFAULT_CLI_HISTORY_CONFIG)
}
