<template>
  <Teleport to="body">
    <div class="overlay" @mousedown.self="emit('close')">
    <div class="card" role="dialog" aria-labelledby="pn-add-title">
      <header class="header">
        <div class="header-text">
          <h2 id="pn-add-title" class="title">添加</h2>
          <p class="desc">从步骤 <strong>{{ fromNodeLabel }}</strong>（{{ fromNodeId }}）出发</p>
        </div>
        <button type="button" class="close-btn" aria-label="关闭" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </header>

      <aside class="placeholder-notice">
        <p class="placeholder-notice-line">
          <strong>Session 占位符</strong>（任务说明、文档路径等均可使用，执行时自动替换）：
          <code>{workspace}</code> 工作区路径；
          <code>{requirement_id}</code> 需求 ID
        </p>
        <p class="placeholder-notice-line">
          <strong>路径模式</strong>：通配 <code>{*}</code> 或正则 <code>{re:pattern}</code>，目录与文件名均可匹配。
        </p>
      </aside>

      <div class="tabs" role="tablist">
        <button
          type="button"
          class="tab"
          :class="{ active: tab === 'node' }"
          role="tab"
          :aria-selected="tab === 'node'"
          @click="tab = 'node'"
        >
          下游节点
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: tab === 'edge' }"
          role="tab"
          :aria-selected="tab === 'edge'"
          @click="tab = 'edge'"
        >
          出边
        </button>
      </div>

      <form class="form" @submit.prevent="handleSubmit">
        <div v-show="tab === 'node'" class="form-body">
          <div class="field">
            <label for="pa-node-id">节点 ID</label>
            <input id="pa-node-id" :value="draftNodeId" type="text" readonly class="readonly" />
          </div>
          <div class="field">
            <label for="pa-label">步骤名称</label>
            <input id="pa-label" v-model="nodeForm.label" type="text" placeholder="新步骤名称" />
          </div>
          <div class="field">
            <label for="pa-task">任务说明</label>
            <textarea id="pa-task" v-model="nodeForm.task" rows="2" placeholder="编排执行时注入该步骤的 task" />
          </div>
          <div class="field">
            <label for="pa-phase">Phase</label>
            <input id="pa-phase" v-model="nodeForm.phase" type="text" placeholder="如：设计 / 开发 / 测试" />
          </div>
          <div class="field">
            <label for="pa-role">节点类型</label>
            <select id="pa-role" v-model="nodeForm.nodeVisualType" @change="onNodeVisualTypeChange">
              <option value="execute">AI执行类</option>
              <option value="check">AI检查类</option>
              <option value="human">人工卡点类</option>
              <option value="expand">扩展类</option>
            </select>
          </div>
          <div v-if="nodeForm.nodeVisualType === 'human'" class="hint">
            人工卡点类需配置 pass / reject 出边：pass 继续下游，reject 返工上游。
          </div>
          <div v-if="nodeForm.nodeVisualType === 'human'" class="field">
            <label for="pa-human-auto">是否自动执行</label>
            <select id="pa-human-auto" v-model="nodeForm.humanAutoConfirm">
              <option :value="false">否</option>
              <option :value="true">是</option>
            </select>
            <p class="hint">选择「是」时等同默认人工确认通过并继续执行</p>
          </div>
          <template v-else-if="nodeForm.nodeVisualType === 'expand'">
            <div class="field">
              <label for="pa-expand-template">Lane 模板</label>
              <select
                id="pa-expand-template"
                v-model="nodeForm.expandDefaultLaneTemplateId"
                @change="onExpandTemplateChange"
              >
                <option value="">请选择模板</option>
                <option v-for="tpl in workflowTemplates" :key="tpl.template_id" :value="tpl.template_id">
                  {{ tpl.name }}（{{ tpl.template_id }}）
                </option>
              </select>
            </div>
            <div class="field">
              <label for="pa-expand-planner">扩展规划</label>
              <select id="pa-expand-planner" v-model="nodeForm.expandPlanner">
                <option value="source">上游产出 / 默认</option>
                <option value="native_llm">Session LLM 规划</option>
              </select>
            </div>
            <div class="field">
              <label for="pa-expand-merge">汇聚节点名称</label>
              <input id="pa-expand-merge" v-model="nodeForm.expandMergeLabel" type="text" placeholder="任务汇聚" />
            </div>
          </template>
          <template v-else>
          <div v-if="!agentOptions.length" class="hint">
            暂无已注册 Agent，请先在「Agent 注册」中配置。
          </div>
          <div v-else class="field">
            <label for="pa-registered-agent">选择已注册 Agent</label>
            <select
              id="pa-registered-agent"
              v-model="nodeForm.registeredAgentId"
              required
              @change="onRegisteredAgentChange"
            >
              <option value="" disabled>请选择 Agent</option>
              <option v-for="opt in agentOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}（{{ kindLabel(opt.kind) }}）
              </option>
            </select>
            <p class="hint">CLI 参数、结果字段、会话配置均取自 Agent 模板；本步骤只需填写「任务说明」。</p>
          </div>
          </template>
          <p class="hint">将在当前步骤与后继之间插入该节点。</p>
        </div>

        <div v-show="tab === 'edge'" class="form-body">
          <div class="field">
            <label for="pa-from">起点</label>
            <input id="pa-from" :value="fromNodeLabel ? `${fromNodeLabel}（${fromNodeId}）` : fromNodeId" type="text" readonly class="readonly" />
          </div>
          <div class="field">
            <label for="pa-to">终点</label>
            <select id="pa-to" v-model="edgeForm.to">
              <option v-for="id in otherNodeIds" :key="'t-' + id" :value="id">{{ nodeLabel(id) }}</option>
              <option :value="END_NODE">END（结束）</option>
            </select>
          </div>
          <div class="field">
            <label for="pa-cond">条件</label>
            <select id="pa-cond" v-model="edgeForm.condition">
              <option value="always">顺序 (always)</option>
              <option value="pass">通过 (pass)</option>
              <option value="reject">驳回返工 (reject)</option>
            </select>
          </div>
          <p class="hint">新增一条从当前步骤出发的连线，可连接已有步骤或 END。</p>
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <footer class="footer">
          <button type="button" class="btn secondary" :disabled="loading" @click="emit('close')">取消</button>
          <button type="submit" class="btn primary" :disabled="loading">
            {{ loading ? '提交中…' : (tab === 'node' ? '添加节点' : '添加出边') }}
          </button>
        </footer>
      </form>
    </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  END_NODE,
  applyRegisteredAgentToForm,
  createDefaultNode,
  editFormToNode,
  generateNodeId,
  nodeToEditForm,
  normalizeEdgeCondition,
  syncFormFromNodeVisualType,
  usesRegisteredAgent,
} from '../../utils/planGraphEdit.js'
import { resolveGraphNodeLabel } from '../../utils/planGraphState.js'
import { listWorkflowTemplates } from '../../api/layerApi.js'

const props = defineProps({
  fromNodeId: { type: String, required: true },
  fromNodeLabel: { type: String, default: '' },
  graphSpec: { type: Object, required: true },
  agentOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const KIND_LABELS = {
  native: '自研',
  codex_sdk: 'Codex SDK',
  claude_code_cli: 'Claude Code CLI',
  api: '第三方 API',
}

function kindLabel(kind) {
  return KIND_LABELS[kind] || kind
}

function onRegisteredAgentChange() {
  const opt = props.agentOptions.find((item) => item.value === nodeForm.value.registeredAgentId)
  if (!opt) return
  nodeForm.value = applyRegisteredAgentToForm(nodeForm.value, opt)
}

const emit = defineEmits(['close', 'submit-node', 'submit-edge'])

const tab = ref('node')
const draftNodeId = ref('')
const nodeForm = ref({})
const edgeForm = reactive({
  to: '',
  condition: 'always',
})
const errorMsg = ref('')
const workflowTemplates = ref([])

async function loadWorkflowTemplates() {
  try {
    workflowTemplates.value = await listWorkflowTemplates()
  } catch {
    workflowTemplates.value = []
  }
}

onMounted(() => {
  loadWorkflowTemplates()
})

function onExpandTemplateChange() {
  const tid = String(nodeForm.value.expandDefaultLaneTemplateId || '').trim()
  if (tid && !String(nodeForm.value.expandCatalogTemplatesText || '').trim()) {
    nodeForm.value.expandCatalogTemplatesText = tid
  }
}

const otherNodeIds = computed(() => (
  (props.graphSpec?.nodes || []).map((n) => n.id).filter((id) => id && id !== props.fromNodeId)
))

function nodeLabel(nodeId) {
  return resolveGraphNodeLabel(props.graphSpec, nodeId) || nodeId
}

function defaultEdgeTo() {
  return otherNodeIds.value[0] || END_NODE
}

function resetForms() {
  draftNodeId.value = generateNodeId(props.graphSpec)
  nodeForm.value = nodeToEditForm(createDefaultNode(draftNodeId.value))
  const defaultAgent = props.agentOptions.find((opt) => opt.value === 'claude_code')
    || props.agentOptions.find((opt) => String(opt.executorTemplate?.kind || '').toLowerCase() === 'cli')
    || props.agentOptions[0]
  if (defaultAgent && !nodeForm.value.registeredAgentId) {
    nodeForm.value = applyRegisteredAgentToForm(nodeForm.value, defaultAgent)
  }
  edgeForm.to = defaultEdgeTo()
  edgeForm.condition = 'always'
  tab.value = 'node'
  errorMsg.value = ''
}

watch(
  () => [props.fromNodeId, props.graphSpec],
  () => resetForms(),
  { immediate: true },
)

function onNodeVisualTypeChange() {
  nodeForm.value = syncFormFromNodeVisualType(nodeForm.value)
  if (nodeForm.value.nodeVisualType === 'expand' || nodeForm.value.nodeVisualType === 'fork') return
  if (nodeForm.value.nodeVisualType !== 'human' && !nodeForm.value.registeredAgentId && props.agentOptions.length) {
    const defaultAgent = props.agentOptions.find((opt) => opt.value === 'claude_code')
      || props.agentOptions.find((opt) => String(opt.executorTemplate?.kind || '').toLowerCase() === 'cli')
      || props.agentOptions[0]
    if (defaultAgent) {
      nodeForm.value = applyRegisteredAgentToForm(nodeForm.value, defaultAgent)
    }
  }
}

function validateNodeTab() {
  if (!String(nodeForm.value.label || '').trim()) {
    errorMsg.value = '请填写步骤名称'
    return false
  }
  if (nodeForm.value.nodeVisualType === 'human') {
    return true
  }
  if (nodeForm.value.nodeVisualType === 'expand') {
    if (!String(nodeForm.value.expandDefaultLaneTemplateId || '').trim()) {
      errorMsg.value = '请选择 Lane 模板'
      return false
    }
    return true
  }
  if (props.agentOptions.length && !usesRegisteredAgent(nodeForm.value)) {
    errorMsg.value = '请选择已注册 Agent'
    return false
  }
  return true
}

function validateEdgeTab() {
  if (!edgeForm.to) {
    errorMsg.value = '请选择终点'
    return false
  }
  if (edgeForm.to === props.fromNodeId) {
    errorMsg.value = '起点与终点不能相同'
    return false
  }
  const dup = (props.graphSpec?.edges || []).some(
    (e) => e.from === props.fromNodeId
      && e.to === edgeForm.to
      && normalizeEdgeCondition(e.condition) === edgeForm.condition,
  )
  if (dup) {
    errorMsg.value = '相同条件的连线已存在'
    return false
  }
  return true
}

function handleSubmit() {
  errorMsg.value = ''
  if (tab.value === 'node') {
    if (!validateNodeTab()) return
    emit('submit-node', editFormToNode(draftNodeId.value, nodeForm.value, { id: draftNodeId.value }))
    return
  }
  if (!validateEdgeTab()) return
  emit('submit-edge', {
    from: props.fromNodeId,
    to: edgeForm.to,
    condition: edgeForm.condition,
  })
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.35);
}
.card {
  width: min(480px, 100%);
  max-height: min(90vh, 640px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #202124;
}
.desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #5f6368;
}
.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #5f6368;
  padding: 4px;
  border-radius: 6px;
}
.close-btn:hover {
  background: #f1f3f4;
}
.tabs {
  display: flex;
  gap: 0;
  padding: 0 18px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.tab {
  padding: 10px 16px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #5f6368;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab.active {
  color: #1a73e8;
  border-bottom-color: #1a73e8;
}
.form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}
.form-body {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}
.field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #3c4043;
  margin-bottom: 4px;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 13px;
}
.field input.readonly {
  background: #f8f9fa;
  color: #5f6368;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.seg-group {
  display: flex;
  gap: 8px;
}
.seg-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.seg-item.active {
  border-color: #1a73e8;
  background: #e8f0fe;
  color: #1a73e8;
}
.seg-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.hint {
  margin: 0;
  font-size: 11px;
  color: #80868b;
  line-height: 1.4;
}
.placeholder-notice {
  flex-shrink: 0;
  margin: 0;
  padding: 10px 18px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  background: #f8f9fa;
}
.placeholder-notice-line {
  margin: 0;
  font-size: 12px;
  color: #5f6368;
  line-height: 1.55;
}
.placeholder-notice-line code {
  font-family: ui-monospace, 'Cascadia Code', 'SF Mono', Consolas, monospace;
  font-size: 11px;
  color: #1a73e8;
  background: #fff;
  border: 1px solid #d2e3fc;
  padding: 0 5px;
  border-radius: 4px;
}
.error-msg {
  margin: 0 18px;
  font-size: 12px;
  color: #c5221f;
}
.footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn.secondary {
  background: #fff;
  border-color: #dadce0;
  color: #3c4043;
}
.btn.primary {
  background: #1a73e8;
  color: #fff;
}
</style>
