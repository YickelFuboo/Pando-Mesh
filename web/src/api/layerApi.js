const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || body.message || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export function listWorkflows() {
  return request('/workflows')
}

export function listRequirements(workspacePath) {
  const qs = new URLSearchParams({ workspace_path: workspacePath })
  return request(`/workflows/meta/requirements?${qs.toString()}`)
}

export function listFeatures(workspacePath) {
  const qs = new URLSearchParams({ workspace_path: workspacePath })
  return request(`/workflows/meta/features?${qs.toString()}`)
}

export function listArchitecturesTree(workspacePath) {
  const qs = new URLSearchParams({ workspace_path: workspacePath })
  return request(`/workflows/meta/architectures/tree?${qs.toString()}`)
}

export function getMetaWorkspaceFile(workspacePath, path) {
  const qs = new URLSearchParams({ workspace_path: workspacePath, path })
  return request(`/workflows/meta/workspace-file?${qs.toString()}`)
}

export function listRequirementsTree(workspacePath) {
  const qs = new URLSearchParams({ workspace_path: workspacePath })
  return request(`/workflows/meta/requirements/tree?${qs.toString()}`)
}

export function openRequirementSession(requirementId, payload) {
  return request(`/workflows/requirements/${encodeURIComponent(requirementId)}/session`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getWorkflow(id) {
  return request(`/workflows/${encodeURIComponent(id)}`)
}

export function createWorkflow(payload) {
  return request('/workflows', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateWorkflow(id, payload) {
  return request(`/workflows/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function updateTopology(id, graph) {
  return request(`/workflows/${encodeURIComponent(id)}/topology`, {
    method: 'PUT',
    body: JSON.stringify({ graph }),
  })
}

export function executeWorkflow(id, payload = {}) {
  return request(`/workflows/${encodeURIComponent(id)}/execute`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function abortWorkflow(id) {
  return request(`/workflows/${encodeURIComponent(id)}/abort`, { method: 'POST' })
}

export function getWorkflowMessages(id) {
  return request(`/workflows/${encodeURIComponent(id)}/messages`)
}

export function getNodeMessages(workflowId, nodeId) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/node-messages/${encodeURIComponent(nodeId)}`)
}

export function getRequirementDoc(workflowId) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/doc/requirement`)
}

export function getNodeDoc(workflowId, nodeId) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/nodes/${encodeURIComponent(nodeId)}/doc`)
}

export function getWorkspaceFile(workflowId, path) {
  const qs = new URLSearchParams({ path })
  return request(`/workflows/${encodeURIComponent(workflowId)}/workspace-file?${qs.toString()}`)
}

export async function getLlmStatus() {
  try {
    return await request('/workflows/meta/llm-status')
  } catch {
    const health = await request('/health')
    return health?.llm || { available: false }
  }
}

export function getLlmConfig() {
  return request('/workflows/meta/llm-config')
}

export function updateLlmConfig(payload) {
  return request('/workflows/meta/llm-config', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function generateGraph(id, payload = {}) {
  return request(`/workflows/${encodeURIComponent(id)}/generate-graph`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteWorkflow(id) {
  return request(`/workflows/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function gateApprove(id, payload = {}) {
  return request(`/workflows/${encodeURIComponent(id)}/gate/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function gateReject(id, payload = {}) {
  return request(`/workflows/${encodeURIComponent(id)}/gate/reject`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function expandApply(id) {
  return request(`/workflows/${encodeURIComponent(id)}/expand/apply`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function getNodeOutput(workflowId, nodeId) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/nodes/${encodeURIComponent(nodeId)}/output`)
}

export function reviseNode(workflowId, nodeId, payload) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/nodes/${encodeURIComponent(nodeId)}/revise`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listAgents() {
  return request('/agents')
}

export function getAgentKindDefaults(kind) {
  return request(`/agents/meta/kind-defaults/${encodeURIComponent(kind)}`)
}

export function getAgent(agentId) {
  return request(`/agents/${encodeURIComponent(agentId)}`)
}

export function registerAgent(payload) {
  return request('/agents', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateAgent(agentId, payload) {
  return request(`/agents/${encodeURIComponent(agentId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function unregisterAgent(agentId) {
  return request(`/agents/${encodeURIComponent(agentId)}`, { method: 'DELETE' })
}

export function listWorkflowTemplates() {
  return request('/workflows/templates')
}

export function getWorkflowTemplate(templateId) {
  return request(`/workflows/templates/${encodeURIComponent(templateId)}`)
}

export function createWorkflowTemplate(payload) {
  return request('/workflows/templates', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateWorkflowTemplate(templateId, payload) {
  return request(`/workflows/templates/${encodeURIComponent(templateId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteWorkflowTemplate(templateId) {
  return request(`/workflows/templates/${encodeURIComponent(templateId)}`, { method: 'DELETE' })
}

export function duplicateWorkflowTemplate(templateId, payload = {}) {
  return request(`/workflows/templates/${encodeURIComponent(templateId)}/duplicate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function saveWorkflowAsTemplate(workflowId, payload) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/save-as-template`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function initWorkflowFromTemplate(workflowId, templateId) {
  return request(`/workflows/${encodeURIComponent(workflowId)}/init-from-template`, {
    method: 'POST',
    body: JSON.stringify({ template_id: templateId }),
  }).catch(async (error) => {
    const msg = error?.message || ''
    if (msg !== 'Not Found') throw error
    return request(
      `/workflows/${encodeURIComponent(workflowId)}/apply-template/${encodeURIComponent(templateId)}`,
      { method: 'POST', body: JSON.stringify({}) },
    )
  })
}
