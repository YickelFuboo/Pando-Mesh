<template>
  <div
    class="app-shell"
    :class="{
      'full-width-mode': mainTab !== 'workflow',
      'sidebar-collapsed': mainTab === 'workflow' && sidebarCollapsed,
    }"
    :style="mainTab === 'workflow' && !sidebarCollapsed ? { '--sidebar-width': `${sidebarWidth}px` } : undefined"
  >
    <header class="app-header">
      <div class="header-start">
        <div class="header-brand">
          <span class="brand-mark" aria-hidden="true">P</span>
          <h1>MOMA Pipeline</h1>
        </div>
        <nav class="header-nav" role="tablist">
          <button
            type="button"
            class="nav-link nav-link-home"
            :class="{ active: mainTab === 'home' }"
            title="主页"
            aria-label="主页"
            @click="switchMainTab('home')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M12 3l9 8h-2v9h-5v-6H10v6H5v-9H3l9-8z" />
            </svg>
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: mainTab === 'features' }"
            @click="switchMainTab('features')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M4 6h7v7H4V6zm9 0h7v7h-7V6zM4 15h7v7H4v-7zm9 0h7v7h-7v-7z" />
            </svg>
            Features
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: mainTab === 'architectures' }"
            @click="switchMainTab('architectures')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M4 6h7v2H4V6zm0 5h10v2H4v-2zm0 5h7v2H4v-2zM14 8h6v2h-6V8zm0 5h6v2h-6v-2z" />
            </svg>
            Architectures
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: mainTab === 'requirements' }"
            @click="switchMainTab('requirements')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM8 13h8v2H8v-2zm0 4h8v2H8v-2z" />
            </svg>
            Requirements
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: mainTab === 'knowledge' }"
            @click="switchMainTab('knowledge')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M12 3a6 6 0 0 0-4.5 10.06V17a1 1 0 0 0 .55.9l3.45 1.72a1 1 0 0 0 .9 0L15.45 17.9A1 1 0 0 0 16 17v-3.94A6 6 0 0 0 12 3zm0 2a4 4 0 0 1 0 8 4 4 0 0 1 0-8z" />
            </svg>
            Knowledge
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: mainTab === 'workflow' }"
            @click="switchMainTab('workflow')"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M4 6c0-1.1.9-2 2-2h3v2H6v3H4V6zm14-2h-3v2h3v3h2V6c0-1.1-.9-2-2-2zM4 18v-3H2v3c0 1.1.9 2 2 2h3v-2H4zm16 0h-3v2h3c1.1 0 2-.9 2-2v-3h-2v3zM9 10h6v4H9v-4z" />
            </svg>
            WorkFlow
          </button>
        </nav>
      </div>
      <div class="header-end">
        <div class="header-workspace">
          <label class="header-workspace-label" for="header-workspace-input">作业空间路径</label>
          <input
            id="header-workspace-input"
            v-model="workspacePath"
            class="header-workspace-input"
            placeholder="D:/projects/my-app"
            :title="workspacePath"
            @change="onWorkspaceChange"
          />
        </div>
        <div class="header-actions">
        <template v-if="mainTab === 'workflow'">
        <button
          v-if="workflow && isDynamicPlan"
          type="button"
          class="btn"
          :disabled="generating"
          :title="llmStatus?.available === false ? 'LLM 未配置，仍可填写目标；生成前请在配置中设置模型' : undefined"
          @click="onGenerateGraph"
        >
          {{ generating ? '生成中…' : 'AI 生成拓扑' }}
        </button>
        <button
          v-if="workflow && executing"
          type="button"
          class="btn btn-danger"
          :disabled="subjectAbortId === workflowId"
          @click="onAbort"
        >
          {{ subjectAbortId === workflowId ? '中止中…' : '中止' }}
        </button>
        </template>
        <button
          type="button"
          class="icon-btn"
          title="配置"
          aria-label="配置"
          @click="configVisible = true"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path
              fill="currentColor"
              d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81a.488.488 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.49.49 0 0 0-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z"
            />
          </svg>
        </button>
        </div>
      </div>
    </header>

    <aside v-if="mainTab === 'workflow'" class="sidebar">
      <div class="sidebar-section">
        <div class="switch-row">
          <span class="switch-label">使用工作流模板</span>
          <label class="toggle">
            <input v-model="useWorkflow" type="checkbox" class="toggle-input" @change="onUseWorkflowChange" />
            <span class="toggle-track" aria-hidden="true" />
          </label>
        </div>
        <select
          v-if="useWorkflow"
          v-model="selectedSubjectType"
          class="workspace-input template-select"
          @change="onSubjectTypeChange"
        >
          <option v-for="opt in ALL_SUBJECT_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <select
          v-else
          v-model="selectedSubjectType"
          class="workspace-input template-select"
          @change="onSubjectTypeChange"
        >
          <option v-for="opt in ALL_SUBJECT_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <select
          v-if="useWorkflow"
          v-model="defaultTemplateId"
          class="workspace-input template-select"
          @change="onDefaultTemplateChange"
        >
          <option value="">请选择模板…</option>
          <option v-for="tpl in filteredWorkflowTemplates" :key="tpl.template_id" :value="tpl.template_id">
            {{ tpl.name }}
          </option>
        </select>
        <p v-if="useWorkflow && selectedTemplate && subjectGranularityLabel" class="sidebar-subject-hint">
          粒度：{{ subjectGranularityLabel }}
        </p>
        <p class="sidebar-hint">
          {{ useWorkflow
            ? '新建 Session 时引用所选模板；已有 Session 可点「初始化」套用新模板；拓扑请在右上角「配置 → 模板管理」中编辑'
            : '关闭后由 AI 动态规划生成编排拓扑' }}
        </p>
      </div>
      <div v-if="showSubjectObjectPanel" class="sidebar-section">
        <div class="sidebar-head">
          <h2>作业对象</h2>
          <button type="button" class="btn btn-small" :disabled="subjectObjectsLoading" @click="refreshSubjectObjects">
            {{ subjectObjectsLoading ? '…' : '刷新' }}
          </button>
        </div>
        <p v-if="subjectObjectsError" class="sidebar-error">{{ subjectObjectsError }}</p>
        <div v-else-if="supportsBatchActions && subjectObjects.length" class="req-batch-bar">
          <label class="req-select-all" @click.stop>
            <input
              type="checkbox"
              :checked="allSubjectObjectsChecked"
              :disabled="batchBusy"
              @change="toggleSelectAllSubjectObjects"
            />
            <span>全选</span>
          </label>
          <div class="req-actions">
            <button
              type="button"
              class="btn-play"
              :disabled="!checkedSubjectObjectCount || batchBusy"
              title="批量启动"
              @click="batchStartSubjectObjects"
            >
              <svg class="play-icon" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M5 3.5v9l7-4.5z" fill="currentColor" />
              </svg>
            </button>
            <button
              v-if="useWorkflow && defaultTemplateId"
              type="button"
              class="btn btn-init"
              :disabled="!checkedSubjectObjectCount || batchBusy"
              title="批量初始化"
              @click="batchInitSubjectObjects"
            >
              {{ batchBusy ? '…' : '初始化' }}
            </button>
          </div>
        </div>
        <ul v-if="!subjectObjectsError" class="req-list">
          <li
            v-for="item in subjectObjects"
            :key="item.object_id"
            :class="{ active: isSubjectObjectActive(item), checked: isSubjectObjectChecked(item) }"
            @click="selectSubjectObject(item)"
          >
            <label v-if="supportsBatchActions" class="req-check" @click.stop>
              <input
                type="checkbox"
                :checked="isSubjectObjectChecked(item)"
                :disabled="batchBusy"
                @change="toggleSubjectObjectCheck(item)"
              />
            </label>
            <div class="req-main">
              <span class="req-name">{{ item.label }}</span>
              <span v-if="item.summary" class="req-summary">{{ item.summary }}</span>
            </div>
            <div class="req-badges" @click.stop>
              <div v-if="item.running || item.has_session || (useWorkflow && defaultTemplateId)" class="req-actions">
                <button
                  v-if="item.running"
                  type="button"
                  class="btn-stop"
                  :disabled="!item.workflow_id || subjectAbortId === item.workflow_id || batchBusy"
                  title="停止执行"
                  @click.stop="stopSubjectObjectWorkflow(item)"
                >
                  {{ subjectAbortId === item.workflow_id ? '…' : '停止' }}
                </button>
                <button
                  v-else-if="item.has_session"
                  type="button"
                  class="btn-play"
                  :disabled="subjectOpeningId === item.object_id || subjectStartId === item.object_id || batchBusy || item.running || subjectObjectAwaitingPending(item) || (item.workflow_id === workflowId && executing)"
                  :title="subjectObjectStartTitle(item)"
                  @click.stop="startSubjectObjectWorkflow(item)"
                >
                  <svg class="play-icon" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M5 3.5v9l7-4.5z" fill="currentColor" />
                  </svg>
                </button>
                <button
                  v-if="useWorkflow && defaultTemplateId && !item.running"
                  type="button"
                  class="btn btn-init"
                  :disabled="subjectInitId === item.object_id || batchBusy"
                  @click.stop="initSubjectObjectFromTemplate(item)"
                >
                  {{ subjectInitId === item.object_id ? '…' : '初始化' }}
                </button>
              </div>
              <span v-if="item.running" class="wf-badge">执行中</span>
              <span v-else-if="subjectObjectAwaitingPending(item)" class="req-tag req-tag-pending">待确认</span>
              <span v-else-if="item.has_session" class="req-tag">Session</span>
            </div>
          </li>
        </ul>
        <p v-if="!subjectObjectsLoading && !subjectObjectsError && workspacePath && !subjectObjects.length" class="sidebar-empty">
          {{ subjectObjectsEmptyHint }}
        </p>
        <p class="sidebar-hint req-list-hint">{{ subjectObjectsHint }}</p>
      </div>
      <p v-else-if="useWorkflow && !defaultTemplateId" class="sidebar-empty">请先选择工作流模板</p>
    </aside>

    <div
      v-if="mainTab === 'workflow'"
      class="sidebar-resize-handle"
      :class="{ dragging: sidebarResizing && !sidebarCollapsed, collapsed: sidebarCollapsed }"
      :title="sidebarCollapsed ? '展开侧栏' : '拖动调整侧栏宽度'"
      @mousedown.prevent="onSidebarHandleMouseDown"
    >
      <button
        type="button"
        class="sidebar-collapse-btn"
        :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
        :aria-label="sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
        @click.stop="toggleSidebarCollapsed"
        @mousedown.stop
      >
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path
            fill="currentColor"
            :d="sidebarCollapsed ? 'M6 3l5 5-5 5V3z' : 'M10 3L5 8l5 5V3z'"
          />
        </svg>
      </button>
      <span v-if="!sidebarCollapsed" class="sidebar-resize-handle-bar" aria-hidden="true" />
    </div>

    <main
      class="main"
      :class="{
        'workspace-main': activeMainView === 'workflow',
        'canvas-main': activeMainView === 'features' || activeMainView === 'architectures' || activeMainView === 'requirements',
        'page-main': activeMainView === 'home' || activeMainView === 'knowledge',
      }"
    >
      <HomePanel
        v-if="activeMainView === 'home'"
        key="tab-home"
        :workspace-path="workspacePath"
        @navigate="switchMainTab"
      />

      <FeaturesPanel
        v-else-if="activeMainView === 'features'"
        key="tab-features"
        :workspace-path="workspacePath"
      />

      <ArchitecturesPanel
        v-else-if="activeMainView === 'architectures'"
        key="tab-architectures"
        :workspace-path="workspacePath"
      />

      <RequirementsPanel
        v-else-if="activeMainView === 'requirements'"
        key="tab-requirements"
        :workspace-path="workspacePath"
      />

      <KnowledgePanel
        v-else-if="activeMainView === 'knowledge'"
        key="tab-knowledge"
        :workspace-path="workspacePath"
      />

      <div v-else-if="activeMainView === 'workflow'" key="tab-workflow" class="workflow-shell">
      <WorkflowPendingPanel
        class="workbench-pending"
        :phase="snapshot?.phase || 'idle'"
        :pending-gate="snapshot?.pendingGate || {}"
        :pending-expand="snapshot?.pendingExpand || {}"
        :busy="pendingBusy"
        @approve="onGateApprove"
        @reject="onGateReject"
        @expand="onExpandApply"
      />

      <div ref="workbenchMainRef" class="workbench-main">
        <PlanningGraphPanel
          v-if="graphSpec"
          ref="planGraphPanelRef"
          :graph-spec="graphSpec"
          :phase="snapshot?.phase || 'idle'"
          :running-node-ids="snapshot?.runningNodeIds || []"
          :completed-node-ids="snapshot?.completedNodeIds || []"
          :node-iterations="snapshot?.nodeIterations || {}"
          :pre-node-reject-infos="snapshot?.preNodeRejectInfos || {}"
          :node-session-ids="snapshot?.nodeSessionIds || {}"
          :topology-selected-node-id="topologySelectedNodeId"
          :selected-node-id="selectedPlanNodeId"
          :execution-disabled="executeInFlight"
          :editable="false"
          :show-settings-button="true"
          :panel-height="planGraphPanelHeight"
          @topology-select-node="onTopologySelectNode"
          @select-node="onSelectPlanNode"
          @execute-node="onExecuteFromNode"
          @open-settings="sessionSettingsVisible = true"
        />
        <div
          v-if="graphSpec"
          class="plan-graph-resize-handle"
          title="拖动调整拓扑区域高度"
          @mousedown.prevent="startResizePlanGraph"
        >
          <span class="plan-graph-resize-handle-bar" />
        </div>
        <WorkflowChatPanel
          :workflow-id="workflowId"
          :graph-spec="graphSpec"
          :snapshot="snapshot"
          :selected-node-id="selectedPlanNodeId || ''"
          :message-count="workflow?.messages?.length ?? 0"
          :busy="reviseBusy"
          :executing="executing"
          :disabled="awaitingPending"
          @revise="onNodeRevise"
          @send="onChatSend"
        />
      </div>
      </div>

      <div v-else-if="activeMainView === 'workflow-empty'" key="tab-workflow-empty" class="empty-hint">
        {{ workspacePath ? emptyWorkflowHint : '请先在顶栏填写作业空间路径' }}
      </div>
    </main>

    <Teleport to="body">
      <div v-if="generateGraphVisible" class="overlay" @mousedown.self="closeGenerateGraphDialog">
        <div class="dialog-card dialog-wide" role="dialog" aria-modal="true" aria-labelledby="generate-graph-title">
          <h3 id="generate-graph-title">AI 生成拓扑</h3>
          <p class="dialog-desc">填写任务目标，AI 将根据目标生成编排拓扑。</p>
          <p v-if="llmStatus && !llmStatus.available" class="dialog-warn">
            LLM 未配置，请先在右上角「配置 → 模型服务」中设置模型后再开始生成。
          </p>
          <label class="dialog-field">
            任务目标
            <textarea
              ref="generateGoalInputRef"
              v-model="generateGraphGoal"
              rows="5"
              placeholder="描述要实现的功能、约束与交付物…"
            />
          </label>
          <p v-if="generateGraphError" class="dialog-error">{{ generateGraphError }}</p>
          <footer class="dialog-foot">
            <button type="button" class="btn" @click="closeGenerateGraphDialog">取消</button>
            <button type="button" class="btn btn-primary" :disabled="generating" @click="confirmGenerateGraph">
              {{ generating ? '生成中…' : '开始生成' }}
            </button>
          </footer>
        </div>
      </div>
    </Teleport>

    <WorkflowSessionSettingsDialog
      :visible="sessionSettingsVisible"
      :user-goal="form.user_goal"
      :judge-mode="form.judge_mode"
      :show-judge="isDynamicPlan"
      :saving="sessionSettingsSaving"
      @close="sessionSettingsVisible = false"
      @save="onSessionSettingsSave"
    />

    <AppConfigDialog
      :visible="configVisible"
      @close="configVisible = false"
      @models-saved="onSettingsSaved"
      @templates-changed="loadWorkflowTemplates"
      @agents-changed="loadAgents"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import PlanningGraphPanel from './components/planning/PlanningGraphPanel.vue'
import WorkflowPendingPanel from './components/planning/WorkflowPendingPanel.vue'
import WorkflowChatPanel from './components/workspace/WorkflowChatPanel.vue'
import WorkflowSessionSettingsDialog from './components/workspace/WorkflowSessionSettingsDialog.vue'
import HomePanel from './components/workspace/HomePanel.vue'
import FeaturesPanel from './components/workspace/FeaturesPanel.vue'
import ArchitecturesPanel from './components/workspace/ArchitecturesPanel.vue'
import RequirementsPanel from './components/workspace/RequirementsPanel.vue'
import KnowledgePanel from './components/workspace/KnowledgePanel.vue'
import AppConfigDialog from './components/settings/AppConfigDialog.vue'
import { extractPlanGraphSnapshot } from './utils/planGraphState.js'
import { cloneGraphSpec } from './utils/planGraphEdit.js'
import {
  ALL_SUBJECT_TYPE_OPTIONS,
  SUBJECT_TYPE_IR,
  filterTemplatesBySubjectType,
  findTemplateById,
  granularityLabel,
  objectMatchesWorkflow,
  objectSessionKey,
  resolveTemplateSubjectSchema,
} from './utils/subjectSchema.js'
import {
  generateGraph,
  getLlmStatus,
  listSubjectObjects,
  openSubjectSession,
  getWorkflow,
  updateWorkflow,
  executeWorkflow,
  abortWorkflow,
  gateApprove,
  gateReject,
  expandApply,
  reviseNode,
  listWorkflowTemplates,
  initWorkflowFromTemplate,
} from './api/layerApi.js'

const WORKSPACE_STORAGE_KEY = 'moma_pipeline_workspace_path'
const DEFAULT_TEMPLATE_STORAGE_KEY = 'moma_pipeline_default_template_id'
const SUBJECT_TYPE_STORAGE_KEY = 'moma_pipeline_subject_type'
const PLAN_MODE_STORAGE_KEY = 'moma_pipeline_plan_mode'
const SIDEBAR_WIDTH_STORAGE_KEY = 'moma_pipeline_sidebar_width'
const SIDEBAR_COLLAPSED_STORAGE_KEY = 'moma_pipeline_sidebar_collapsed'
const SIDEBAR_MIN_W = 220
const SIDEBAR_MAX_W = 560
const SIDEBAR_DEFAULT_W = 280

function readSidebarWidth() {
  const raw = Number(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY))
  if (!Number.isFinite(raw)) return SIDEBAR_DEFAULT_W
  return Math.min(SIDEBAR_MAX_W, Math.max(SIDEBAR_MIN_W, Math.round(raw)))
}

function readSidebarCollapsed() {
  return localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === '1'
}

const EMPTY_GRAPH = { nodes: [], edges: [], entry: '' }

const useWorkflow = ref((localStorage.getItem(PLAN_MODE_STORAGE_KEY) || 'template') !== 'dynamic')
const defaultTemplateId = ref(localStorage.getItem(DEFAULT_TEMPLATE_STORAGE_KEY) || '')
const selectedSubjectType = ref(localStorage.getItem(SUBJECT_TYPE_STORAGE_KEY) || SUBJECT_TYPE_IR)
const workflowTemplates = ref([])
const subjectObjects = ref([])
const selectedObjectId = ref('')
const subjectObjectsLoading = ref(false)
const subjectObjectsError = ref('')
const subjectOpeningId = ref('')
const subjectInitId = ref('')
const subjectStartId = ref('')
const subjectAbortId = ref('')
const checkedSubjectObjectIds = ref([])
const workspacePath = ref(localStorage.getItem(WORKSPACE_STORAGE_KEY) || '')
const batchBusy = ref(false)
const sidebarWidth = ref(readSidebarWidth())
const sidebarCollapsed = ref(readSidebarCollapsed())
const sidebarResizing = ref(false)
const mainTab = ref('home')

function switchMainTab(tab) {
  mainTab.value = tab
}

const workflowId = ref('')
const workflow = ref(null)
const graphSpec = ref(null)
const form = reactive({ workspace_path: '', user_goal: '', judge_mode: '' })
const llmStatus = ref(null)
const generating = ref(false)
const pendingBusy = ref(false)
const reviseBusy = ref(false)
const configVisible = ref(false)
const sessionSettingsVisible = ref(false)
const sessionSettingsSaving = ref(false)
const generateGraphVisible = ref(false)
const generateGraphGoal = ref('')
const generateGraphError = ref('')
const generateGoalInputRef = ref(null)
const workbenchMainRef = ref(null)
const planGraphPanelRef = ref(null)
const planGraphPanelHeight = ref(168)
const PLAN_GRAPH_MIN_H = 120
const PLAN_GRAPH_DEFAULT_H = 168
const topologySelectedNodeId = ref(null)
const selectedPlanNodeId = ref(null)
let pollTimer = null

const snapshot = computed(() => {
  if (!workflow.value?.metadata) return null
  return extractPlanGraphSnapshot(workflow.value.metadata)
})

const workflowRunning = computed(() => Boolean(workflow.value?.running))
const executing = computed(() => workflowRunning.value || snapshot.value?.phase === 'executing')
const executeInFlight = computed(() => workflowRunning.value)
const activeSubjectType = computed(() => selectedSubjectType.value)
const anySubjectObjectRunning = computed(() => subjectObjects.value.some((item) => item.running))
const filteredWorkflowTemplates = computed(() => (
  filterTemplatesBySubjectType(workflowTemplates.value, selectedSubjectType.value)
))
const selectedTemplate = computed(() => findTemplateById(workflowTemplates.value, defaultTemplateId.value))
const selectedSubjectSchema = computed(() => resolveTemplateSubjectSchema(selectedTemplate.value || {}))
const subjectGranularityLabel = computed(() => granularityLabel(selectedSubjectSchema.value.granularity))
const showSubjectObjectPanel = computed(() => (
  Boolean(workspacePath.value.trim()) && (!useWorkflow.value || Boolean(defaultTemplateId.value))
))
const supportsBatchActions = computed(() => selectedSubjectType.value === SUBJECT_TYPE_IR)
const checkedSubjectObjectCount = computed(() => checkedSubjectObjectIds.value.length)
const allSubjectObjectsChecked = computed(() => (
  subjectObjects.value.length > 0
  && subjectObjects.value.every((item) => checkedSubjectObjectIds.value.includes(item.object_id))
))
const subjectObjectsEmptyHint = computed(() => {
  const hints = {
    workspace: '当前 Workspace 已就绪',
    feature: '未找到特性节点，请检查 features/ 目录',
    arch_element: '未找到架构元素，请检查 architectures/ 目录',
    ir: '未找到需求子目录',
    sr: '未找到 SR 变更说明',
    ar: '未找到 AR 变更说明',
    repo: '未找到代码仓，请检查 repos/ 目录',
  }
  return hints[selectedSubjectType.value] || '未找到作业对象'
})
const subjectObjectsHint = computed(() => {
  const hints = {
    workspace: '作用于整个作业空间',
    feature: '对象来自 features/ 特性库',
    arch_element: '对象来自 architectures/ 架构元素',
    ir: '对象来自 requirements/ 需求目录',
    sr: '对象来自各 IR 下的 SR 变更说明',
    ar: '对象来自各 IR 下的 AR 变更说明',
    repo: '对象来自 repos/ 代码仓目录',
  }
  return hints[selectedSubjectType.value] || ''
})
const emptyWorkflowHint = computed(() => {
  if (useWorkflow.value && !defaultTemplateId.value) {
    return '请先在左侧选择工作流模板'
  }
  return `请从左侧选择${ALL_SUBJECT_TYPE_OPTIONS.find((o) => o.value === selectedSubjectType.value)?.label || '作业对象'}以打开 Workflow Session`
})

const awaitingPending = computed(() => {
  const phase = snapshot.value?.phase || workflow.value?.pending?.phase || 'idle'
  return phase === 'awaiting_human' || phase === 'awaiting_expand'
})

function subjectObjectAwaitingPending(item) {
  if (!item?.has_session) return false
  if (isSubjectObjectActive(item)) {
    return awaitingPending.value
  }
  const phase = String(item.plan_phase || '').trim()
  return phase === 'awaiting_human' || phase === 'awaiting_expand'
}

function subjectObjectStartTitle(item) {
  if (subjectObjectAwaitingPending(item)) {
    if (isSubjectObjectActive(item)) {
      return pendingStartBlockMessage()
    }
    return '工作流有待确认事项，请先在右侧处理'
  }
  if (item.running) return '工作流执行中'
  return '启动工作流'
}

function pendingStartBlockMessage() {
  const phase = snapshot.value?.phase || workflow.value?.pending?.phase || 'idle'
  if (phase === 'awaiting_expand') {
    return '工作流停在「任务分裂确认」：请在右侧工作区顶部的黄色面板中确认子任务列表，然后再点启动。'
  }
  if (phase === 'awaiting_human') {
    return '工作流停在「人工卡点」：请在右侧工作区顶部的黄色面板中通过或驳回，然后再点启动。'
  }
  return '当前工作流暂不可启动，请先处理右侧工作区的待确认事项。'
}

function isSubjectObjectActive(item) {
  return objectMatchesWorkflow(item, workflow.value) && workflowId.value === item.workflow_id
}

function isSubjectObjectChecked(item) {
  return checkedSubjectObjectIds.value.includes(item.object_id)
}

function toggleSubjectObjectCheck(item) {
  const id = item.object_id
  if (isSubjectObjectChecked(item)) {
    checkedSubjectObjectIds.value = checkedSubjectObjectIds.value.filter((row) => row !== id)
  } else {
    checkedSubjectObjectIds.value = [...checkedSubjectObjectIds.value, id]
  }
}

function toggleSelectAllSubjectObjects() {
  if (allSubjectObjectsChecked.value) {
    checkedSubjectObjectIds.value = []
  } else {
    checkedSubjectObjectIds.value = subjectObjects.value.map((item) => item.object_id)
  }
}

function getCheckedSubjectObjects() {
  const idSet = new Set(checkedSubjectObjectIds.value)
  return subjectObjects.value.filter((item) => idSet.has(item.object_id))
}

function syncCheckedSubjectObjectIds(items) {
  const validIds = new Set(items.map((item) => item.object_id))
  checkedSubjectObjectIds.value = checkedSubjectObjectIds.value.filter((id) => validIds.has(id))
}

const isDynamicPlan = computed(() => {
  if (workflow.value?.plan_mode) return workflow.value.plan_mode === 'dynamic'
  return !useWorkflow.value
})

const activeMainView = computed(() => {
  if (mainTab.value === 'home') return 'home'
  if (mainTab.value === 'features') return 'features'
  if (mainTab.value === 'architectures') return 'architectures'
  if (mainTab.value === 'requirements') return 'requirements'
  if (mainTab.value === 'knowledge') return 'knowledge'
  if (mainTab.value === 'workflow' && workflow.value) return 'workflow'
  if (mainTab.value === 'workflow') return 'workflow-empty'
  return 'none'
})

function onSelectPlanNode(nodeId) {
  selectedPlanNodeId.value = nodeId || null
  topologySelectedNodeId.value = nodeId || null
}

function onTopologySelectNode(nodeId) {
  topologySelectedNodeId.value = nodeId || null
}

function resetWorkflowViewState() {
  selectedPlanNodeId.value = null
  topologySelectedNodeId.value = null
  planGraphPanelHeight.value = PLAN_GRAPH_DEFAULT_H
}

function toggleSidebarCollapsed() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, sidebarCollapsed.value ? '1' : '0')
}

function onSidebarHandleMouseDown(e) {
  if (sidebarCollapsed.value) return
  startResizeSidebar(e)
}

function startResizeSidebar(e) {
  const startX = e.clientX
  const startW = sidebarWidth.value
  sidebarResizing.value = true
  function onMove(moveE) {
    const delta = moveE.clientX - startX
    sidebarWidth.value = Math.round(
      Math.min(SIDEBAR_MAX_W, Math.max(SIDEBAR_MIN_W, startW + delta)),
    )
  }
  function onUp() {
    sidebarResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.classList.remove('split-dragging')
    localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth.value))
  }
  document.body.classList.add('split-dragging')
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function startResizePlanGraph(e) {
  const panel = planGraphPanelRef.value?.$el
  if (!panel) return
  const startY = e.clientY
  const startH = planGraphPanelHeight.value ?? PLAN_GRAPH_DEFAULT_H
  const card = workbenchMainRef.value
  const cardH = card?.getBoundingClientRect().height ?? 800
  const maxH = Math.max(PLAN_GRAPH_MIN_H, cardH - 220)
  function onMove(moveE) {
    const delta = moveE.clientY - startY
    planGraphPanelHeight.value = Math.round(
      Math.min(maxH, Math.max(PLAN_GRAPH_MIN_H, startH + delta)),
    )
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
  }
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'ns-resize'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function syncSubjectTypeWithTemplate() {
  const tpl = findTemplateById(workflowTemplates.value, defaultTemplateId.value)
  if (!tpl) return
  const type = resolveTemplateSubjectSchema(tpl).subject_type
  if (type && type !== selectedSubjectType.value) {
    selectedSubjectType.value = type
    localStorage.setItem(SUBJECT_TYPE_STORAGE_KEY, selectedSubjectType.value)
  }
}

function ensureTemplateMatchesSubjectType() {
  const list = filteredWorkflowTemplates.value
  if (!list.length) {
    defaultTemplateId.value = ''
    localStorage.removeItem(DEFAULT_TEMPLATE_STORAGE_KEY)
    return
  }
  if (!list.some((tpl) => tpl.template_id === defaultTemplateId.value)) {
    defaultTemplateId.value = list[0].template_id
    localStorage.setItem(DEFAULT_TEMPLATE_STORAGE_KEY, defaultTemplateId.value)
  }
}

async function loadWorkflowTemplates() {
  try {
    workflowTemplates.value = await listWorkflowTemplates()
    if (defaultTemplateId.value && !workflowTemplates.value.some((t) => t.template_id === defaultTemplateId.value)) {
      defaultTemplateId.value = ''
      localStorage.removeItem(DEFAULT_TEMPLATE_STORAGE_KEY)
    }
    if (!ALL_SUBJECT_TYPE_OPTIONS.some((opt) => opt.value === selectedSubjectType.value)) {
      selectedSubjectType.value = ALL_SUBJECT_TYPE_OPTIONS[0]?.value || SUBJECT_TYPE_IR
      localStorage.setItem(SUBJECT_TYPE_STORAGE_KEY, selectedSubjectType.value)
    }
    if (defaultTemplateId.value) {
      syncSubjectTypeWithTemplate()
    }
    ensureTemplateMatchesSubjectType()
    if (useWorkflow.value && !defaultTemplateId.value && filteredWorkflowTemplates.value.length) {
      defaultTemplateId.value = filteredWorkflowTemplates.value[0].template_id
      localStorage.setItem(DEFAULT_TEMPLATE_STORAGE_KEY, defaultTemplateId.value)
    }
    await refreshSubjectObjects()
  } catch {
    workflowTemplates.value = []
  }
}

function onSubjectTypeChange() {
  localStorage.setItem(SUBJECT_TYPE_STORAGE_KEY, selectedSubjectType.value)
  if (useWorkflow.value) {
    ensureTemplateMatchesSubjectType()
    onDefaultTemplateChange()
  } else {
    refreshSubjectObjects()
  }
}

function onDefaultTemplateChange() {
  if (defaultTemplateId.value) {
    localStorage.setItem(DEFAULT_TEMPLATE_STORAGE_KEY, defaultTemplateId.value)
    syncSubjectTypeWithTemplate()
  } else {
    localStorage.removeItem(DEFAULT_TEMPLATE_STORAGE_KEY)
  }
  refreshSubjectObjects()
}

function onUseWorkflowChange() {
  localStorage.setItem(PLAN_MODE_STORAGE_KEY, useWorkflow.value ? 'template' : 'dynamic')
}

async function loadAgents() {
  /* Agent 列表由注册页维护；Session 拓扑只读无需加载 */
}

async function refreshSubjectObjects() {
  const ws = workspacePath.value.trim()
  subjectObjectsError.value = ''
  if (!ws || !showSubjectObjectPanel.value) {
    subjectObjects.value = []
    return
  }
  subjectObjectsLoading.value = true
  try {
    const items = await listSubjectObjects(ws, activeSubjectType.value, useWorkflow.value ? defaultTemplateId.value : '')
    subjectObjects.value = items
    syncCheckedSubjectObjectIds(items)
  } catch (e) {
    subjectObjects.value = []
    const msg = e?.message || '加载对象列表失败'
    subjectObjectsError.value = msg === 'Not Found' ? '' : msg
  } finally {
    subjectObjectsLoading.value = false
  }
}

async function onWorkspaceChange() {
  const ws = workspacePath.value.trim()
  if (ws) {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, ws)
  } else {
    localStorage.removeItem(WORKSPACE_STORAGE_KEY)
  }
  selectedObjectId.value = ''
  workflowId.value = ''
  workflow.value = null
  graphSpec.value = null
  checkedSubjectObjectIds.value = []
  await refreshSubjectObjects()
}

function resolveTemplateLabel() {
  const tpl = workflowTemplates.value.find((t) => t.template_id === defaultTemplateId.value)
  return tpl?.name || defaultTemplateId.value
}

function buildOpenSubjectSessionPayload(item) {
  const ws = workspacePath.value.trim()
  const payload = {
    workspace_path: ws,
    subject_type: activeSubjectType.value,
    object_id: item.object_id,
    subject_id: item.subject_id || item.object_id,
    user_goal: item.summary || item.label || '',
    plan_mode: useWorkflow.value ? 'template' : 'dynamic',
    template_id: useWorkflow.value ? defaultTemplateId.value : '',
  }
  if (item.subject_refs && Object.keys(item.subject_refs).length) {
    payload.subject_refs = item.subject_refs
  }
  return payload
}

async function ensureSubjectObjectSession(item) {
  const ws = workspacePath.value.trim()
  if (!ws) throw new Error('请先填写 Workspace 路径')
  if (item.workflow_id) return item.workflow_id
  if (useWorkflow.value && !defaultTemplateId.value) {
    throw new Error('请先选择工作流模板')
  }
  const record = await openSubjectSession(buildOpenSubjectSessionPayload(item))
  return record.workflow_id
}

async function initSubjectObjectItem(item) {
  const wfId = await ensureSubjectObjectSession(item)
  if (useWorkflow.value && defaultTemplateId.value) {
    await initWorkflowFromTemplate(wfId, defaultTemplateId.value)
  }
  return wfId
}

function formatInitErrorMessage(error) {
  const msg = error?.message || '初始化失败'
  if (msg === 'Not Found') {
    return '初始化接口未就绪，请重启后端（start.py）后重试'
  }
  if (msg.includes('编排方式在创建 Session 时选定')) {
    return '后端版本过旧，请重启 start.py 以加载最新接口'
  }
  return msg
}

async function startSubjectObjectItem(item, wfId) {
  const id = wfId || item.workflow_id
  if (!id) throw new Error('无 Session')
  const latest = subjectObjects.value.find((row) => row.object_id === item.object_id) || item
  if (latest.running) throw new Error('已在执行中')
  const record = await getWorkflow(id)
  const snap = extractPlanGraphSnapshot(record.metadata)
  const planMode = record.plan_mode || (useWorkflow.value ? 'template' : 'dynamic')
  if (planMode === 'dynamic' && !(snap?.graphSpec?.nodes?.length)) {
    throw new Error('请先生成拓扑')
  }
  const phase = snap?.phase || 'idle'
  await executeWorkflow(id, { clear_history: phase === 'idle' || phase === 'done' })
  if (item.object_id === selectedObjectId.value) {
    await loadWorkflow(id)
  }
  return id
}

function reportBatchFailures(label, failures) {
  if (!failures.length) return
  alert(
    `${label}完成，${failures.length} 项失败：\n`
    + failures.map((row) => `${row.name}: ${row.message}`).join('\n'),
  )
}

async function runBatchSubjectObjectAction(label, handler, { confirmText } = {}) {
  const items = getCheckedSubjectObjects()
  if (!items.length || batchBusy.value) return
  if (confirmText && !window.confirm(confirmText)) return
  batchBusy.value = true
  const failures = []
  try {
    for (const item of items) {
      try {
        await handler(item)
      } catch (e) {
        failures.push({ name: item.label || item.object_id, message: formatInitErrorMessage(e) })
      }
    }
    await refreshSubjectObjects()
    reportBatchFailures(label, failures)
  } finally {
    batchBusy.value = false
  }
}

async function batchInitSubjectObjects() {
  const items = getCheckedSubjectObjects()
  if (!items.length) return
  if (useWorkflow.value && !defaultTemplateId.value) {
    alert('批量初始化请先选择工作流模板')
    return
  }
  const confirmText = useWorkflow.value
    ? `将对 ${items.length} 个对象用模板「${resolveTemplateLabel()}」初始化，已有 Session 会清空执行历史，是否继续？`
    : `将为 ${items.length} 个对象打开 Session（动态规划模式），是否继续？`
  await runBatchSubjectObjectAction('批量初始化', async (item) => {
    await initSubjectObjectItem(item)
  }, { confirmText })
}

async function batchStartSubjectObjects() {
  const items = getCheckedSubjectObjects()
  if (!items.length) return
  await runBatchSubjectObjectAction('批量启动', async (item) => {
    const wfId = await ensureSubjectObjectSession(item)
    await startSubjectObjectItem(item, wfId)
  }, {
    confirmText: `将启动 ${items.length} 个对象的工作流，是否继续？`,
  })
}

async function startSubjectObjectWorkflow(item) {
  const ws = workspacePath.value.trim()
  if (!ws || !item?.object_id || subjectStartId.value || subjectOpeningId.value || item.running || batchBusy.value) return
  if (!item.has_session) return
  subjectStartId.value = item.object_id
  try {
    if (item.object_id !== selectedObjectId.value || workflowId.value !== item.workflow_id) {
      await selectSubjectObject(item)
    }
    if (!workflowId.value) return
    if (executing.value || awaitingPending.value) {
      mainTab.value = 'workflow'
      alert(pendingStartBlockMessage())
      return
    }
    await startSubjectObjectItem(item, workflowId.value)
    await refreshSubjectObjects()
  } catch (e) {
    alert(e?.message || '启动失败')
  } finally {
    subjectStartId.value = ''
  }
}

async function initSubjectObjectFromTemplate(item) {
  const ws = workspacePath.value.trim()
  if (!ws || !defaultTemplateId.value || subjectInitId.value || batchBusy.value) return
  const tplLabel = resolveTemplateLabel()
  const ok = window.confirm(
    item.workflow_id
      ? `将用模板「${tplLabel}」重新初始化该对象的工作流，会清空执行历史、待确认状态与节点产出，是否继续？`
      : `将用模板「${tplLabel}」为该对象创建 Session，是否继续？`,
  )
  if (!ok) return
  subjectInitId.value = item.object_id
  try {
    const wfId = await initSubjectObjectItem(item)
    selectedObjectId.value = item.object_id
    mainTab.value = 'workflow'
    await loadWorkflow(wfId)
    await refreshSubjectObjects()
  } catch (e) {
    alert(formatInitErrorMessage(e))
  } finally {
    subjectInitId.value = ''
  }
}

async function selectSubjectObject(item, options = {}) {
  const ws = workspacePath.value.trim()
  if (!ws || !item?.object_id || subjectOpeningId.value) return
  const openingNew = !item.workflow_id
  if (openingNew && useWorkflow.value && !defaultTemplateId.value) {
    alert('新建 Session 请先选择工作流模板，或关闭「使用工作流模板」改用 AI 动态规划')
    return
  }
  selectedObjectId.value = item.object_id
  subjectOpeningId.value = item.object_id
  try {
    let record
    if (item.workflow_id) {
      record = await getWorkflow(item.workflow_id)
    } else {
      record = await openSubjectSession(buildOpenSubjectSessionPayload(item))
      await refreshSubjectObjects()
    }
    await loadWorkflow(record.workflow_id)
    if (options.switchToWorkflow) {
      mainTab.value = 'workflow'
    }
  } catch (e) {
    alert(e?.message || '打开 Session 失败')
  } finally {
    subjectOpeningId.value = ''
  }
}

async function stopSubjectObjectWorkflow(item) {
  const wfId = item?.workflow_id
  if (!wfId || subjectAbortId.value) return
  subjectAbortId.value = wfId
  try {
    await abortWorkflowById(wfId)
    await refreshSubjectObjects()
  } catch (e) {
    alert(e?.message || '停止失败')
  } finally {
    subjectAbortId.value = ''
  }
}

async function loadWorkflow(id) {
  const switchingSession = id !== workflowId.value
  workflowId.value = id
  workflow.value = await getWorkflow(id)
  if (switchingSession) {
    resetWorkflowViewState()
  }
  const matched = subjectObjects.value.find((row) => objectMatchesWorkflow(row, workflow.value))
  if (matched) {
    selectedObjectId.value = matched.object_id
  } else if (workflow.value.subject_id) {
    selectedObjectId.value = workflow.value.subject_id
  }
  const snap = extractPlanGraphSnapshot(workflow.value.metadata)
  form.workspace_path = workflow.value.workspace_path || workspacePath.value.trim()
  form.user_goal = workflow.value.user_goal || resolveSubjectObjectSummary() || ''
  form.judge_mode = workflow.value.judge_mode || ''
  graphSpec.value = snap?.graphSpec ? cloneGraphSpec(snap.graphSpec) : cloneGraphSpec(EMPTY_GRAPH)
}

async function refreshSubjectObjectStatus() {
  const ws = workspacePath.value.trim()
  if (!ws || !subjectObjects.value.length) return
  try {
    const latest = await listSubjectObjects(ws, activeSubjectType.value, useWorkflow.value ? defaultTemplateId.value : '')
    const byId = Object.fromEntries(latest.map((item) => [item.object_id, item]))
    subjectObjects.value = subjectObjects.value.map((item) => ({
      ...item,
      ...(byId[item.object_id] || {}),
    }))
  } catch {
    /* ignore transient errors */
  }
}

async function saveMeta() {
  if (!workflowId.value) return
  await updateWorkflow(workflowId.value, {
    workspace_path: workspacePath.value.trim() || form.workspace_path,
    user_goal: form.user_goal,
    judge_mode: isDynamicPlan.value ? (form.judge_mode || undefined) : undefined,
  })
  await loadWorkflow(workflowId.value)
}

async function onSessionSettingsSave(payload) {
  if (!workflowId.value || sessionSettingsSaving.value) return
  form.user_goal = payload?.user_goal || ''
  if (isDynamicPlan.value) {
    form.judge_mode = payload?.judge_mode || ''
  }
  sessionSettingsSaving.value = true
  try {
    await saveMeta()
    sessionSettingsVisible.value = false
  } catch (e) {
    alert(e?.message || '保存失败')
  } finally {
    sessionSettingsSaving.value = false
  }
}

async function onGenerateGraph() {
  if (!workflowId.value || generating.value) return
  generateGraphGoal.value = String(form.user_goal || '').trim() || resolveSubjectObjectSummary()
  generateGraphError.value = ''
  generateGraphVisible.value = true
  await nextTick()
  generateGoalInputRef.value?.focus()
}

function resolveSubjectObjectSummary() {
  const item = subjectObjects.value.find((r) => r.object_id === selectedObjectId.value)
  return String(item?.summary || form.user_goal || '').trim()
}

function closeGenerateGraphDialog() {
  generateGraphVisible.value = false
  generateGraphError.value = ''
}

async function confirmGenerateGraph() {
  const goal = String(generateGraphGoal.value || '').trim()
  if (!goal) {
    generateGraphError.value = '请填写任务目标'
    generateGoalInputRef.value?.focus()
    return
  }
  try {
    llmStatus.value = await getLlmStatus()
  } catch {
    llmStatus.value = { available: false }
  }
  if (!llmStatus.value?.available) {
    generateGraphError.value = 'LLM 未配置，请先打开右上角配置中的模型服务'
    return
  }
  form.user_goal = goal
  generateGraphError.value = ''
  await runGenerateGraph(goal)
  if (!generateGraphError.value) {
    closeGenerateGraphDialog()
  }
}

async function runGenerateGraph(goal) {
  if (!workflowId.value || generating.value) return
  generating.value = true
  generateGraphError.value = ''
  try {
    form.user_goal = goal
    await saveMeta()
    await generateGraph(workflowId.value, {
      user_goal: goal,
      recreate: true,
    })
    await loadWorkflow(workflowId.value)
  } catch (e) {
    const msg = e?.message || '生成失败'
    if (generateGraphVisible.value) {
      generateGraphError.value = msg
    } else {
      alert(msg)
    }
  } finally {
    generating.value = false
  }
}

async function onExecuteFromNode(nodeId) {
  if (!workflowId.value) return
  if (executeInFlight.value) {
    alert('工作流正在执行中，请稍候')
    return
  }
  if (!workspacePath.value.trim()) {
    alert('请先在左侧填写 Workspace 路径')
    return
  }
  const entry = graphSpec.value?.entry
  const isEntry = entry && nodeId === entry
  if (awaitingPending.value && !isEntry) {
    const ok = window.confirm(
      `${pendingStartBlockMessage()}\n\n若改为从步骤「${nodeId}」重新执行，将放弃当前待确认状态。是否继续？`,
    )
    if (!ok) return
  } else if (awaitingPending.value && isEntry) {
    alert(pendingStartBlockMessage())
    return
  }
  try {
    await executeWorkflow(workflowId.value, {
      start_node_id: isEntry ? null : nodeId,
      clear_history: Boolean(isEntry),
    })
    await loadWorkflow(workflowId.value)
    await refreshSubjectObjectStatus()
  } catch (e) {
    alert(e?.message || '执行失败')
  }
}

async function abortWorkflowById(wfId) {
  if (!wfId) return
  try {
    await abortWorkflow(wfId)
  } catch (e) {
    const msg = String(e?.message || '')
    if (!msg.includes('无进行中')) {
      throw e
    }
  }
  if (workflowId.value === wfId) {
    await loadWorkflow(wfId)
  }
  await refreshSubjectObjectStatus()
}

async function onAbort() {
  if (!workflowId.value || subjectAbortId.value) return
  subjectAbortId.value = workflowId.value
  try {
    await abortWorkflowById(workflowId.value)
  } catch (e) {
    alert(e?.message || '中止失败')
  } finally {
    subjectAbortId.value = ''
  }
}

async function onGateApprove(comment) {
  if (!workflowId.value || pendingBusy.value) return
  pendingBusy.value = true
  try {
    await gateApprove(workflowId.value, { comment: comment || '' })
    await loadWorkflow(workflowId.value)
  } catch (e) {
    alert(e?.message || '确认失败')
  } finally {
    pendingBusy.value = false
  }
}

async function onGateReject(comment) {
  if (!workflowId.value || pendingBusy.value) return
  if (!String(comment || '').trim()) {
    alert('驳回时请填写意见')
    return
  }
  pendingBusy.value = true
  try {
    await gateReject(workflowId.value, { comment: comment || '' })
    await loadWorkflow(workflowId.value)
  } catch (e) {
    alert(e?.message || '驳回失败')
  } finally {
    pendingBusy.value = false
  }
}

async function onExpandApply() {
  if (!workflowId.value || pendingBusy.value) return
  pendingBusy.value = true
  try {
    await expandApply(workflowId.value)
    await loadWorkflow(workflowId.value)
  } catch (e) {
    alert(e?.message || '任务分裂失败')
  } finally {
    pendingBusy.value = false
  }
}

async function onNodeRevise(feedback) {
  const nodeId = selectedPlanNodeId.value
  if (!workflowId.value || !nodeId || reviseBusy.value) return
  if (!workspacePath.value.trim()) {
    alert('请先在左侧填写 Workspace 路径')
    return
  }
  reviseBusy.value = true
  try {
    await reviseNode(workflowId.value, nodeId, { feedback })
    await loadWorkflow(workflowId.value)
  } catch (e) {
    alert(e?.message || '修正重跑失败')
  } finally {
    reviseBusy.value = false
  }
}

async function onChatSend(text) {
  const trimmed = String(text || '').trim()
  if (!trimmed || executing.value || !workflowId.value) return
  if (!workspacePath.value.trim()) {
    alert('请先在左侧填写 Workspace 路径')
    return
  }
  if (isDynamicPlan.value && !(graphSpec.value?.nodes?.length)) {
    alert('请先使用 AI 生成拓扑')
    return
  }
  selectedPlanNodeId.value = null
  topologySelectedNodeId.value = null
  try {
    const phase = snapshot.value?.phase || 'idle'
    const clearHistory = phase === 'idle' || phase === 'done'
    await executeWorkflow(workflowId.value, { clear_history: clearHistory })
    await loadWorkflow(workflowId.value)
  } catch (e) {
    alert(e?.message || '执行失败')
  }
}

async function onSettingsSaved() {
  try {
    llmStatus.value = await getLlmStatus()
  } catch {
    llmStatus.value = { available: false }
  }
}

async function refreshWorkflowSubjectStatus() {
  await refreshSubjectObjectStatus()
}

async function poll() {
  if (workflowId.value) {
    try {
      await loadWorkflow(workflowId.value)
    } catch {
      /* ignore transient errors */
    }
  }
  if (
    executing.value
    || awaitingPending.value
    || anySubjectObjectRunning.value
  ) {
    await refreshWorkflowSubjectStatus()
  }
}

function pollIntervalMs() {
  return (
    executing.value
    || awaitingPending.value
    || anySubjectObjectRunning.value
  ) ? 2000 : 8000
}

function schedulePoll() {
  pollTimer = setTimeout(async () => {
    await poll()
    schedulePoll()
  }, pollIntervalMs())
}

onMounted(async () => {
  try {
    llmStatus.value = await getLlmStatus()
  } catch {
    llmStatus.value = { available: false }
  }
  await loadAgents()
  await loadWorkflowTemplates()
  if (workspacePath.value.trim()) {
    await refreshSubjectObjects()
  }
  schedulePoll()
})

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style>
* { box-sizing: border-box; }
html, body, #app {
  height: 100%;
  margin: 0;
}
body {
  font-family: "Inter", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
  background: var(--pm-bg, #f4f6f8);
  color: var(--pm-text, #1a1a1a);
  -webkit-font-smoothing: antialiased;
}
input,
textarea,
select,
button {
  font-family: inherit;
}
body.split-dragging {
  cursor: col-resize;
  user-select: none;
}
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width, 280px) 6px 1fr;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}
.app-shell .sidebar {
  grid-column: 1;
  grid-row: 2;
  min-height: 0;
  min-width: 0;
}
.app-shell .sidebar-resize-handle {
  grid-column: 2;
  grid-row: 2;
}
.app-shell .main {
  grid-column: 3;
  grid-row: 2;
}
.app-shell:not(.full-width-mode) .main {
  min-height: 0;
}
.app-shell.full-width-mode {
  grid-template-columns: 1fr;
}
.app-shell.full-width-mode .main {
  grid-column: 1 / -1;
  grid-row: 2;
  min-height: 0;
}
.app-shell.sidebar-collapsed {
  grid-template-columns: 28px 1fr;
}
.app-shell.sidebar-collapsed .sidebar {
  display: none;
}
.app-shell.sidebar-collapsed .sidebar-resize-handle {
  grid-column: 1;
  cursor: default;
}
.app-shell.sidebar-collapsed .main {
  grid-column: 2;
}
.app-header {
  grid-column: 1 / -1;
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 24px;
  height: 60px;
  background: var(--pm-surface, #fff);
  border-bottom: 1px solid var(--pm-border, #e8eaed);
}
.header-start {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 0;
}
.header-end {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
  flex-shrink: 0;
}
.header-brand {
  justify-self: start;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--pm-primary, #00b894);
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  line-height: 1;
  flex-shrink: 0;
}
.header-brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
  white-space: nowrap;
  color: var(--pm-text);
}
.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.header-workspace {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding-right: 12px;
  border-right: 1px solid var(--pm-border);
}
.header-workspace-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--pm-text-secondary);
  white-space: nowrap;
}
.header-workspace-input {
  width: 300px;
  flex-shrink: 0;
  padding: 7px 10px;
  border: 1px solid var(--pm-border-strong);
  border-radius: var(--pm-radius);
  font-size: 12px;
  background: var(--pm-surface);
  color: var(--pm-text);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.header-workspace-input:focus {
  outline: none;
  border-color: var(--pm-primary);
  box-shadow: 0 0 0 3px var(--pm-primary-soft);
}
.header-workspace-input::placeholder {
  color: var(--pm-text-muted);
}
.header-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border: none;
  border-radius: var(--pm-radius);
  background: transparent;
  color: var(--pm-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s;
}
.nav-link .nav-icon {
  opacity: 0.7;
}
.nav-link:hover {
  color: var(--pm-text);
  background: var(--pm-surface-muted);
}
.nav-link.active {
  color: var(--pm-primary);
  font-weight: 600;
  background: var(--pm-primary-soft);
}
.nav-link.active .nav-icon {
  opacity: 1;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--pm-border-strong);
  border-radius: var(--pm-radius);
  background: var(--pm-surface);
  color: var(--pm-text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.icon-btn:hover {
  background: var(--pm-surface-muted);
  color: var(--pm-primary);
  border-color: var(--pm-primary-muted);
}
.btn-primary {
  background: var(--pm-primary, #1677ff);
  border-color: var(--pm-primary, #1677ff);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: var(--pm-primary-hover, #4096ff);
  border-color: var(--pm-primary-hover, #4096ff);
}
.header-actions .btn-group {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 14px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
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
.sidebar {
  background: #fff;
  padding: 12px;
  overflow: auto;
}
.sidebar-resize-handle {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: col-resize;
  touch-action: none;
  background: #fff;
  border-right: 1px solid #dadce0;
}
.sidebar-resize-handle.collapsed {
  cursor: default;
}
.sidebar-resize-handle:hover:not(.collapsed),
.sidebar-resize-handle.dragging {
  background: var(--pm-primary-soft);
}
.sidebar-collapse-btn {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--pm-border-strong, #dadce0);
  border-radius: 6px;
  background: #fff;
  color: #5f6368;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.sidebar-collapse-btn:hover {
  background: var(--pm-surface-muted, #f1f3f4);
  color: var(--pm-primary, #00b894);
  border-color: var(--pm-primary-muted, #80cbc4);
}
.sidebar-resize-handle.collapsed .sidebar-collapse-btn {
  width: 24px;
  height: 48px;
}
.sidebar-resize-handle-bar {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 3px;
  height: 48px;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background: var(--pm-primary-muted);
  transition: background 0.15s, height 0.15s;
}
.sidebar-resize-handle:hover .sidebar-resize-handle-bar,
.sidebar-resize-handle.dragging .sidebar-resize-handle-bar {
  height: 64px;
  background: var(--pm-primary);
}
.sidebar-section + .sidebar-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f1f3f4;
}
.sidebar h2 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #5f6368;
}
.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.sidebar-head h2 {
  margin: 0;
}
.workspace-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  font-size: 12px;
}
.sidebar-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: #80868b;
  line-height: 1.4;
}
.sidebar-hint code {
  font-size: 10px;
}
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.switch-label {
  font-size: 13px;
  font-weight: 600;
  color: #3c4043;
}
.template-select {
  margin-top: 4px;
}
.toggle {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
  cursor: pointer;
}
.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-track {
  position: relative;
  display: block;
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: #dadce0;
  transition: background 0.2s;
}
.toggle-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s;
}
.toggle-input:checked + .toggle-track {
  background: var(--pm-primary);
}
.toggle-input:checked + .toggle-track::after {
  transform: translateX(16px);
}
.toggle-input:focus-visible + .toggle-track {
  box-shadow: 0 0 0 2px #e8f0fe;
}
.sidebar-error {
  margin: 0;
  font-size: 12px;
  color: #c5221f;
  line-height: 1.4;
}
.sidebar-empty {
  margin: 8px 0 0;
  font-size: 12px;
  color: #80868b;
}
.req-list-hint {
  margin: 10px 0 0;
}
.sidebar-subject-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #5f6368;
}
.workspace-subject-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #e8eaed;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}
.workspace-subject-card:hover {
  background: #f8f9fa;
}
.workspace-subject-card.active {
  border-color: #90caf9;
  background: #e3f2fd;
}
.workspace-subject-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.workspace-subject-name {
  font-size: 13px;
  font-weight: 600;
  color: #202124;
}
.workspace-subject-path {
  font-size: 11px;
  color: #80868b;
  word-break: break-all;
}
.btn-small {
  padding: 4px 10px;
  font-size: 12px;
}
.req-batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e8eaed;
}
.req-select-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #5f6368;
  cursor: pointer;
  user-select: none;
}
.req-select-all input {
  margin: 0;
  cursor: pointer;
}
.req-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.req-list li {
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(78px, max-content);
  column-gap: 8px;
  align-items: start;
  border: 1px solid transparent;
}
.req-list li.checked {
  background: #fafbfc;
}
.req-check {
  display: inline-flex;
  align-items: flex-start;
  padding-top: 2px;
  flex-shrink: 0;
  cursor: pointer;
  grid-column: 1;
}
.req-check input {
  margin: 0;
  cursor: pointer;
}
.req-list li:hover { background: #f8f9fa; }
.req-list li.active {
  background: var(--pm-primary-soft);
  border-color: var(--pm-primary-muted);
}
.req-main {
  min-width: 0;
  grid-column: 2;
  overflow: hidden;
}
.req-name {
  display: block;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.req-summary {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: #80868b;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.req-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
  grid-column: 3;
  position: relative;
  z-index: 2;
  min-width: max-content;
  padding-left: 4px;
}
.req-list li.active .req-badges {
  background: var(--pm-primary-soft);
}
.req-actions {
  display: grid;
  grid-template-columns: 22px max-content;
  align-items: center;
  gap: 4px 6px;
  flex-shrink: 0;
}
.req-actions .btn-play {
  grid-column: 1;
  grid-row: 1;
}
.req-actions .btn-init {
  grid-column: 2;
  grid-row: 1;
}
.req-actions .btn-stop {
  grid-column: 1 / -1;
}
.btn-play {
  width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--pm-primary-muted);
  background: var(--pm-primary-soft);
  color: var(--pm-primary-hover);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.btn-play:hover:not(:disabled) {
  background: var(--pm-primary-muted);
}
.btn-play:disabled {
  opacity: 0.45;
  cursor: default;
}
.play-icon {
  width: 10px;
  height: 10px;
  margin-left: 1px;
}
.req-tag {
  font-size: 10px;
  color: #5f6368;
  background: #f1f3f4;
  padding: 2px 6px;
  border-radius: 999px;
}
.req-tag-pending {
  color: #e65100;
  background: #fff8e1;
}
.btn-init {
  padding: 2px 8px;
  font-size: 10px;
  line-height: 1.4;
  border-radius: 999px;
  border: 1px solid var(--pm-primary-muted);
  background: var(--pm-primary-soft);
  color: var(--pm-primary-hover);
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
}
.btn-init:hover:not(:disabled) {
  background: var(--pm-primary-muted);
}
.btn-init:disabled {
  opacity: 0.6;
  cursor: default;
}
.wf-badge {
  font-size: 10px;
  color: #1565c0;
  background: #e3f2fd;
  padding: 2px 6px;
  border-radius: 999px;
}
.btn-stop {
  padding: 2px 8px;
  font-size: 10px;
  line-height: 1.4;
  border-radius: 999px;
  border: 1px solid #ef9a9a;
  background: #ffebee;
  color: #c62828;
  cursor: pointer;
}
.btn-stop:hover:not(:disabled) {
  background: #ffcdd2;
}
.btn-stop:disabled {
  opacity: 0.6;
  cursor: default;
}
.main {
  padding: 16px;
  overflow: auto;
  min-height: 0;
}
.main.workspace-main {
  padding: 0;
  overflow: hidden;
}
.main.page-main {
  padding: 0;
  overflow: auto;
  background: var(--pm-bg);
}
.main.canvas-main {
  padding: 0;
  overflow: hidden;
  background: var(--pm-bg);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.nav-link-home {
  padding: 8px 10px;
}
.nav-link-home .nav-icon {
  margin: 0;
}
.workflow-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 0;
}
.workbench-main {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--pm-surface, #fff);
  overflow: hidden;
}
.workbench-pending {
  flex-shrink: 0;
}
.workbench-pending :deep(.pending-panel) {
  margin: 0;
}
.workbench-main :deep(.plan-graph-panel) {
  flex-shrink: 0;
  border: none;
  border-radius: 0;
}
.plan-graph-resize-handle {
  flex-shrink: 0;
  height: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ns-resize;
  background: #eef4fd;
  border-bottom: 1px solid rgba(22, 119, 255, 0.15);
  color: #9eb4c8;
  transition: color 0.15s, background 0.15s;
}
.plan-graph-resize-handle:hover {
  color: var(--pm-primary, #1677ff);
  background: rgba(22, 119, 255, 0.08);
}
.plan-graph-resize-handle-bar {
  display: block;
  width: 48px;
  height: 2px;
  border-radius: 2px;
  background: currentColor;
  opacity: 0.85;
}
.empty-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #80868b;
  font-size: 14px;
}
.workspace-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.workspace-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.workspace-top {
  flex-shrink: 0;
}
.workspace-bottom {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
  align-items: stretch;
}
.split-pane {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.split-pane-left {
  flex-shrink: 0;
}
.split-pane-right {
  flex: 1;
}
.split-resizer {
  position: relative;
  flex-shrink: 0;
  width: 8px;
  margin: 0 -2px;
  cursor: col-resize;
  touch-action: none;
  z-index: 2;
}
.split-resizer::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  transform: translateX(-50%);
  background: #dadce0;
  transition: background 0.15s, width 0.15s;
}
.split-resizer:hover::after,
.split-resizer.dragging::after {
  width: 3px;
  background: #1a73e8;
}
@media (max-width: 1100px) {
  .workspace-bottom {
    flex-direction: column;
  }
  .split-pane-left {
    width: auto !important;
    min-height: 240px;
  }
  .split-resizer {
    display: none;
  }
  .workspace-main {
    overflow: auto;
  }
}
.meta-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  background: #fff;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #dadce0;
}
.meta-bar label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #5f6368;
}
.meta-bar input {
  min-width: 200px;
  padding: 6px 8px;
  border: 1px solid #dadce0;
  border-radius: 4px;
}
.meta-bar input.readonly {
  background: #f8f9fa;
  color: #5f6368;
}
.meta-bar input.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.meta-bar select {
  min-width: 200px;
  padding: 6px 8px;
  border: 1px solid #dadce0;
  border-radius: 4px;
  background: #fff;
}
.meta-bar label.meta-goal {
  flex: 1 1 100%;
  min-width: 100%;
}
.meta-bar textarea.meta-goal-input {
  width: 100%;
  box-sizing: border-box;
  padding: 6px 8px;
  border: 1px solid #dadce0;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  min-height: 52px;
}
.dialog-wide {
  width: min(560px, 100%);
}
.dialog-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: #5f6368;
  line-height: 1.5;
}
.dialog-warn {
  margin: 0 0 12px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fef7e0;
  border: 1px solid #f9ab00;
  color: #b06000;
  font-size: 13px;
  line-height: 1.5;
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
.dialog-card {
  width: min(420px, 100%);
  background: #fff;
  border-radius: 12px;
  padding: 18px;
}
.dialog-card h3 {
  margin: 0 0 12px;
  font-size: 16px;
}
.dialog-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #5f6368;
}
.dialog-field input,
.dialog-field textarea {
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 13px;
}
.dialog-error {
  margin: 0 0 8px;
  color: #c5221f;
  font-size: 13px;
}
.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
