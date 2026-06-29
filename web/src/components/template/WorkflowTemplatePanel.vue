<template>
  <div class="template-panel">
    <div class="panel-toolbar">
      <div>
        <h2>Workflow 模板</h2>
        <p class="hint">模板定义通用编排；Session 通过「使用模板」引用，各 Session 仅 Workspace 不同。</p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreate">新建模板</button>
    </div>

    <div v-if="loading" class="empty-state">加载中…</div>
    <div v-else-if="loadError" class="empty-state error">{{ loadError }}</div>
    <div v-else-if="!templates.length" class="empty-state">暂无模板，点击「新建模板」或从已有模板复制后编辑。</div>
    <div v-else class="template-grid">
      <article v-for="item in templates" :key="item.template_id" class="template-card">
        <header class="card-head">
          <div>
            <h3>{{ item.name }}</h3>
            <code>{{ item.template_id }}</code>
          </div>
        </header>
        <p class="desc">{{ item.description || '无描述' }}</p>
        <div class="card-meta">
          <span v-if="item.judge_mode" class="tag">Judge: {{ item.judge_mode }}</span>
          <span v-if="item.source_workflow_id" class="tag tag-src">复制来源</span>
        </div>
        <footer class="card-actions">
          <button type="button" class="btn" @click="openView(item)">查看</button>
          <button type="button" class="btn" @click="openEdit(item)">编辑</button>
          <button
            type="button"
            class="btn"
            :disabled="duplicatingId === item.template_id"
            @click="onDuplicate(item)"
          >
            {{ duplicatingId === item.template_id ? '复制中…' : '复制' }}
          </button>
          <button
            type="button"
            class="btn btn-danger"
            :disabled="deletingId === item.template_id"
            @click="onDelete(item)"
          >
            {{ deletingId === item.template_id ? '删除中…' : '删除' }}
          </button>
        </footer>
      </article>
    </div>

    <div v-if="editorDialogVisible" class="overlay overlay-editor" @mousedown.self="closeEditorDialog">
      <div class="dialog dialog-editor" role="dialog">
        <header class="dialog-head">
          <div>
            <h3>{{ editorDialogTitle }}</h3>
            <p v-if="form.name" class="dialog-sub">{{ form.name }}</p>
          </div>
          <button type="button" class="close-btn" @click="closeEditorDialog">×</button>
        </header>
        <div class="dialog-tabs" role="tablist">
          <button
            type="button"
            class="dialog-tab"
            :class="{ active: editorTab === 'info' }"
            role="tab"
            :aria-selected="editorTab === 'info'"
            @click="editorTab = 'info'"
          >
            基本信息
          </button>
          <button
            type="button"
            class="dialog-tab"
            :class="{ active: editorTab === 'graph' }"
            role="tab"
            :aria-selected="editorTab === 'graph'"
            @click="editorTab = 'graph'"
          >
            工作流
          </button>
        </div>
        <div class="dialog-body editor-body">
          <div v-show="editorTab === 'info'" class="tab-panel">
            <div class="field-row">
              <div class="field">
                <label for="tpl-name">模板名称</label>
                <input id="tpl-name" v-model="form.name" type="text" :readonly="dialogMode === 'view'" />
              </div>
              <div class="field">
                <label for="tpl-judge">Judge 模式</label>
                <select id="tpl-judge" v-model="form.judge_mode" :disabled="dialogMode === 'view'">
                  <option value="">auto（默认）</option>
                  <option value="auto">auto</option>
                  <option value="llm">llm</option>
                  <option value="json">json</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label for="tpl-desc">描述</label>
              <textarea id="tpl-desc" v-model="form.description" rows="3" :readonly="dialogMode === 'view'" />
            </div>
            <div class="field">
              <label for="tpl-goal">默认任务目标</label>
              <input id="tpl-goal" v-model="form.user_goal" type="text" :readonly="dialogMode === 'view'" />
            </div>
          </div>
          <div v-show="editorTab === 'graph'" class="tab-panel tab-panel-graph">
            <div class="graph-field graph-field-fill">
              <PlanningGraphPanel
                v-if="graphSpec"
                :graph-spec="graphSpec"
                phase="idle"
                fill-height
                :editable="dialogMode !== 'view'"
                @edit-node="openEditNode"
                @edit-edge="openEditEdge"
                @open-add-menu="openAddNode"
                @delete-node="onDeleteNode"
              />
            </div>
          </div>
          <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
        </div>
        <footer class="dialog-foot">
          <button type="button" class="btn" @click="closeEditorDialog">关闭</button>
          <button
            v-if="dialogMode !== 'view'"
            type="button"
            class="btn btn-primary"
            :disabled="submitting"
            @click="onSubmitEditor"
          >
            {{ submitting ? '保存中…' : '保存' }}
          </button>
        </footer>
      </div>
    </div>

    <PlanGraphNodeEditDialog
      v-if="editNodeVisible"
      :node-id="editingNodeId"
      :node="editingNode"
      :graph-spec="graphSpec"
      :agent-options="agentOptions"
      @close="editNodeVisible = false"
      @save="onSaveNode"
      @delete="onDeleteNode"
    />
    <PlanGraphEdgeEditDialog
      v-if="editEdgeVisible"
      :edge="editingEdge"
      :graph-spec="graphSpec"
      :creating="edgeCreating"
      @close="editEdgeVisible = false"
      @save="onSaveEdge"
      @delete="onDeleteEdge"
    />
    <PlanGraphNodeAddDialog
      v-if="addNodeVisible"
      :from-node-id="addAnchorNodeId"
      :from-node-label="addAnchorLabel"
      :graph-spec="graphSpec"
      :agent-options="agentOptions"
      @close="addNodeVisible = false"
      @submit-node="onAddNode"
      @submit-edge="onAddEdge"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import PlanningGraphPanel from '../planning/PlanningGraphPanel.vue'
import PlanGraphNodeEditDialog from '../planning/PlanGraphNodeEditDialog.vue'
import PlanGraphEdgeEditDialog from '../planning/PlanGraphEdgeEditDialog.vue'
import PlanGraphNodeAddDialog from '../planning/PlanGraphNodeAddDialog.vue'
import {
  cloneGraphSpec,
  replaceGraphNode,
  removeGraphNode,
  updateGraphEdge,
  addGraphEdge,
  removeGraphEdge,
  addSuccessorNode,
  agentsToOptions,
} from '../../utils/planGraphEdit.js'
import { resolveGraphNodeLabel } from '../../utils/planGraphState.js'
import {
  createWorkflowTemplate,
  deleteWorkflowTemplate,
  duplicateWorkflowTemplate,
  listAgents,
  listWorkflowTemplates,
  updateWorkflowTemplate,
} from '../../api/layerApi.js'

const emit = defineEmits(['changed'])

const templates = ref([])
const loading = ref(false)
const loadError = ref('')
const editorDialogVisible = ref(false)
const editorTab = ref('info')
const dialogMode = ref('create')
const editingId = ref('')
const submitting = ref(false)
const deletingId = ref('')
const duplicatingId = ref('')
const errorMsg = ref('')
const graphSpec = ref(null)
const agentOptions = ref([])
const editNodeVisible = ref(false)
const editEdgeVisible = ref(false)
const addNodeVisible = ref(false)
const editingNodeId = ref('')
const editingNode = ref(null)
const editingEdge = ref(null)
const edgeCreating = ref(false)
const addAnchorNodeId = ref('')

const form = reactive({
  name: '',
  description: '',
  user_goal: '',
  judge_mode: '',
})

const editorDialogTitle = computed(() => {
  if (dialogMode.value === 'create') return '新建 Workflow 模板'
  if (dialogMode.value === 'edit') return '编辑 Workflow 模板'
  return '查看 Workflow 模板'
})

const addAnchorLabel = computed(() => resolveGraphNodeLabel(graphSpec.value, addAnchorNodeId.value))

function defaultGraphSpec() {
  return {
    nodes: [],
    edges: [],
    entry: '',
  }
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.user_goal = ''
  form.judge_mode = ''
  graphSpec.value = cloneGraphSpec(defaultGraphSpec())
  errorMsg.value = ''
}

function fillForm(item) {
  form.name = item.name || ''
  form.description = item.description || ''
  form.user_goal = item.user_goal || ''
  form.judge_mode = item.judge_mode || ''
  graphSpec.value = cloneGraphSpec(item.graph || defaultGraphSpec())
  errorMsg.value = ''
}

function openEditor(mode, item = null, tab = 'info') {
  dialogMode.value = mode
  editorTab.value = tab
  if (item) {
    editingId.value = item.template_id
    fillForm(item)
  } else {
    editingId.value = ''
    resetForm()
  }
  editorDialogVisible.value = true
}

function editingNodeById(nodeId) {
  return graphSpec.value?.nodes?.find((n) => n.id === nodeId) || null
}

async function loadAgents() {
  try {
    const agents = await listAgents()
    agentOptions.value = agentsToOptions(agents.filter((a) => a.enabled !== false))
  } catch {
    agentOptions.value = []
  }
}

async function refresh() {
  loading.value = true
  loadError.value = ''
  try {
    templates.value = await listWorkflowTemplates()
  } catch (e) {
    templates.value = []
    loadError.value = e?.message || '加载模板失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  openEditor('create')
}

function openView(item) {
  openEditor('view', item, 'info')
}

function openEdit(item, tab = 'info') {
  openEditor('edit', item, tab)
}

function closeEditorDialog() {
  editorDialogVisible.value = false
  errorMsg.value = ''
}

function openEditNode(nodeId) {
  editingNodeId.value = nodeId
  editingNode.value = editingNodeById(nodeId)
  editNodeVisible.value = true
}

function openEditEdge(edge) {
  edgeCreating.value = false
  editingEdge.value = { ...edge }
  editEdgeVisible.value = true
}

function openAddNode(anchorNodeId) {
  addAnchorNodeId.value = anchorNodeId
  addNodeVisible.value = true
}

function onSaveNode(nextNode) {
  graphSpec.value = replaceGraphNode(graphSpec.value, nextNode.id, nextNode)
  editNodeVisible.value = false
}

function onDeleteNode(nodeId) {
  const id = nodeId || editingNodeId.value
  if (!id) return
  graphSpec.value = removeGraphNode(graphSpec.value, id)
  editNodeVisible.value = false
}

function onSaveEdge(nextEdge) {
  graphSpec.value = edgeCreating.value
    ? addGraphEdge(graphSpec.value, nextEdge.from, nextEdge.to, nextEdge.condition)
    : updateGraphEdge(graphSpec.value, editingEdge.value, nextEdge)
  editEdgeVisible.value = false
}

function onDeleteEdge(edge) {
  graphSpec.value = removeGraphEdge(graphSpec.value, edge || editingEdge.value)
  editEdgeVisible.value = false
}

function onAddNode(nextNode) {
  const { spec } = addSuccessorNode(graphSpec.value, addAnchorNodeId.value, nextNode)
  graphSpec.value = spec
  addNodeVisible.value = false
}

function onAddEdge(nextEdge) {
  graphSpec.value = addGraphEdge(
    graphSpec.value,
    nextEdge.from,
    nextEdge.to,
    nextEdge.condition,
  )
  addNodeVisible.value = false
}

async function onSubmitEditor() {
  if (dialogMode.value === 'view') return
  errorMsg.value = ''
  if (!String(form.name || '').trim()) {
    errorMsg.value = '请填写模板名称'
    editorTab.value = 'info'
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      user_goal: form.user_goal.trim(),
      judge_mode: form.judge_mode || '',
      graph: graphSpec.value || defaultGraphSpec(),
    }
    if (dialogMode.value === 'create') {
      const created = await createWorkflowTemplate(payload)
      editingId.value = created.template_id
      dialogMode.value = 'edit'
    } else {
      await updateWorkflowTemplate(editingId.value, payload)
    }
    await refresh()
    emit('changed')
    closeEditorDialog()
  } catch (e) {
    errorMsg.value = e?.message || '保存失败'
  } finally {
    submitting.value = false
  }
}

async function onDuplicate(item) {
  if (!item?.template_id || duplicatingId.value) return
  duplicatingId.value = item.template_id
  try {
    const created = await duplicateWorkflowTemplate(item.template_id, {
      name: `${item.name} 副本`,
    })
    await refresh()
    emit('changed')
    openEdit(created)
  } catch (e) {
    alert(e?.message || '复制失败')
  } finally {
    duplicatingId.value = ''
  }
}

async function onDelete(item) {
  if (!item?.template_id) return
  if (!window.confirm(`确定删除模板「${item.name}」？`)) return
  deletingId.value = item.template_id
  try {
    await deleteWorkflowTemplate(item.template_id)
    await refresh()
    emit('changed')
  } catch (e) {
    alert(e?.message || '删除失败')
  } finally {
    deletingId.value = ''
  }
}

onMounted(async () => {
  await Promise.all([refresh(), loadAgents()])
})

defineExpose({ refresh })
</script>

<style scoped>
.template-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}
.panel-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 16px;
}
.panel-toolbar h2 {
  margin: 0 0 4px;
  font-size: 16px;
}
.hint {
  margin: 0;
  font-size: 13px;
  color: #5f6368;
}
.template-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.template-card {
  flex: 0 1 320px;
  max-width: 360px;
  width: 100%;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.card-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
}
.card-head code {
  font-size: 11px;
  color: #5f6368;
  background: #f1f3f4;
  padding: 2px 6px;
  border-radius: 4px;
}
.card-actions {
  display: flex;
  justify-content: center;
  gap: 6px;
  flex-wrap: nowrap;
}
.desc {
  margin: 0;
  font-size: 13px;
  color: #3c4043;
  line-height: 1.5;
  flex: 1;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f3f4;
  color: #5f6368;
}
.tag-src {
  background: #fef7e0;
  color: #b06000;
}
.card-actions .btn {
  padding: 6px 10px;
  white-space: nowrap;
  flex-shrink: 0;
}
.empty-state {
  padding: 48px;
  text-align: center;
  color: #80868b;
  background: #fff;
  border: 1px dashed #dadce0;
  border-radius: 8px;
}
.empty-state.error {
  color: #c5221f;
  border-color: #f28b82;
  background: #fce8e6;
}
.btn {
  padding: 6px 14px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
}
.btn-danger {
  background: #fce8e6;
  border-color: #f28b82;
  color: #c5221f;
}
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(32, 33, 36, 0.48);
}
.overlay-editor {
  z-index: 1310;
  padding: 12px;
  align-items: stretch;
}
.dialog-tabs {
  display: flex;
  gap: 0;
  padding: 0 18px;
  border-bottom: 1px solid #e8eaed;
  background: #fafbfc;
  flex-shrink: 0;
}
.dialog-tab {
  border: none;
  background: transparent;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #5f6368;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.dialog-tab.active {
  color: #1a73e8;
  border-bottom-color: #1a73e8;
}
.editor-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0;
  position: relative;
}
.tab-panel:not(.tab-panel-graph) {
  padding: 16px 18px;
  overflow: auto;
}
.tab-panel {
  flex: 1;
  min-height: 0;
}
.tab-panel-graph {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}
.graph-field-fill {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  border: none;
  border-radius: 0;
  overflow: hidden;
}
.graph-field-fill :deep(.plan-graph-panel) {
  border-radius: 0;
}
.editor-body .error-msg {
  padding: 8px 18px 0;
  flex-shrink: 0;
}
.dialog {
  width: min(720px, 100%);
  max-height: min(90vh, 820px);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.dialog-wide {
  width: min(960px, 100%);
  max-height: min(92vh, 900px);
}
.dialog-graph {
  width: min(1200px, calc(100vw - 48px));
  height: min(96vh, 920px);
  max-height: min(96vh, 920px);
}
.dialog.dialog-editor {
  width: 100%;
  max-width: none;
  height: calc(100vh - 24px);
  max-height: calc(100vh - 24px);
}
.dialog-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #5f6368;
  font-weight: normal;
}
.graph-dialog-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.overlay-graph {
  z-index: 1310;
}
.dialog-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #e8eaed;
}
.dialog-head h3 {
  margin: 0;
  font-size: 16px;
}
.close-btn {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  color: #5f6368;
}
.dialog-body {
  padding: 16px 18px;
  overflow: auto;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 12px;
}
.field {
  margin-bottom: 12px;
}
.graph-field {
  border: 1px solid #dadce0;
  border-radius: 8px;
  overflow: hidden;
}
.graph-field label {
  display: block;
  padding: 8px 10px 0;
  margin-bottom: 0;
}
.field label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
}
.error-msg {
  color: #c5221f;
  font-size: 13px;
}
.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid #e8eaed;
  background: #fafbfc;
  flex-shrink: 0;
}
</style>
