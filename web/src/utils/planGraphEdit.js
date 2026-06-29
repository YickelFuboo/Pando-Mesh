import { resolveGraphNodeExecutorKind } from './planGraphState.js'

export const START_NODE = 'START'
export const END_NODE = 'END'
export const EDGE_CONDITIONS = ['always', 'pass', 'reject']
export const NODE_ROLES = ['execute', 'check']
export const NODE_ROLE_LABELS = {
  execute: '执行类',
  check: '检查类',
}
export const NODE_VISUAL_TYPES = ['execute', 'check', 'human']
export const NODE_VISUAL_TYPE_LABELS = {
  execute: 'AI执行类',
  check: 'AI检查类',
  human: '人工卡点类',
}

export function normalizeNodeVisualType(raw) {
  const key = String(raw || '').trim().toLowerCase()
  if (key === 'human' || key === 'human_gate') return 'human'
  if (key === 'check') return 'check'
  return 'execute'
}

export function nodeVisualTypeFromNode(node) {
  const kind = String(node?.executor?.kind || '').trim().toLowerCase()
  if (kind === 'human') return 'human'
  if (normalizeNodeRole(node?.node_role) === 'check') return 'check'
  return 'execute'
}

export function syncFormFromNodeVisualType(form) {
  const next = { ...form }
  const visualType = normalizeNodeVisualType(next.nodeVisualType)
  next.nodeVisualType = visualType
  if (visualType === 'human') {
    next.nodeRole = 'execute'
    next.executorKind = 'human'
    next.registeredAgentId = ''
  } else {
    next.nodeRole = visualType === 'check' ? 'check' : 'execute'
    if (next.executorKind === 'human') {
      next.executorKind = 'cli'
    }
  }
  return next
}

export function usesRegisteredAgent(form) {
  return Boolean(String(form?.registeredAgentId || '').trim())
}

export function buildRegisteredAgentExecutor(form) {
  const agentId = String(form.registeredAgentId || '').trim()
  const kind = String(form.executorKind || 'cli').trim().toLowerCase()
  if (kind === 'react') {
    return {
      kind: 'react',
      registered_agent_id: agentId,
      ...(String(form.agentType || '').trim() ? { agent_type: String(form.agentType).trim() } : {}),
    }
  }
  if (kind === 'expand') {
    return {
      kind: 'expand',
      registered_agent_id: agentId,
      expand: {
        ...(String(form.expandSourceNodeId || '').trim()
          ? { source_node_id: String(form.expandSourceNodeId).trim() }
          : {}),
        merge_label: String(form.expandMergeLabel || '任务汇聚').trim() || '任务汇聚',
      },
    }
  }
  return {
    kind: 'cli',
    registered_agent_id: agentId,
  }
}

export function normalizeNodeRole(raw) {
  return String(raw || 'execute').trim().toLowerCase() === 'check' ? 'check' : 'execute'
}

export function formatDocPathsText(refs) {
  return (refs || [])
    .map((item) => {
      if (typeof item === 'string') return String(item || '').trim()
      return String(item?.path || '').trim()
    })
    .filter(Boolean)
    .join('\n')
}

export function readNodeInputDocPaths(node) {
  if (!Array.isArray(node?.input_doc_paths)) return []
  return node.input_doc_paths.map((p) => String(p || '').trim()).filter(Boolean)
}

export function readNodeOutputDocPaths(node) {
  if (!Array.isArray(node?.output_doc_paths)) return []
  return node.output_doc_paths.map((p) => String(p || '').trim()).filter(Boolean)
}

export function parseWorkspaceRefsText(text) {
  const refs = []
  for (const line of String(text || '').split(/\r?\n/)) {
    const raw = String(line || '').trim()
    if (!raw || raw.startsWith('#')) continue
    const sep = raw.indexOf('|')
    if (sep >= 0) {
      refs.push({
        label: raw.slice(0, sep).trim(),
        path: raw.slice(sep + 1).trim(),
      })
    } else {
      refs.push({ path: raw })
    }
  }
  return refs.filter((item) => String(item.path || '').trim())
}

export function formatWorkspaceRefsText(refs) {
  return (refs || [])
    .map((item) => {
      const path = String(item?.path || '').trim()
      if (!path) return ''
      const label = String(item?.label || '').trim()
      return label ? `${label}|${path}` : path
    })
    .filter(Boolean)
    .join('\n')
}

export const DEFAULT_CLI_CONFIG = {
  commands: [
    {
      command: 'claude',
      args: ['-p', '--output-format', 'json', '--dangerously-skip-permissions', '--disallowedTools', 'AskUserQuestion'],
    },
  ],
  input: 'arg',
  cwd: '{workspace}',
  timeout_sec: 3600,
  output_mode: 'json',
  result_json_key: 'result',
  session: {
    enabled: true,
    resume_args: ['--resume', '{cli_session_id}'],
    read_session_id_from_json: true,
    session_id_json_key: 'session_id',
    history: {
      config_dir: '~/.claude',
    },
  },
}

export function cloneGraphSpec(graphSpec) {
  return JSON.parse(JSON.stringify(graphSpec || { nodes: [], edges: [], entry: '' }))
}

export function replaceGraphNode(graphSpec, nodeId, nextNode) {
  const spec = cloneGraphSpec(graphSpec)
  const idx = (spec.nodes || []).findIndex((n) => n.id === nodeId)
  if (idx < 0) return spec
  spec.nodes[idx] = { ...nextNode, id: nodeId }
  return spec
}

/** 合并拓扑到 session metadata（保留 phase、执行记录等） */
export function mergePlanGraphTopology(metadata, graphSpec) {
  const base = metadata && typeof metadata === 'object' ? { ...metadata } : {}
  const planRaw = base.plan_graph && typeof base.plan_graph === 'object'
    ? { ...base.plan_graph }
    : {}
  planRaw.plan_graph = cloneGraphSpec(graphSpec)
  base.plan_graph = planRaw
  return base
}

export function nodeToEditForm(node) {
  const kind = String(node?.executor?.kind || 'cli').trim().toLowerCase()
  const expand = node?.executor?.expand && typeof node.executor.expand === 'object'
    ? node.executor.expand
    : {}
  const cli = node?.executor?.cli && typeof node.executor.cli === 'object'
    ? node.executor.cli
    : { ...DEFAULT_CLI_CONFIG }
  const firstStep = Array.isArray(cli.commands) && cli.commands.length
    ? cli.commands.find((s) => s && (s.command || s.shell)) || cli.commands[0]
    : DEFAULT_CLI_CONFIG.commands[0]
  const cliMode = String(cli.shell || '').trim() ? 'shell' : 'commands'
  return {
    label: String(node?.label || node?.id || '').trim(),
    task: String(node?.task || '').trim(),
    phase: String(node?.phase || '').trim(),
    nodeVisualType: nodeVisualTypeFromNode(node),
    nodeRole: normalizeNodeRole(node?.node_role),
    inputDocPathsText: formatDocPathsText(readNodeInputDocPaths(node)),
    outputDocPathsText: formatDocPathsText(readNodeOutputDocPaths(node)),
    registeredAgentId: String(node?.executor?.registered_agent_id || '').trim(),
    executorKind: kind,
    agentType: String(node?.executor?.agent_type || node?.agent_type || '').trim(),
    expandSourceNodeId: String(expand.source_node_id || '').trim(),
    expandMergeLabel: String(expand.merge_label || '任务汇聚').trim(),
    cliMode,
    cliCommand: String(firstStep?.command || 'claude').trim(),
    cliArgsText: formatCliArgsText(firstStep?.args),
    cliShell: String(cli.shell || '').trim(),
    cliCwd: String(cli.cwd || '{workspace}').trim(),
    cliInput: String(cli.input || 'arg').trim().toLowerCase(),
    cliTimeoutSec: Number.parseInt(cli.timeout_sec, 10) || 3600,
    cliOutputMode: String(cli.output_mode || 'json').trim().toLowerCase(),
    cliResultKey: String(cli.result_json_key || 'result').trim(),
    cliSessionEnabled: Boolean(cli.session?.enabled),
    cliHistoryConfigDir: String(cli.session?.history?.config_dir || '').trim(),
  }
}

export function editFormToNode(nodeId, form, originalNode = {}) {
  const label = String(form.label || originalNode.label || nodeId).trim()
  const task = String(form.task ?? originalNode.task ?? '').trim()
  const maxIterations = Number.parseInt(originalNode.max_iterations, 10) || 3
  const payload = {
    id: nodeId,
    label,
    task,
    max_iterations: maxIterations,
  }
  if (String(form.phase || '').trim()) {
    payload.phase = String(form.phase).trim()
  }
  const visualType = normalizeNodeVisualType(form.nodeVisualType)
  if (visualType === 'human') {
    payload.node_role = 'execute'
    payload.executor = { kind: 'human' }
    return payload
  }
  payload.node_role = visualType === 'check' ? 'check' : 'execute'
  const inputPaths = parseWorkspaceRefsText(form.inputDocPathsText)
    .map((item) => String(item.path || '').trim())
    .filter(Boolean)
  const outputPaths = parseWorkspaceRefsText(form.outputDocPathsText)
    .map((item) => String(item.path || '').trim())
    .filter(Boolean)
  if (inputPaths.length) {
    payload.input_doc_paths = inputPaths
  }
  if (outputPaths.length) {
    payload.output_doc_paths = outputPaths
  }
  if (form.executorKind === 'cli') {
    if (usesRegisteredAgent(form)) {
      payload.executor = buildRegisteredAgentExecutor(form)
    } else {
      const cli = buildCliConfigFromForm(form)
      payload.executor = { kind: 'cli', cli }
    }
  } else if (form.executorKind === 'human') {
    payload.executor = { kind: 'human' }
  } else if (form.executorKind === 'expand') {
    payload.executor = usesRegisteredAgent(form)
      ? buildRegisteredAgentExecutor(form)
      : {
          kind: 'expand',
          expand: {
            ...(String(form.expandSourceNodeId || '').trim()
              ? { source_node_id: String(form.expandSourceNodeId).trim() }
              : {}),
            merge_label: String(form.expandMergeLabel || '任务汇聚').trim() || '任务汇聚',
          },
        }
  } else {
    payload.executor = usesRegisteredAgent(form)
      ? buildRegisteredAgentExecutor(form)
      : {
          kind: 'react',
          agent_type: String(form.agentType || '').trim(),
        }
  }
  return payload
}

function buildCliConfigFromForm(form) {
  const defaultSession = DEFAULT_CLI_CONFIG.session || {}
  const defaultHistory = defaultSession.history || { config_dir: '~/.claude' }
  const cli = {
    input: form.cliInput === 'stdin' ? 'stdin' : 'arg',
    cwd: String(form.cliCwd || '{workspace}').trim() || '{workspace}',
    timeout_sec: Math.max(1, Number.parseInt(form.cliTimeoutSec, 10) || 3600),
    output_mode: form.cliOutputMode === 'stdout' ? 'stdout' : 'json',
    result_json_key: String(DEFAULT_CLI_CONFIG.result_json_key || 'result').trim() || 'result',
    session: {
      enabled: Boolean(defaultSession.enabled),
      resume_args: Array.isArray(defaultSession.resume_args)
        ? [...defaultSession.resume_args]
        : ['--resume', '{cli_session_id}'],
      read_session_id_from_json: defaultSession.read_session_id_from_json !== false,
      session_id_json_key: String(defaultSession.session_id_json_key || 'session_id').trim() || 'session_id',
      history: {
        config_dir: String(defaultHistory.config_dir || '~/.claude').trim() || '~/.claude',
      },
    },
  }
  if (form.cliMode === 'shell') {
    cli.shell = String(form.cliShell || '').trim()
    if (!cli.shell) {
      cli.shell = 'cd {workspace} && claude -p --output-format json {session_args}'
    }
  } else {
    const command = String(form.cliCommand || 'claude').trim() || 'claude'
    const args = parseCliArgsText(form.cliArgsText)
    cli.commands = [{ command, args }]
  }
  return cli
}

export function formatCliArgsText(args) {
  if (!Array.isArray(args)) return DEFAULT_CLI_CONFIG.commands[0].args.join('\n')
  return args.map((x) => String(x)).join('\n')
}

export function parseCliArgsText(text) {
  return String(text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

export function normalizeEdgeCondition(condition) {
  const c = String(condition || 'always').trim().toLowerCase()
  return EDGE_CONDITIONS.includes(c) ? c : 'always'
}

export function edgeEquals(a, b) {
  return a.from === b.from
    && a.to === b.to
    && normalizeEdgeCondition(a.condition) === normalizeEdgeCondition(b.condition)
}

export function listGraphNodeIds(graphSpec) {
  return (graphSpec?.nodes || []).map((n) => n.id).filter(Boolean)
}

export function listEditableEdges(graphSpec) {
  return (graphSpec?.edges || []).filter(
    (e) => e && e.from !== START_NODE && e.to !== END_NODE,
  )
}

export function generateNodeId(graphSpec) {
  const ids = new Set(listGraphNodeIds(graphSpec))
  let i = 1
  while (ids.has(`n${i}`)) i += 1
  return `n${i}`
}

export function createDefaultNode(nodeId, label) {
  return {
    id: nodeId,
    label: label || `新步骤 ${nodeId}`,
    task: '',
    max_iterations: 3,
    executor: { kind: 'cli', cli: { ...DEFAULT_CLI_CONFIG } },
  }
}

export function agentsToOptions(agents) {
  return (agents || []).map((agent) => ({
    value: agent.agent_id,
    label: agent.name || agent.agent_id,
    kind: agent.kind,
    description: agent.description || '',
    builtin: Boolean(agent.builtin),
    executorTemplate: agent.executor_template || {},
  }))
}

export function applyRegisteredAgentToForm(form, agent) {
  if (!agent?.executorTemplate) return { ...form }
  const next = { ...form }
  const executor = agent.executorTemplate
  const kind = String(executor.kind || 'cli').trim().toLowerCase()
  next.registeredAgentId = agent.value
  next.executorKind = kind
  if (kind === 'react') {
    next.agentType = String(executor.agent_type || '').trim()
    return next
  }
  if (kind === 'human') {
    next.nodeVisualType = 'human'
    next.nodeRole = 'execute'
    return next
  }
  if (next.nodeVisualType === 'human') {
    next.nodeVisualType = normalizeNodeRole(next.nodeRole) === 'check' ? 'check' : 'execute'
  }
  if (kind === 'expand') {
    const expand = executor.expand && typeof executor.expand === 'object' ? executor.expand : {}
    next.expandSourceNodeId = String(expand.source_node_id || '').trim()
    next.expandMergeLabel = String(expand.merge_label || '任务汇聚').trim()
    return next
  }
  const cli = executor.cli && typeof executor.cli === 'object' ? executor.cli : DEFAULT_CLI_CONFIG
  const firstStep = Array.isArray(cli.commands) && cli.commands.length
    ? cli.commands.find((s) => s && (s.command || s.shell)) || cli.commands[0]
    : DEFAULT_CLI_CONFIG.commands[0]
  next.cliMode = String(cli.shell || '').trim() ? 'shell' : 'commands'
  next.cliCommand = String(firstStep?.command || 'claude').trim()
  next.cliArgsText = formatCliArgsText(firstStep?.args)
  next.cliShell = String(cli.shell || '').trim()
  next.cliCwd = String(cli.cwd || '{workspace}').trim()
  next.cliInput = String(cli.input || 'arg').trim().toLowerCase()
  next.cliTimeoutSec = Number.parseInt(cli.timeout_sec, 10) || 3600
  next.cliOutputMode = String(cli.output_mode || 'json').trim().toLowerCase()
  next.cliResultKey = String(cli.result_json_key || 'result').trim()
  next.cliSessionEnabled = Boolean(cli.session?.enabled)
  next.cliHistoryConfigDir = String(cli.session?.history?.config_dir || '').trim()
  return next
}

function ensureBoundaryEdges(spec) {
  const nodeIds = new Set(listGraphNodeIds(spec))
  if (!spec.entry || !nodeIds.has(spec.entry)) {
    spec.entry = spec.nodes[0]?.id || ''
  }
  if (spec.entry) {
    spec.edges = (spec.edges || []).filter((e) => !(e.from === START_NODE))
    spec.edges.unshift({ from: START_NODE, to: spec.entry, condition: 'always' })
  }
  const hasEnd = (spec.edges || []).some((e) => e.to === END_NODE)
  if (!hasEnd && spec.nodes.length) {
    const outToEnd = new Set(
      (spec.edges || []).filter((e) => e.to === END_NODE).map((e) => e.from),
    )
    const leaf = [...nodeIds].find((id) => !(spec.edges || []).some((e) => e.from === id))
      || spec.nodes[spec.nodes.length - 1]?.id
    if (leaf && !outToEnd.has(leaf)) {
      spec.edges.push({ from: leaf, to: END_NODE, condition: 'always' })
    }
  }
}

export function validateGraphSpec(graphSpec) {
  const errors = []
  if (!graphSpec?.nodes?.length) {
    errors.push('至少需要一个节点')
    return errors
  }
  const nodeIds = new Set(listGraphNodeIds(graphSpec))
  if (!graphSpec.entry || !nodeIds.has(graphSpec.entry)) {
    errors.push('入口节点无效')
  }
  if (!(graphSpec.edges || []).some((e) => e.from === START_NODE && e.to === graphSpec.entry)) {
    errors.push('缺少 START 到入口节点的连线')
  }
  if (!(graphSpec.edges || []).some((e) => e.to === END_NODE)) {
    errors.push('缺少指向 END 的连线')
  }
  for (const e of graphSpec.edges || []) {
    if (e.from !== START_NODE && !nodeIds.has(e.from)) {
      errors.push(`边起点 ${e.from} 不存在`)
    }
    if (e.to !== END_NODE && !nodeIds.has(e.to)) {
      errors.push(`边终点 ${e.to} 不存在`)
    }
  }
  return errors
}

export function updateGraphEdge(graphSpec, oldEdge, newEdge) {
  const spec = cloneGraphSpec(graphSpec)
  const idx = (spec.edges || []).findIndex((e) => edgeEquals(e, oldEdge))
  if (idx < 0) return spec
  spec.edges[idx] = {
    from: newEdge.from,
    to: newEdge.to,
    condition: normalizeEdgeCondition(newEdge.condition),
  }
  if (newEdge.from === START_NODE && nodeIdsInclude(spec, newEdge.to)) {
    spec.entry = newEdge.to
  }
  ensureBoundaryEdges(spec)
  return spec
}

function nodeIdsInclude(spec, nodeId) {
  return listGraphNodeIds(spec).includes(nodeId)
}

export function removeGraphEdge(graphSpec, edge) {
  const spec = cloneGraphSpec(graphSpec)
  spec.edges = (spec.edges || []).filter((e) => !edgeEquals(e, edge))
  return spec
}

export function addGraphEdge(graphSpec, from, to, condition = 'always') {
  const spec = cloneGraphSpec(graphSpec)
  const cond = normalizeEdgeCondition(condition)
  const exists = (spec.edges || []).some(
    (e) => e.from === from && e.to === to && normalizeEdgeCondition(e.condition) === cond,
  )
  if (!exists) {
    spec.edges.push({ from, to, condition: cond })
  }
  if (from === START_NODE && nodeIdsInclude(spec, to)) {
    spec.entry = to
  }
  return spec
}

/** 在前向节点后插入后继节点（拆原 always / pass 出边）；可选传入完整节点配置 */
export function addSuccessorNode(graphSpec, fromNodeId, nextNode = null) {
  const spec = cloneGraphSpec(graphSpec)
  const newId = nextNode?.id || generateNodeId(spec)
  const newNode = nextNode
    ? { ...nextNode, id: newId }
    : createDefaultNode(newId)
  spec.nodes.push(newNode)
  const outEdges = (spec.edges || []).filter((e) => e.from === fromNodeId)
  const targetEdge = outEdges.find((e) => normalizeEdgeCondition(e.condition) === 'always')
    || outEdges.find((e) => normalizeEdgeCondition(e.condition) === 'pass')
  if (targetEdge) {
    const oldTo = targetEdge.to
    const cond = normalizeEdgeCondition(targetEdge.condition)
    targetEdge.to = newId
    spec.edges.push({ from: newId, to: oldTo, condition: cond })
  } else {
    spec.edges.push({ from: fromNodeId, to: newId, condition: 'always' })
    const endEdge = outEdges.find((e) => e.to === END_NODE)
    if (endEdge) {
      endEdge.from = newId
    } else {
      spec.edges.push({ from: newId, to: END_NODE, condition: 'always' })
    }
  }
  ensureBoundaryEdges(spec)
  return { spec, newNodeId: newId }
}

export function removeGraphNode(graphSpec, nodeId) {
  const spec = cloneGraphSpec(graphSpec)
  if (!listGraphNodeIds(spec).includes(nodeId)) return spec
  const inEdges = (spec.edges || []).filter((e) => e.to === nodeId)
  const outEdges = (spec.edges || []).filter((e) => e.from === nodeId)
  spec.edges = (spec.edges || []).filter((e) => e.from !== nodeId && e.to !== nodeId)
  spec.nodes = (spec.nodes || []).filter((n) => n.id !== nodeId)
  for (const inE of inEdges) {
    for (const outE of outEdges) {
      const cond = normalizeEdgeCondition(inE.condition)
      const outCond = normalizeEdgeCondition(outE.condition)
      if (cond !== outCond) continue
      const dup = spec.edges.some(
        (e) => e.from === inE.from && e.to === outE.to && normalizeEdgeCondition(e.condition) === cond,
      )
      if (!dup) {
        spec.edges.push({ from: inE.from, to: outE.to, condition: cond })
      }
    }
  }
  if (spec.entry === nodeId) {
    const startEdge = spec.edges.find((e) => e.from === START_NODE)
    spec.entry = startEdge?.to && nodeIdsInclude(spec, startEdge.to) ? startEdge.to : (spec.nodes[0]?.id || '')
  }
  ensureBoundaryEdges(spec)
  return spec
}

export function purgeNodeFromPlanMetadata(planGraphRaw, nodeId) {
  const plan = planGraphRaw && typeof planGraphRaw === 'object' ? { ...planGraphRaw } : {}
  for (const key of ['node_outputs', 'node_iterations', 'node_session_id', 'pre_node_reject_infos']) {
    if (plan[key] && typeof plan[key] === 'object' && nodeId in plan[key]) {
      const next = { ...plan[key] }
      delete next[nodeId]
      plan[key] = next
    }
  }
  return plan
}

export function listNodeRelatedEdges(graphSpec, nodeId) {
  if (!nodeId || !graphSpec?.edges) return []
  return graphSpec.edges.filter((e) => e.from === nodeId || e.to === nodeId)
}

export function canRemoveGraphNode(graphSpec, nodeId) {
  if (!(graphSpec?.nodes || []).some((n) => n.id === nodeId)) {
    return { ok: false, reason: '节点不存在' }
  }
  if ((graphSpec.nodes || []).length <= 1) {
    return { ok: false, reason: '至少保留一个步骤节点' }
  }
  const relatedEdges = listNodeRelatedEdges(graphSpec, nodeId)
  return { ok: true, relatedEdgeCount: relatedEdges.length, relatedEdges }
}

export function mergePlanGraphTopologyWithCleanup(metadata, graphSpec, removedNodeIds = []) {
  let base = mergePlanGraphTopology(metadata, graphSpec)
  if (removedNodeIds.length && base.plan_graph) {
    for (const nid of removedNodeIds) {
      base.plan_graph = purgeNodeFromPlanMetadata(base.plan_graph, nid)
    }
  }
  return base
}
