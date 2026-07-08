<template>
  <Teleport to="body">
    <div class="overlay" @mousedown.self="emit('close')">
    <div class="card" role="dialog" aria-labelledby="pn-edit-title">
      <header class="header">
        <div class="header-text">
          <h2 id="pn-edit-title" class="title">编辑节点</h2>
          <code class="node-id">{{ nodeId }}</code>
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
          <strong>路径模式</strong>：支持通配 <code>{*}</code> 与正则 <code>{re:...}</code>，运行时按实际文件展开。
        </p>
      </aside>

      <form class="form" @submit.prevent="handleSubmit">
        <div class="form-body">
          <section class="section">
            <h3 class="section-title">基本信息</h3>
            <div class="field">
              <label for="pn-label">步骤名称</label>
              <input id="pn-label" v-model="form.label" type="text" placeholder="节点在编排图中的显示名称" />
            </div>
            <div class="field">
              <label for="pn-task">任务说明</label>
              <textarea id="pn-task" v-model="form.task" rows="2" placeholder="编排执行时注入该步骤的 task" />
            </div>
            <div class="field">
              <label for="pn-phase">Phase <span class="label-hint">相同 Phase 的节点在拓扑图中虚框分组</span></label>
              <input id="pn-phase" v-model="form.phase" type="text" placeholder="如：设计 / 开发 / 测试" />
            </div>
            <div class="field">
              <label for="pn-role">节点类型</label>
              <select id="pn-role" v-model="form.nodeVisualType" @change="onNodeVisualTypeChange">
                <option value="execute">AI执行类</option>
                <option value="check">AI检查类</option>
                <option value="human">人工卡点类</option>
                <option value="expand">扩展类</option>
                <option value="fork">分支汇聚类</option>
              </select>
              <p v-if="form.nodeVisualType === 'human'" class="hint-text">
                人工验收节点，需配置 pass / reject 出边：pass 继续下游，reject 返工上游。
              </p>
              <p v-else-if="form.nodeVisualType === 'check'" class="hint-text">
                AI检查类由 Judge 或 LLM 审查上游产出。
              </p>
              <p v-else-if="form.nodeVisualType === 'expand'" class="hint-text">
                扩展类按 Lane 模板并行展开子工作流；规划由 LLM 或上游产出 JSON 完成。
              </p>
              <p v-else-if="form.nodeVisualType === 'fork'" class="hint-text">
                分支汇聚类通常由扩展节点自动插入，一般无需手动创建。
              </p>
            </div>
          </section>

          <section v-if="form.nodeVisualType === 'human'" class="section">
            <h3 class="section-title">人工卡点配置</h3>
            <div class="field">
              <label for="pn-human-auto">是否自动执行</label>
              <select id="pn-human-auto" v-model="form.humanAutoConfirm">
                <option :value="false">否</option>
                <option :value="true">是</option>
              </select>
              <p class="hint-text">
                选择「是」时，到达该卡点后等同默认人工确认通过，自动沿 pass 出边继续执行。
              </p>
            </div>
          </section>

          <section v-if="form.nodeVisualType === 'expand'" class="section">
            <h3 class="section-title">扩展配置</h3>
            <div class="field">
              <label for="pn-expand-template">Lane 模板</label>
              <select
                id="pn-expand-template"
                v-model="form.expandDefaultLaneTemplateId"
                @change="onExpandTemplateChange"
              >
                <option value="">请选择模板</option>
                <option v-for="tpl in workflowTemplates" :key="tpl.template_id" :value="tpl.template_id">
                  {{ tpl.name }}（{{ tpl.template_id }}）
                </option>
              </select>
              <p class="hint-text">每个并行分支实例化该 Workflow 模板；占位符由扩展规划填入</p>
            </div>
            <div class="field">
              <label for="pn-expand-catalog">候选模板（可选）</label>
              <textarea
                id="pn-expand-catalog"
                v-model="form.expandCatalogTemplatesText"
                class="mono"
                rows="2"
                spellcheck="false"
                placeholder="每行一个 template_id；留空则仅使用上方 Lane 模板"
              />
            </div>
            <div class="field-row-2">
              <div class="field">
                <label for="pn-expand-planner">扩展规划</label>
                <select id="pn-expand-planner" v-model="form.expandPlanner">
                  <option value="source">上游产出 / 默认</option>
                  <option value="native_llm">Session LLM 规划</option>
                </select>
              </div>
              <div class="field">
                <label for="pn-expand-confirm">分裂确认</label>
                <select id="pn-expand-confirm" v-model="form.expandConfirmMode">
                  <option value="manual">手工确认</option>
                  <option value="auto">自动确认</option>
                </select>
              </div>
            </div>
            <div class="field-row-2">
              <div class="field">
                <label for="pn-expand-merge">汇聚节点名称</label>
                <input id="pn-expand-merge" v-model="form.expandMergeLabel" type="text" placeholder="任务汇聚" />
              </div>
              <div class="field">
                <label for="pn-expand-source">任务来源节点 id</label>
                <input id="pn-expand-source" v-model="form.expandSourceNodeId" type="text" placeholder="留空则取直接上游" />
              </div>
            </div>
            <p v-if="form.expandConfirmMode === 'auto'" class="hint-text">
              自动确认：LLM 规划完成后直接生成分叉/汇聚拓扑并继续执行，无需点击「确认分裂」。
            </p>
          </section>

          <section class="section">
            <h3 class="section-title">文档路径</h3>
            <div class="field">
              <label for="pn-input-doc-paths">输入文档路径</label>
              <textarea
                id="pn-input-doc-paths"
                v-model="form.inputDocPathsText"
                class="mono"
                rows="4"
                spellcheck="false"
              />
              <p class="hint-text">Agent 执行前读取的参考文档，每行一条路径；留空表示不配置</p>
            </div>
            <div class="field">
              <label for="pn-output-doc-paths">输出文档路径</label>
              <textarea
                id="pn-output-doc-paths"
                v-model="form.outputDocPathsText"
                class="mono"
                rows="4"
                spellcheck="false"
              />
              <p class="hint-text">本步骤预期产出的文档，每行一条路径；留空表示不配置</p>
            </div>
          </section>

          <section v-if="form.nodeVisualType !== 'human' && form.nodeVisualType !== 'expand' && form.nodeVisualType !== 'fork'" class="section">
            <h3 class="section-title">执行 Agent</h3>
            <div v-if="!agentOptions.length" class="hint-text">
                暂无已注册 Agent，请先在「Agent 注册」中配置后再编辑本步骤。
              </div>
              <div v-else class="field field-full">
                <label for="pn-registered-agent">选择已注册 Agent</label>
                <select
                  id="pn-registered-agent"
                  v-model="form.registeredAgentId"
                  required
                  @change="onRegisteredAgentChange"
                >
                  <option value="" disabled>请选择 Agent</option>
                  <option v-for="opt in agentOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}（{{ kindLabel(opt.kind) }}）
                  </option>
                </select>
                <p v-if="selectedAgentHint" class="hint-text">{{ selectedAgentHint }}</p>
                <p v-if="usesRegisteredAgentBinding" class="hint-text bound-agent-hint">
                  命令、参数、结果 JSON 字段、会话续跑与历史目录等均取自 Agent 注册模板；本步骤只需填写上方「任务说明」。
                </p>
              </div>
          </section>
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
        <p v-if="relatedEdges.length" class="edge-hint">
          该节点有 {{ relatedEdges.length }} 条关联连线，删除时将一并移除并桥接相邻步骤。
        </p>

        <footer class="footer">
          <button
            v-if="canDelete"
            type="button"
            class="btn btn-danger"
            :disabled="loading"
            @click="handleDelete"
          >
            删除节点
          </button>
          <span class="footer-spacer" />
          <button type="button" class="btn secondary" :disabled="loading" @click="emit('close')">取消</button>
          <button type="submit" class="btn primary" :disabled="loading">{{ loading ? '保存中…' : '保存' }}</button>
        </footer>
      </form>
    </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { applyRegisteredAgentToForm, canRemoveGraphNode, editFormToNode, listNodeRelatedEdges, nodeToEditForm, syncFormFromNodeVisualType, usesRegisteredAgent } from '../../utils/planGraphEdit.js'
import { listWorkflowTemplates } from '../../api/layerApi.js'

const KIND_LABELS = {
  native: '自研',
  codex_sdk: 'Codex SDK',
  claude_code_cli: 'Claude Code CLI',
  api: '第三方 API',
}

function pickDefaultRegisteredAgent(options) {
  if (!options?.length) return null
  return options.find((opt) => opt.value === 'claude_code')
    || options.find((opt) => String(opt.executorTemplate?.kind || '').toLowerCase() === 'cli')
    || options[0]
}

function ensureRegisteredAgentDefault() {
  if (form.value.nodeVisualType === 'human') return
  if (form.value.nodeVisualType === 'expand' || form.value.nodeVisualType === 'fork') return
  if (form.value.executorKind === 'expand' || form.value.executorKind === 'fork') return
  if (!props.agentOptions.length) return
  if (form.value.registeredAgentId) return
  const preferred = pickDefaultRegisteredAgent(props.agentOptions)
  if (preferred) {
    form.value = applyRegisteredAgentToForm(form.value, preferred)
  }
}

const props = defineProps({
  nodeId: { type: String, required: true },
  node: { type: Object, default: null },
  graphSpec: { type: Object, default: null },
  agentOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save', 'delete'])

const canDelete = computed(() => {
  if (!props.graphSpec || !props.nodeId) return false
  return canRemoveGraphNode(props.graphSpec, props.nodeId).ok
})

const relatedEdges = computed(() => {
  if (!props.graphSpec || !props.nodeId) return []
  return listNodeRelatedEdges(props.graphSpec, props.nodeId)
})

const selectedAgentHint = computed(() => {
  const opt = props.agentOptions.find((item) => item.value === form.value.registeredAgentId)
  return opt?.description || ''
})

const usesRegisteredAgentBinding = computed(() => usesRegisteredAgent(form.value))

function kindLabel(kind) {
  return KIND_LABELS[kind] || kind
}

function onRegisteredAgentChange() {
  const opt = props.agentOptions.find((item) => item.value === form.value.registeredAgentId)
  if (!opt) return
  form.value = applyRegisteredAgentToForm(form.value, opt)
}

const form = ref(nodeToEditForm(props.node || { id: props.nodeId }))
const errorMsg = ref('')
const workflowTemplates = ref([])

async function loadWorkflowTemplates() {
  try {
    workflowTemplates.value = await listWorkflowTemplates()
  } catch {
    workflowTemplates.value = []
  }
}

function onExpandTemplateChange() {
  const tid = String(form.value.expandDefaultLaneTemplateId || '').trim()
  if (tid && !String(form.value.expandCatalogTemplatesText || '').trim()) {
    form.value.expandCatalogTemplatesText = tid
  }
}

onMounted(() => {
  loadWorkflowTemplates()
})

watch(
  () => [props.nodeId, props.node, props.agentOptions],
  () => {
    form.value = nodeToEditForm(props.node || { id: props.nodeId })
    ensureRegisteredAgentDefault()
    errorMsg.value = ''
  },
  { immediate: true, deep: true },
)

function onNodeVisualTypeChange() {
  form.value = syncFormFromNodeVisualType(form.value)
  ensureRegisteredAgentDefault()
}

function handleSubmit() {
  errorMsg.value = ''
  if (!String(form.value.label || '').trim()) {
    errorMsg.value = '请填写步骤名称'
    return
  }
  if (form.value.nodeVisualType === 'human') {
    emit('save', editFormToNode(props.nodeId, form.value, props.node || {}))
    return
  }
  if (form.value.nodeVisualType === 'fork') {
    emit('save', editFormToNode(props.nodeId, form.value, props.node || { id: props.nodeId }))
    return
  }
  if (form.value.nodeVisualType === 'expand') {
    if (!String(form.value.expandDefaultLaneTemplateId || '').trim()) {
      errorMsg.value = '请选择 Lane 模板'
      return
    }
    emit('save', editFormToNode(props.nodeId, form.value, props.node || { id: props.nodeId }))
    return
  }
  if (props.agentOptions.length && !usesRegisteredAgent(form.value)) {
    errorMsg.value = '请选择已注册 Agent'
    return
  }
  emit('save', editFormToNode(props.nodeId, form.value, props.node || { id: props.nodeId }))
}

function handleDelete() {
  if (!canDelete.value || props.loading) return
  emit('delete', props.nodeId)
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
  padding: 24px;
  background: rgba(32, 33, 36, 0.48);
  backdrop-filter: blur(2px);
}
.card {
  width: min(800px, 100%);
  max-height: min(90vh, 680px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.16), 0 0 0 1px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}
.header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #e8eaed;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
}
.header-text {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #202124;
  white-space: nowrap;
}
.node-id {
  font-family: ui-monospace, 'Cascadia Code', 'SF Mono', Consolas, monospace;
  font-size: 12px;
  color: #5f6368;
  background: #f1f3f4;
  padding: 3px 8px;
  border-radius: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 360px;
}
.close-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #5f6368;
  border-radius: 8px;
  transition: background 0.15s, color 0.15s;
}
.close-btn:hover {
  background: #f1f3f4;
  color: #202124;
}
.form {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.form-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 20px 8px;
}
.section + .section {
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid #f1f3f4;
}
.section-title {
  margin: 0 0 12px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #80868b;
}
.field {
  margin-bottom: 12px;
}
.field-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.field-row-2 .field {
  margin-bottom: 12px;
}
.field:last-child {
  margin-bottom: 0;
}
.field label:not(.toggle-check) {
  display: block;
  margin-bottom: 5px;
  font-size: 13px;
  font-weight: 500;
  color: #3c4043;
}
.label-hint {
  font-weight: 400;
  color: #80868b;
}
.field input:not([type="checkbox"]),
.field textarea,
.field select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 8px 11px;
  font-size: 14px;
  font-family: inherit;
  color: #202124;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field input:not([type="checkbox"]):focus,
.field textarea:focus,
.field select:focus {
  outline: none;
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.12);
}
.field textarea {
  resize: vertical;
  min-height: 56px;
  line-height: 1.45;
}
.mono {
  font-family: ui-monospace, 'Cascadia Code', 'SF Mono', Consolas, monospace;
  font-size: 13px;
}
.seg-group {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}
.seg-group-2 {
  grid-template-columns: 1fr 1fr;
}
.seg-group-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.seg-group-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.hint-text {
  margin: 0;
  font-size: 12px;
  color: #5f6368;
  line-height: 1.5;
}
.placeholder-notice {
  flex-shrink: 0;
  margin: 0;
  padding: 10px 20px;
  border-bottom: 1px solid #e8eaed;
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
.type-badge {
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}
.type-badge-human {
  color: #7627bb;
  background: #f3e8fd;
  border: 1px solid #d7aefb;
}
.seg-group-compact {
  margin-bottom: 12px;
}
.seg-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}
.seg-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 10px 12px;
  border: 1.5px solid #e8eaed;
  border-radius: 10px;
  background: #fafbfc;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  text-align: center;
}
.seg-item:hover {
  border-color: #c6dafc;
  background: #f8faff;
}
.seg-item.active {
  border-color: #1a73e8;
  background: #e8f0fe;
  box-shadow: 0 0 0 1px rgba(26, 115, 232, 0.2);
}
.seg-item-compact {
  flex-direction: row;
  padding: 8px 12px;
}
.seg-label {
  font-size: 13px;
  font-weight: 600;
  color: #202124;
}
.seg-item.active .seg-label {
  color: #1557b0;
}
.seg-desc {
  font-size: 11px;
  color: #80868b;
}
.subsection {
  margin-top: 2px;
}
.cli-panel {
  padding: 14px;
  border-radius: 10px;
  background: #f8f9fa;
  border: 1px solid #e8eaed;
}
.field-full {
  margin-bottom: 12px;
}
.field-check-row {
  margin-bottom: 10px;
}
.cli-options-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px 12px;
  margin-bottom: 12px;
}
.toggle-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  margin: 0;
  font-weight: 400;
}
.toggle-check input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
  padding: 0;
  border: none;
  pointer-events: none;
}
.toggle-box {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 1.5px solid #dadce0;
  border-radius: 4px;
  background: #fff;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}
.toggle-check input:checked + .toggle-box {
  border-color: #1a73e8;
  background: #1a73e8;
}
.toggle-check input:checked + .toggle-box::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 5px;
  height: 9px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.toggle-text {
  font-size: 13px;
  color: #3c4043;
}
.toggle-text code {
  font-size: 11px;
  color: #5f6368;
  background: #e8eaed;
  padding: 1px 5px;
  border-radius: 4px;
}
.error-msg {
  margin: 0;
  padding: 8px 20px 0;
  font-size: 13px;
  color: #d93025;
  flex-shrink: 0;
}
.edge-hint {
  margin: 0;
  padding: 8px 20px 0;
  font-size: 12px;
  color: #5f6368;
  flex-shrink: 0;
}
.footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px 16px;
  border-top: 1px solid #e8eaed;
  background: #fafbfc;
}
.footer-spacer {
  flex: 1;
}
.btn {
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;
}
.btn.secondary {
  background: #fff;
  border-color: #dadce0;
  color: #3c4043;
}
.btn.secondary:hover {
  background: #f8f9fa;
  border-color: #bdc1c6;
}
.btn.primary {
  background: #1a73e8;
  color: #fff;
}
.btn.primary:hover:not(:disabled) {
  background: #1765cc;
}
.btn.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-danger {
  background: #fce8e6;
  border-color: #f28b82;
  color: #c5221f;
}
@media (max-width: 720px) {
  .cli-options-grid,
  .seg-group-2 {
    grid-template-columns: 1fr;
  }
  .header-text {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .node-id {
    max-width: 100%;
  }
}
</style>
