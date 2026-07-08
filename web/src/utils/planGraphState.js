/** 从 SessionInfo.metadata 解析 Planning 编排快照 */

export function extractPlanGraphSnapshot(metadata) {
  const raw = metadata?.plan_graph
  if (!raw || typeof raw !== 'object') return null
  const graphSpec = raw.plan_graph
  if (!graphSpec || !Array.isArray(graphSpec.nodes) || !graphSpec.nodes.length) {
    return null
  }
  return {
    graphSpec,
    phase: raw.phase || 'idle',
    runningNodeIds: Array.isArray(raw.running_node_ids) ? raw.running_node_ids : [],
    nodeSessionIds: raw.node_session_id && typeof raw.node_session_id === 'object' ? raw.node_session_id : {},
    completedNodeIds: raw.node_outputs && typeof raw.node_outputs === 'object'
      ? Object.keys(raw.node_outputs)
      : [],
    nodeIterations: raw.node_iterations && typeof raw.node_iterations === 'object' ? raw.node_iterations : {},
    nodeOutputs: raw.node_outputs && typeof raw.node_outputs === 'object' ? raw.node_outputs : {},
    preNodeRejectInfos: raw.pre_node_reject_infos && typeof raw.pre_node_reject_infos === 'object'
      ? raw.pre_node_reject_infos
      : {},
    pendingGate: raw.pending_gate && typeof raw.pending_gate === 'object' ? raw.pending_gate : {},
    pendingExpand: raw.pending_expand && typeof raw.pending_expand === 'object' ? raw.pending_expand : {},
    userGoal: raw.user_goal || '',
  }
}

/** 图的 entry 起始节点 id */
export function resolveGraphEntryId(graphSpec) {
  if (!graphSpec) return ''
  const entry = String(graphSpec.entry || '').trim()
  if (entry) return entry
  return String(graphSpec.nodes?.[0]?.id || '').trim()
}

export function isGraphEntryNode(graphSpec, nodeId) {
  const key = String(nodeId || '').trim()
  if (!key) return false
  const entry = resolveGraphEntryId(graphSpec)
  return Boolean(entry) && key === entry
}

/** @returns {{ status: 'pending'|'running'|'done', label: string }} */
export function resolvePlanNodeStatus(nodeId, snapshot) {
  if (!nodeId || !snapshot) return { status: 'pending', label: '未启动' }
  if ((snapshot.runningNodeIds || []).includes(nodeId)) {
    return { status: 'running', label: '执行中' }
  }
  if ((snapshot.completedNodeIds || []).includes(nodeId)) {
    return { status: 'done', label: '已完成' }
  }
  return { status: 'pending', label: '未启动' }
}

export function resolveNodeSessionId(snapshot, nodeId) {
  if (!snapshot || !nodeId) return null
  return snapshot.nodeSessionIds?.[nodeId] || null
}

/** 节点累计执行次数（含首次） */
export function resolveNodeIterationCount(nodeId, nodeIterations) {
  const n = Number.parseInt(nodeIterations?.[nodeId], 10)
  return Number.isFinite(n) && n > 0 ? n : 0
}

/** 返工次数 = 执行次数 - 1 */
export function resolveNodeReworkCount(nodeId, nodeIterations) {
  const total = resolveNodeIterationCount(nodeId, nodeIterations)
  return total > 1 ? total - 1 : 0
}

export function resolveGraphNodeLabel(graphSpec, nodeId) {
  const node = graphSpec?.nodes?.find((n) => n.id === nodeId)
  return String(node?.label || nodeId || '').trim()
}

/** @returns executor kind 字符串 */
export function resolveGraphNodeExecutorKind(graphSpec, nodeId) {
  const node = graphSpec?.nodes?.find((n) => n.id === nodeId)
  if (!node) return 'cli'
  return String(node.executor?.kind || 'cli').trim().toLowerCase()
}

function normalizeNodeRole(raw) {
  return String(raw || 'execute').trim().toLowerCase() === 'check' ? 'check' : 'execute'
}

export const NODE_VISUAL_LABELS = {
  ai_execute: 'AI执行类',
  ai_check: 'AI检查类',
  human_gate: '人工卡点类',
  expand_gate: '扩展',
  fork_gate: '分支汇聚类',
}

/** @returns {'ai_execute'|'ai_check'|'human_gate'|'expand_gate'|'fork_gate'} */
export function resolveNodeVisualType(node) {
  if (!node) return 'ai_execute'
  const kind = String(node.executor?.kind || 'cli').trim().toLowerCase()
  if (kind === 'expand') return 'expand_gate'
  if (kind === 'fork') return 'fork_gate'
  if (kind === 'human') return 'human_gate'
  if (normalizeNodeRole(node.node_role) === 'check') return 'ai_check'
  return 'ai_execute'
}

export function isCliGraphNode(snapshot, nodeId) {
  if (!snapshot || !nodeId) return false
  const node = snapshot.graphSpec?.nodes?.find((n) => n.id === nodeId)
  if (!node) return false
  const kind = String(node.executor?.kind || '').trim().toLowerCase()
  if (kind !== 'cli') return false
  const cli = node.executor?.cli
  return cli != null && typeof cli === 'object'
}

/** 节点副标题：AI执行 / AI检查 / 人工卡点 */
export function resolveGraphNodeDisplayAgent(graphSpec, nodeId) {
  const node = findGraphNode(graphSpec, nodeId)
  if (!node) return ''
  const visual = resolveNodeVisualType(node)
  if (visual === 'human_gate') return '人工卡点'
  if (visual === 'ai_check') return 'AI检查'
  if (visual === 'expand_gate') return '扩展'
  if (visual === 'fork_gate') return '分支汇聚'
  return 'AI执行'
}

export function findGraphNode(graphSpec, nodeId) {
  if (!graphSpec || !nodeId) return null
  return graphSpec.nodes?.find((n) => n.id === nodeId) || null
}

/** 有编排图即可编辑拓扑（不因 phase / 节点执行状态限制） */
export function isPlanGraphTopologyEditable(snapshot) {
  return Boolean(snapshot?.graphSpec)
}

/** 驳回意见是否由指定源节点写入（与后端 reject_msg 格式一致） */
export function rejectInfoFromNode(rejectInfo, fromLabel) {
  const info = String(rejectInfo || '').trim()
  const label = String(fromLabel || '').trim()
  if (!info || !label) return false
  return info.includes(`步骤「${label}」`)
}

const REJECT_EDGE_IDLE = { label: '已驳回 0次', active: false, tooltip: '尚未触发驳回（0 次）' }

/**
 * 驳回边展示：按边判断，仅源节点已执行且驳回意见对应该边时才计数
 * @returns {{ label: string, active: boolean, tooltip: string }}
 */
export function resolveRejectEdgeDisplay(
  fromId,
  toId,
  condition,
  nodeIterations,
  preNodeRejectInfos,
  graphSpec,
  completedNodeIds,
) {
  if (condition !== 'reject') {
    return { label: '', active: false, tooltip: '' }
  }
  const fromCompleted = Array.isArray(completedNodeIds) && completedNodeIds.includes(fromId)
  if (!fromCompleted) {
    return { ...REJECT_EDGE_IDLE }
  }
  const fromLabel = resolveGraphNodeLabel(graphSpec, fromId)
  const rejectInfo = String(preNodeRejectInfos?.[toId] || '').trim()
  if (!rejectInfoFromNode(rejectInfo, fromLabel)) {
    return { ...REJECT_EDGE_IDLE }
  }
  const reworkCount = resolveNodeReworkCount(toId, nodeIterations)
  return {
    label: `已驳回 ${reworkCount}次`,
    active: reworkCount > 0,
    tooltip: rejectInfo,
  }
}

/** 节点 hover：标题 + 驳回意见 */
export function buildPlanNodeTooltip(fullLabel, nodeId, preNodeRejectInfos) {
  const title = String(fullLabel || nodeId || '').trim()
  const rejectInfo = String(preNodeRejectInfos?.[nodeId] || '').trim()
  if (!rejectInfo) return title
  return `${title}\n\n驳回意见：\n${rejectInfo}`
}

export const PLANNING_AGENT_TYPE = 'Planning'
