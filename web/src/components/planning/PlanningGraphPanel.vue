<template>
  <div
    v-if="graphSpec"
    class="plan-graph-panel"
    :class="{ 'edit-mode': editable, 'fill-height': fillHeight }"
  >
    <header class="plan-graph-toolbar">
      <div class="plan-graph-toolbar-inner">
        <span class="legend-group" aria-label="连线说明">
          <span class="legend-item"><i class="legend-line always" />顺序</span>
          <span class="legend-item"><i class="legend-line pass" />通过</span>
          <span class="legend-item"><i class="legend-line reject" />驳回返工（0次）</span>
          <span class="legend-item"><i class="legend-line reject-fired" />已驳回（≥1次）</span>
        </span>
        <span class="legend-sep" aria-hidden="true" />
        <span class="legend-group" aria-label="节点类型">
          <span class="legend-item"><i class="legend-shape ai-execute" />AI执行类</span>
          <span class="legend-item"><i class="legend-shape ai-check" />AI检查类</span>
          <span class="legend-item"><i class="legend-shape human-gate" />人工卡点类</span>
          <span class="legend-item"><i class="legend-shape expand-gate" />扩展类</span>
          <span class="legend-item"><i class="legend-shape fork-gate" />分支汇聚类</span>
        </span>
        <span class="legend-sep" aria-hidden="true" />
        <span class="legend-group" aria-label="节点状态">
          <span class="legend-item"><i class="legend-dot pending" />未启动</span>
          <span class="legend-item"><i class="legend-dot running" />执行中</span>
          <span class="legend-item"><i class="legend-dot done" />已完成</span>
        </span>
        <template v-if="editable">
          <span class="legend-sep" aria-hidden="true" />
          <span class="plan-graph-edit-hint">{{ editModeHint }}</span>
          <button
            v-if="topologySelectedNodeId"
            type="button"
            class="plan-graph-action plan-graph-action-danger"
            @click="onDeleteSelected"
          >
            删除节点
          </button>
          <button
            v-if="topologySelectedNodeId"
            type="button"
            class="plan-graph-action"
            @click="onEditSelected"
          >
            编辑节点
          </button>
        </template>
        <button
          v-if="selectedNodeId"
          type="button"
          class="plan-graph-back plan-graph-back-solo"
          @click="$emit('select-node', null)"
        >
          返回编排视图
        </button>
      </div>
      <button
        v-if="showSettingsButton"
        type="button"
        class="plan-graph-settings-btn"
        title="Session 配置"
        aria-label="Session 配置"
        @click="$emit('open-settings')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            fill="currentColor"
            d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81a.488.488 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.49.49 0 0 0-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z"
          />
        </svg>
      </button>
      <div v-else-if="$slots['toolbar-trailing']" class="plan-graph-toolbar-slot">
        <slot name="toolbar-trailing" />
      </div>
    </header>
    <div
      ref="viewportRef"
      class="plan-graph-viewport"
      :style="viewportStyle"
    >
      <div class="plan-graph-viewport-inner">
        <svg
          class="plan-graph-svg"
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          :width="layout.width"
          :height="layout.height"
          :preserveAspectRatio="svgPreserveAspectRatio"
        >
        <defs>
          <marker id="plan-arrow" markerWidth="9" markerHeight="9" refX="8" refY="3.5" orient="auto">
            <path d="M0,0 L8,3.5 L0,7 Z" fill="#7a8699" />
          </marker>
          <marker id="plan-arrow-pass" markerWidth="9" markerHeight="9" refX="8" refY="3.5" orient="auto">
            <path d="M0,0 L8,3.5 L0,7 Z" fill="#34a853" />
          </marker>
          <marker id="plan-arrow-reject" markerWidth="9" markerHeight="9" refX="8" refY="3.5" orient="auto">
            <path d="M0,0 L8,3.5 L0,7 Z" fill="#ea4335" />
          </marker>
          <marker id="plan-arrow-reject-fired" markerWidth="9" markerHeight="9" refX="8" refY="3.5" orient="auto">
            <path d="M0,0 L8,3.5 L0,7 Z" fill="#c5221f" />
          </marker>
        </defs>
        <g v-for="(group, gi) in layout.phaseGroups" :key="'phase-' + gi" class="plan-graph-phase-group">
          <rect
            :x="group.x"
            :y="group.y"
            :width="group.w"
            :height="group.h"
            rx="10"
            ry="10"
            class="plan-graph-phase-box"
          />
          <text
            :x="group.labelX"
            :y="group.labelY"
            class="plan-graph-phase-label"
          >{{ group.phase }}</text>
        </g>
        <g v-for="(edge, ei) in displayEdges" :key="'e-' + ei">
          <title v-if="edge.tooltip">{{ edge.tooltip }}</title>
          <path
            :d="edge.path"
            class="plan-graph-edge-hit"
            :class="{ 'edge-readonly': !editable }"
            @click.stop="onEdgeClick(edge)"
          />
          <path
            :d="edge.path"
            class="plan-graph-edge"
            :class="edgeEdgeClass(edge)"
            :marker-end="edgeMarker(edge)"
            :pointer-events="'none'"
          />
          <text
            v-if="edge.displayLabel"
            :x="edge.labelX"
            :y="edge.labelY"
            class="plan-graph-edge-label"
            :class="edgeLabelClass(edge)"
          >{{ edge.displayLabel }}</text>
        </g>
        <g
          v-for="node in layout.nodes"
          :key="node.id"
          class="plan-graph-node-wrap"
          :class="[nodeStateClass(node.id), nodeVisualClass(node)]"
          @click="onNodeClick(node.id)"
          @dblclick.stop="onNodeDblClick(node.id)"
        >
          <title>{{ nodeTooltip(node) }}</title>
          <polygon
            v-if="node.visualType === 'human_gate'"
            :points="nodeDiamondPoints(node)"
            class="plan-graph-node-shape plan-graph-node-diamond"
          />
          <polygon
            v-else-if="node.visualType === 'ai_check'"
            :points="nodeHexPoints(node)"
            class="plan-graph-node-shape plan-graph-node-hex"
          />
          <template v-else-if="node.visualType === 'expand_gate'">
            <polygon
              :points="nodeExpandTrapezoidPoints(node)"
              class="plan-graph-node-shape plan-graph-node-trapezoid plan-graph-node-gate"
            />
          </template>
          <polygon
            v-else-if="node.visualType === 'fork_gate'"
            :points="nodeForkTrapezoidPoints(node)"
            class="plan-graph-node-shape plan-graph-node-trapezoid plan-graph-node-gate"
          />
          <rect
            v-else
            :x="node.x"
            :y="node.y"
            :width="node.w"
            :height="node.h"
            rx="8"
            ry="8"
            class="plan-graph-node-shape plan-graph-node-rect"
          />
          <circle
            :cx="node.statusDot.cx"
            :cy="node.statusDot.cy"
            :r="node.statusDot.r"
            :fill="statusDotColor(node.id)"
            class="plan-graph-status-dot"
            :class="nodeStatus(node.id).status"
            pointer-events="none"
          />
          <g v-if="nodeIterationCount(node.id) > 1">
            <rect
              :x="node.x + node.w - 22"
              :y="node.y + 4"
              width="18"
              height="12"
              rx="6"
              ry="6"
              class="plan-graph-retry-badge"
            />
            <text
              :x="node.x + node.w - 13"
              :y="node.y + 11"
              class="plan-graph-retry-text"
            >×{{ nodeIterationCount(node.id) }}</text>
          </g>
          <text
            :x="node.cx"
            :y="node.labelY"
            class="plan-graph-node-label"
            dominant-baseline="middle"
          >
            <tspan
              v-for="(line, li) in node.labelLines"
              :key="li"
              :x="node.cx"
              :dy="li === 0 ? 0 : node.labelLineDy"
            >{{ line }}</tspan>
          </text>
          <text :x="node.cx" :y="node.agentY" class="plan-graph-node-agent">{{ node.agentType }}</text>
        </g>
        <template v-if="editable || showExecuteButton">
          <g
            v-for="node in layout.nodes"
            :key="'actions-' + node.id"
            class="plan-graph-node-actions"
          >
          <g
            v-if="editable"
            class="plan-graph-node-edit"
            :transform="nodeActionTransform(node, 'edit')"
            @mousedown.stop.prevent
            @click.stop="onEditNodeClick(node.id)"
          >
            <title>编辑节点配置</title>
            <rect :width="ACTION_BTN_SIZE" :height="ACTION_BTN_SIZE" fill="transparent" />
            <path
              class="plan-graph-action-icon plan-graph-edit-btn-icon"
              :transform="ACTION_ICON_TRANSFORM"
              d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z"
            />
          </g>
          <g
            v-if="showExecuteButton"
            class="plan-graph-node-run"
            :class="{ disabled: executionDisabled }"
            :transform="nodeActionTransform(node, 'run')"
            @mousedown.stop.prevent
            @click.stop="onExecuteNodeClick(node.id)"
          >
            <title>{{ executeNodeTitle(node.id) }}</title>
            <rect :width="ACTION_BTN_SIZE" :height="ACTION_BTN_SIZE" fill="transparent" />
            <path
              class="plan-graph-action-icon plan-graph-run-btn-icon"
              :transform="ACTION_ICON_TRANSFORM"
              d="M8 5v14l11-7z"
            />
          </g>
          <g
            v-if="editable"
            class="plan-graph-node-add"
            :transform="nodeActionTransform(node, 'add')"
            @mousedown.stop.prevent
            @click.stop="onOpenAddMenu(node.id)"
          >
            <title>添加下游节点或出边</title>
            <rect :width="ACTION_BTN_SIZE" :height="ACTION_BTN_SIZE" fill="transparent" />
            <path
              class="plan-graph-action-icon plan-graph-add-btn-icon"
              :transform="ACTION_ICON_TRANSFORM"
              d="M10 6 H14 V10 H18 V14 H14 V18 H10 V14 H6 V10 H10 V6 Z"
            />
          </g>
          </g>
        </template>
      </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { buildPlanGraphLayout } from '../../utils/planGraphLayout.js'
import {
  resolvePlanNodeStatus,
  resolveNodeIterationCount,
  resolveRejectEdgeDisplay,
  buildPlanNodeTooltip,
  isGraphEntryNode,
} from '../../utils/planGraphState.js'
import { NODE_ROLE_LABELS } from '../../utils/planGraphEdit.js'
import { NODE_VISUAL_LABELS } from '../../utils/planGraphState.js'

const props = defineProps({
  graphSpec: { type: Object, default: null },
  runningNodeIds: { type: Array, default: () => [] },
  selectedNodeId: { type: String, default: null },
  nodeSessionIds: { type: Object, default: () => ({}) },
  completedNodeIds: { type: Array, default: () => [] },
  nodeIterations: { type: Object, default: () => ({}) },
  preNodeRejectInfos: { type: Object, default: () => ({}) },
  phase: { type: String, default: 'idle' },
  topologySelectedNodeId: { type: String, default: null },
  executionDisabled: { type: Boolean, default: false },
  panelHeight: { type: Number, default: null },
  fillHeight: { type: Boolean, default: false },
  editable: { type: Boolean, default: true },
  layoutSize: { type: String, default: 'default' },
  showExecuteButton: { type: Boolean, default: true },
  showSettingsButton: { type: Boolean, default: false },
})

const emit = defineEmits([
  'select-node',
  'edit-node',
  'topology-select-node',
  'edit-edge',
  'open-add-menu',
  'delete-node',
  'execute-node',
  'open-settings',
])

const ACTION_BTN_SIZE = 20
const ACTION_BTN_GAP = 4
const ACTION_ICON_SIZE = 14
const ACTION_ICON_OFFSET = (ACTION_BTN_SIZE - ACTION_ICON_SIZE) / 2
const ACTION_ICON_SCALE = ACTION_ICON_SIZE / 24
const ACTION_ICON_TRANSFORM = `translate(${ACTION_ICON_OFFSET}, ${ACTION_ICON_OFFSET}) scale(${ACTION_ICON_SCALE})`
const ACTION_INSET_BOTTOM = 5

function actionRowY(node) {
  const base = node.y + node.h - ACTION_INSET_BOTTOM - ACTION_BTN_SIZE
  const type = node.visualType || 'ai_execute'
  if (type === 'ai_check' || type === 'human_gate') return base - 4
  return base
}

function actionSlotIndex(kind) {
  let idx = 0
  if (kind === 'edit') return 0
  if (kind === 'run') {
    return props.editable ? 1 : 0
  }
  return (props.editable ? 1 : 0) + (props.showExecuteButton ? 1 : 0)
}

function actionSlotCount() {
  let count = 0
  if (props.editable) count += 1
  if (props.showExecuteButton) count += 1
  if (props.editable) count += 1
  return count
}

function nodeActionTransform(node, kind) {
  const yBottom = actionRowY(node)
  const slotCount = actionSlotCount()
  const slotIndex = actionSlotIndex(kind)
  const groupW = slotCount * ACTION_BTN_SIZE + Math.max(0, slotCount - 1) * ACTION_BTN_GAP
  const startX = node.x + node.w / 2 - groupW / 2
  const x = startX + slotIndex * (ACTION_BTN_SIZE + ACTION_BTN_GAP)
  return `translate(${x}, ${yBottom})`
}

const editModeHint = computed(() => (
  props.showExecuteButton
    ? '点击节点选中 · 下方可修正重跑 · 连线编辑 · ▶ 执行 · + 添加'
    : '点击节点选中 · 连线编辑 · 编辑 · + 添加'
))

const layout = computed(() => buildPlanGraphLayout(
  props.graphSpec,
  { size: props.layoutSize },
))
const viewportRef = ref(null)
let viewportObserver = null

function syncViewportSize() {
  centerViewportScroll()
}

function centerViewportScroll() {
  const el = viewportRef.value
  if (!el || !props.fillHeight) return
  requestAnimationFrame(() => {
    el.scrollLeft = Math.max(0, (el.scrollWidth - el.clientWidth) / 2)
    el.scrollTop = Math.max(0, (el.scrollHeight - el.clientHeight) / 2)
  })
}

function bindViewportObserver() {
  viewportObserver?.disconnect()
  viewportObserver = null
  if (!props.fillHeight || !viewportRef.value) return
  syncViewportSize()
  viewportObserver = new ResizeObserver(syncViewportSize)
  viewportObserver.observe(viewportRef.value)
}

onMounted(() => {
  if (props.fillHeight) bindViewportObserver()
})

onBeforeUnmount(() => {
  viewportObserver?.disconnect()
})

watch(
  () => props.fillHeight,
  (enabled) => {
    if (enabled) nextTick(bindViewportObserver)
    else viewportObserver?.disconnect()
  },
)

watch(
  () => layout.value.width,
  () => {
    if (props.fillHeight) nextTick(centerViewportScroll)
  },
)

watch(
  () => layout.value.height,
  () => {
    if (props.fillHeight) nextTick(centerViewportScroll)
  },
)

const viewportStyle = computed(() => {
  if (props.fillHeight) {
    return {
      flex: '1',
      minHeight: '0',
      overflow: 'auto',
    }
  }
  const contentH = layout.value.height + 12
  if (props.panelHeight != null) {
    const h = Math.min(contentH, props.panelHeight)
    return {
      height: `${h}px`,
      maxHeight: `${props.panelHeight}px`,
      overflowY: contentH > props.panelHeight ? 'auto' : 'hidden',
      overflowX: 'auto',
    }
  }
  return {
    height: `${contentH}px`,
    maxHeight: `${contentH}px`,
    overflowY: 'hidden',
    overflowX: 'auto',
  }
})

const svgPreserveAspectRatio = computed(() => (
  props.panelHeight != null ? 'xMinYMin meet' : 'xMidYMid meet'
))

const statusSnapshot = computed(() => ({
  runningNodeIds: props.runningNodeIds || [],
  completedNodeIds: props.completedNodeIds || [],
}))

const displayEdges = computed(() => layout.value.edges.map((edge) => {
  const rejectDisplay = resolveRejectEdgeDisplay(
    edge.fromId,
    edge.toId,
    edge.condition,
    props.nodeIterations,
    props.preNodeRejectInfos,
    props.graphSpec,
    props.completedNodeIds,
  )
  return {
    ...edge,
    displayLabel: edge.condition === 'reject' ? rejectDisplay.label : edge.label,
    active: rejectDisplay.active,
    tooltip: edge.condition === 'reject' ? rejectDisplay.tooltip : '',
  }
}))

function nodeStatus(nodeId) {
  return resolvePlanNodeStatus(nodeId, statusSnapshot.value)
}

function statusDotColor(nodeId) {
  const { status } = nodeStatus(nodeId)
  if (status === 'running') return '#f9ab00'
  if (status === 'done') return '#34a853'
  return '#9aa0a6'
}

function nodeIterationCount(nodeId) {
  return resolveNodeIterationCount(nodeId, props.nodeIterations)
}

function nodeDiamondPoints(node) {
  const cx = node.x + node.w / 2
  const cy = node.y + node.h / 2
  return `${cx},${node.y} ${node.x + node.w},${cy} ${cx},${node.y + node.h} ${node.x},${cy}`
}

function nodeHexPoints(node) {
  const { x, y, w, h } = node
  return `${x + w * 0.25},${y} ${x + w * 0.75},${y} ${x + w},${y + h / 2} ${x + w * 0.75},${y + h} ${x + w * 0.25},${y + h} ${x},${y + h / 2}`
}

function nodeExpandTrapezoidPoints(node) {
  const { x, y, w, h } = node
  const inset = w * 0.14
  return `${x + inset},${y} ${x + w - inset},${y} ${x + w},${y + h} ${x},${y + h}`
}

function nodeForkTrapezoidPoints(node) {
  const { x, y, w, h } = node
  const inset = w * 0.14
  return `${x},${y} ${x + w},${y} ${x + w - inset},${y + h} ${x + inset},${y + h}`
}

function nodeVisualClass(node) {
  const type = node.visualType || 'ai_execute'
  return {
    'role-ai-execute': type === 'ai_execute',
    'role-ai-check': type === 'ai_check',
    'role-human-gate': type === 'human_gate',
    'role-expand-gate': type === 'expand_gate',
    'role-fork-gate': type === 'fork_gate',
  }
}

function nodeTooltip(node) {
  const type = node.visualType || 'ai_execute'
  const roleLabel = NODE_VISUAL_LABELS[type] || NODE_ROLE_LABELS.execute
  const base = buildPlanNodeTooltip(node.fullLabel, node.id, props.preNodeRejectInfos)
  const runHint = props.executionDisabled
    ? '执行中，请稍候'
    : isEntryNode(node.id)
      ? '底部 ▶ 从头执行编排'
      : '底部 ▶ 从此步骤开始执行'
  if (!props.editable) {
    return `${base}\n类型：${roleLabel}\n\n${runHint}\n单击选中并查看步骤会话`
  }
  return `${base}\n类型：${roleLabel}\n\n${runHint}\n单击选中并查看步骤会话 · 左下笔编辑 · 中下 ▶ 执行 · 右下 + 添加 · 点击连线编辑`
}

function isEntryNode(nodeId) {
  return isGraphEntryNode(props.graphSpec, nodeId)
}

function executeNodeTitle(nodeId) {
  if (props.executionDisabled) {
    return props.phase === 'executing' && (props.runningNodeIds || []).length > 0
      ? '编排执行中，请稍候'
      : '消息发送中，请稍候'
  }
  return isEntryNode(nodeId) ? '从头执行编排' : '从此步骤开始执行'
}

function onExecuteNodeClick(nodeId) {
  if (!nodeId) return
  if (props.executionDisabled) {
    window.alert('工作流正在执行中，请稍候')
    return
  }
  emit('execute-node', nodeId)
}

function onNodeClick(nodeId) {
  emit('topology-select-node', nodeId)
  emit('select-node', nodeId)
}

function onNodeDblClick(nodeId) {
  emit('topology-select-node', nodeId)
  emit('select-node', nodeId)
}

function onEdgeClick(edge) {
  if (!props.editable) return
  emit('edit-edge', {
    from: edge.fromId,
    to: edge.toId,
    condition: edge.condition || 'always',
  })
}

function onOpenAddMenu(nodeId) {
  if (!props.editable || !nodeId) return
  emit('open-add-menu', nodeId)
}

function onDeleteSelected() {
  if (!props.topologySelectedNodeId) return
  emit('delete-node', props.topologySelectedNodeId)
}

function onEditSelected() {
  if (!props.topologySelectedNodeId) return
  onEditNodeClick(props.topologySelectedNodeId)
}

function onEditNodeClick(nodeId) {
  if (!props.editable || !nodeId) return
  emit('edit-node', nodeId)
}

function nodeStateClass(nodeId) {
  const { status } = nodeStatus(nodeId)
  const selected = props.topologySelectedNodeId === nodeId
    || props.selectedNodeId === nodeId
  const hasSession = Boolean(props.nodeSessionIds?.[nodeId])
  const reworked = nodeIterationCount(nodeId) > 1
  return {
    [status]: true,
    running: status === 'running',
    executed: status === 'done',
    pending: status === 'pending',
    reworked,
    selected,
    clickable: hasSession || status !== 'pending',
  }
}

function edgeEdgeClass(edge) {
  return [
    edge.condition,
    { 'reject-back': edge.backward },
    { 'reject-fired': edge.condition === 'reject' && edge.active },
    { 'reject-idle': edge.condition === 'reject' && !edge.active },
  ]
}

function edgeLabelClass(edge) {
  return [
    edge.condition,
    { 'reject-fired': edge.condition === 'reject' && edge.active },
    { 'reject-idle': edge.condition === 'reject' && !edge.active },
  ]
}

function edgeMarker(edge) {
  if (edge.condition === 'pass') return 'url(#plan-arrow-pass)'
  if (edge.condition === 'reject' || edge.backward) {
    return edge.active ? 'url(#plan-arrow-reject-fired)' : 'url(#plan-arrow-reject)'
  }
  return 'url(#plan-arrow)'
}
</script>

<style scoped>
.plan-graph-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.plan-graph-panel.edit-mode {
  background: #eef4fd;
  border-bottom-color: #1a73e8;
  box-shadow: inset 0 3px 0 #1a73e8;
}
.plan-graph-panel.fill-height {
  flex: 1;
  min-height: 0;
  height: 100%;
  flex-shrink: 1;
  border-bottom: none;
}
.plan-graph-panel.fill-height .plan-graph-viewport {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.plan-graph-panel.fill-height .plan-graph-viewport-inner {
  flex-shrink: 0;
  margin: auto;
}
.plan-graph-toolbar {
  position: relative;
  flex-shrink: 0;
  padding: 8px 44px 8px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
}
.plan-graph-toolbar-inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 8px 12px;
  width: 100%;
  box-sizing: border-box;
}
.plan-graph-toolbar-slot,
.plan-graph-settings-btn {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
}
.plan-graph-settings-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--pm-border, #ebebeb);
  border-radius: 6px;
  background: #fff;
  color: var(--pm-text-secondary, #8c8c8c);
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.plan-graph-settings-btn:hover {
  color: var(--pm-primary, #1677ff);
  border-color: #bae0ff;
}
.plan-graph-viewport {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 12px 4px;
  box-sizing: border-box;
}
.plan-graph-viewport-inner {
  width: max-content;
  margin: 0 auto;
}
.plan-graph-svg {
  display: block;
}
.legend-group {
  display: inline-flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  font-size: 12px;
  color: #5f6368;
}
.legend-sep {
  flex-shrink: 0;
  width: 1px;
  height: 16px;
  background: rgba(0, 0, 0, 0.08);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}
.legend-line {
  display: inline-block;
  width: 20px;
  height: 0;
  border-top-width: 2px;
  border-top-style: solid;
}
.legend-line.always { border-top-color: #9aa0a6; }
.legend-line.pass { border-top-color: #34a853; }
.legend-line.reject {
  border-top-color: #ea4335;
  border-top-style: dashed;
  opacity: 0.55;
}
.legend-line.reject-fired {
  border-top-color: #c5221f;
  border-top-width: 2.5px;
}
.legend-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.legend-dot.pending { background: #9aa0a6; }
.legend-dot.running { background: #f9ab00; }
.legend-dot.done { background: #34a853; }
.plan-graph-back {
  font-size: 12px;
  padding: 4px 10px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  color: #1a73e8;
}
.plan-graph-back-solo {
  flex-shrink: 0;
}
.plan-graph-action-primary {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
  font-weight: 600;
}
.plan-graph-action-primary:hover {
  background: #1765cc;
}
.plan-graph-edit-hint {
  flex-shrink: 0;
  font-size: 11px;
  color: #1a73e8;
  font-weight: 500;
  white-space: nowrap;
}
.plan-graph-action {
  font-size: 12px;
  padding: 4px 10px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  color: #1a73e8;
}
.plan-graph-action-danger {
  color: #c5221f;
  border-color: #f28b82;
  background: #fce8e6;
}
.plan-graph-action:hover {
  background: #f1f3f4;
}
.plan-graph-action-danger:hover {
  background: #fad2cf;
}
.plan-graph-back:hover {
  background: #f1f3f4;
}
.plan-graph-phase-group {
  pointer-events: none;
}
.plan-graph-phase-box {
  fill: rgba(26, 115, 232, 0.04);
  stroke: #7baaf7;
  stroke-width: 1.5;
  stroke-dasharray: 8 5;
  paint-order: stroke fill;
}
.plan-graph-phase-label {
  font-size: 12px;
  font-weight: 600;
  fill: #1a73e8;
  pointer-events: none;
}
.plan-graph-status-dot.running {
  animation: plan-node-pulse 1.2s ease-in-out infinite;
}
.plan-graph-edge {
  fill: none;
  stroke: #9aa0a6;
  stroke-width: 1.4;
}
.plan-graph-edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 14;
  cursor: pointer;
}
.plan-graph-edge-hit.edge-readonly {
  cursor: default;
  pointer-events: none;
}
.plan-graph-edge-hit:hover + .plan-graph-edge {
  stroke-width: 2.2;
}
.plan-graph-edge.pass { stroke: #34a853; }
.plan-graph-edge.reject-idle,
.plan-graph-edge.reject-back.reject-idle {
  stroke: #ea4335;
  stroke-dasharray: 6 4;
  opacity: 0.45;
}
.plan-graph-edge.reject-fired,
.plan-graph-edge.reject-back.reject-fired {
  stroke: #c5221f;
  stroke-width: 2;
  stroke-dasharray: none;
  opacity: 1;
}
.plan-graph-edge-label {
  font-size: 10px;
  fill: #5f6368;
  text-anchor: middle;
}
.plan-graph-edge-label.pass { fill: #1e8e3e; }
.plan-graph-edge-label.reject-fired {
  fill: #c5221f;
  font-weight: 700;
}
.plan-graph-edge-label.reject-idle {
  fill: #e57373;
  font-weight: 500;
  opacity: 0.75;
}
.plan-graph-edge-label.always { fill: #5f6368; }
.plan-graph-node-wrap {
  cursor: pointer;
}
.plan-graph-node-shape {
  fill: #fff;
  stroke: #dadce0;
  stroke-width: 1.5;
  transition: stroke 0.15s, fill 0.15s;
}
.plan-graph-node-wrap:hover .plan-graph-node-shape {
  stroke: #1a73e8;
}
.plan-graph-node-wrap.selected .plan-graph-node-shape {
  stroke: #1a73e8;
  stroke-width: 2.5;
  fill: #e8f0fe;
}
.plan-graph-node-wrap.running .plan-graph-node-shape {
  stroke: #f9ab00;
  fill: #fef7e0;
}
.plan-graph-node-wrap.done .plan-graph-node-shape,
.plan-graph-node-wrap.executed .plan-graph-node-shape {
  stroke: #34a853;
  fill: #f1f8f4;
}
.plan-graph-node-wrap.reworked .plan-graph-node-shape {
  stroke: #e37400;
}
.plan-graph-node-wrap.pending .plan-graph-node-shape {
  stroke: #dadce0;
  fill: #fff;
}
.legend-shape {
  display: inline-block;
  width: 16px;
  height: 12px;
  margin-right: 4px;
  vertical-align: middle;
}
.legend-shape.ai-execute,
.legend-shape.execute {
  border: 1.5px solid #dadce0;
  border-radius: 2px;
  background: #fff;
}
.legend-shape.ai-check,
.legend-shape.check {
  width: 16px;
  height: 12px;
  border: 1.5px solid #dadce0;
  background: #fff;
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  transform: none;
  border-radius: 0;
}
.legend-shape.human-gate {
  width: 13px;
  height: 13px;
  border: 1.5px solid #dadce0;
  background: #fff;
  clip-path: none;
  transform: rotate(45deg);
  border-radius: 1px;
}
.legend-shape.expand-gate {
  border: 1.5px solid #dadce0;
  background: #fff;
  clip-path: polygon(14% 0%, 86% 0%, 100% 100%, 0% 100%);
}
.legend-shape.fork-gate {
  border: 1.5px solid #00897b;
  background: #fff;
  clip-path: polygon(0% 0%, 100% 0%, 86% 100%, 14% 100%);
}
.plan-graph-node-wrap.role-fork-gate .plan-graph-node-gate {
  stroke: #00897b;
}
.plan-graph-node-wrap.role-fork-gate.running .plan-graph-node-gate {
  stroke: #f9ab00;
}
.plan-graph-node-wrap.role-fork-gate.done .plan-graph-node-gate,
.plan-graph-node-wrap.role-fork-gate.executed .plan-graph-node-gate {
  stroke: #34a853;
}
.plan-graph-retry-badge {
  fill: #fce8e6;
  stroke: #ea4335;
  stroke-width: 0.8;
}
.plan-graph-retry-text {
  font-size: 8px;
  font-weight: 700;
  fill: #c5221f;
  text-anchor: middle;
  dominant-baseline: central;
  pointer-events: none;
}
.plan-graph-node-actions {
  pointer-events: all;
}
.plan-graph-node-edit,
.plan-graph-node-add,
.plan-graph-node-run {
  cursor: pointer;
}
.plan-graph-node-run.disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.plan-graph-action-icon {
  pointer-events: none;
  transition: stroke 0.15s, fill 0.15s;
}
.plan-graph-edit-btn-icon {
  fill: #5f6368;
}
.plan-graph-node-edit:hover .plan-graph-edit-btn-icon {
  fill: #1a73e8;
}
.plan-graph-add-btn-icon {
  fill: #5f6368;
}
.plan-graph-node-add:hover .plan-graph-add-btn-icon {
  fill: #137333;
}
.plan-graph-run-btn-icon {
  fill: #81c995;
}
.plan-graph-node-run:not(.disabled):hover .plan-graph-run-btn-icon {
  fill: #34a853;
}
.plan-graph-node-run.disabled .plan-graph-run-btn-icon {
  fill: #9aa0a6;
}
@keyframes plan-node-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}
.plan-graph-node-label {
  font-size: 11px;
  font-weight: 600;
  fill: #202124;
  text-anchor: middle;
  pointer-events: none;
}
.plan-graph-node-agent {
  font-size: 10px;
  fill: #80868b;
  text-anchor: middle;
  dominant-baseline: auto;
  pointer-events: none;
}
</style>
