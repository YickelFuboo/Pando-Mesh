import { findGraphNode } from './planGraphState.js'

export function buildLocalNodeDoc(graphSpec, nodeId, nodeOutput = '') {
  const node = findGraphNode(graphSpec, nodeId)
  if (!node) return null
  const lines = [
    `# ${node.label || node.id}`,
    '',
    `- **节点 ID**：\`${node.id}\``,
  ]
  if (node.phase) {
    lines.push('', `- **Phase**：${node.phase}`)
  }
  if (node.task) {
    lines.push('', '## 任务说明', '', String(node.task).trim())
  }
  const output = String(nodeOutput || '').trim()
  if (output) {
    lines.push('', '## 执行产出', '', '```', output, '```')
  }
  lines.push(
    '',
    '## 文档约定',
    '',
    '可在节点配置中指定输入/输出文档路径，或在需求目录下放置：',
    '',
    `- \`${node.id}.md\``,
    `- \`nodes/${node.id}.md\``,
    `- \`docs/${node.id}.md\``,
    '',
    '_（本地预览：服务端文档接口暂不可用，已根据拓扑生成占位说明）_',
  )
  return {
    node_id: node.id,
    label: node.label || node.id,
    content: lines.join('\n'),
    source_path: '',
    generated: true,
    workspace_refs: [],
  }
}

export function buildLocalRequirementDocHint(requirementId) {
  return {
    node_id: '',
    label: '需求说明',
    content: [
      '# 需求说明',
      '',
      requirementId
        ? `当前需求 \`${requirementId}\` 目录下未找到 README.md / requirement.md。`
        : '未绑定需求 ID。',
      '',
      '请在 `{workspace}/requirements/{需求ID}/` 下添加 `README.md` 作为需求说明。',
      '',
      '_（本地预览：服务端文档接口暂不可用）_',
    ].join('\n'),
    source_path: '',
    generated: true,
    workspace_refs: [],
  }
}

export function formatDocLoadError(message) {
  const text = String(message || '').trim()
  if (!text || text === 'Not Found') {
    return '文档接口不可用或未找到内容，已尝试本地预览'
  }
  if (text === 'Workflow not found') return 'Session 不存在或已删除'
  if (text === 'Planning graph not found') return '尚未配置编排拓扑'
  if (text.startsWith('Node not found:')) return '节点不存在'
  if (text === '未找到需求说明 Markdown') return '需求目录下暂无 README.md'
  return text
}
