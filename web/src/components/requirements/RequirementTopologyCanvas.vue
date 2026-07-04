<template>
  <div class="requirement-topology-canvas">
    <header class="rt-toolbar">
      <div v-if="showLegend" class="rt-legend">
        <span class="rt-legend-title">图例</span>
        <span class="rt-legend-item"><i class="dot ir" />IR</span>
        <span class="rt-legend-item"><i class="dot sr" />SR</span>
        <span class="rt-legend-item"><i class="dot ar" />AR</span>
        <span class="rt-legend-item"><i class="dot repo" />Repo</span>
        <span class="rt-legend-item"><i class="line link" />SR↔AR</span>
      </div>
      <div class="rt-toolbar-actions">
        <button type="button" class="rt-btn" title="放大" @click="zoomBy(0.12)">+</button>
        <button type="button" class="rt-btn" title="缩小" @click="zoomBy(-0.12)">−</button>
        <button type="button" class="rt-btn" title="重置视图" @click="resetView">⌂</button>
      </div>
    </header>

    <div
      ref="viewportRef"
      class="rt-viewport"
      @wheel.prevent="onWheel"
      @mousedown="onPanStart"
    >
      <div v-if="loading" class="rt-state">加载需求库…</div>
      <div v-else-if="error" class="rt-state error">{{ error }}</div>
      <div v-else-if="!layout.nodes.length" class="rt-state">暂无需求分解数据</div>
      <svg
        v-else
        class="rt-svg"
        :width="svgSize.width"
        :height="svgSize.height"
        :viewBox="viewBox"
      >
        <g :transform="`translate(${panX}, ${panY}) scale(${scale})`">
          <g v-for="(edge, i) in layout.edges" :key="'e-' + i">
            <path
              :d="edge.path"
              :class="edge.kind === 'link' ? 'rt-edge-link' : 'rt-edge'"
            />
          </g>
          <g
            v-for="node in layout.nodes"
            :key="node.id"
            class="rt-node"
            :class="{ selected: node.id === selectedNodeId }"
            @click.stop="emit('select-node', node.id)"
          >
            <title>{{ node.description || node.titleLines.join(' ') }}</title>
            <rect
              :x="node.x"
              :y="node.y"
              :width="node.w"
              :height="node.h"
              rx="6"
              ry="6"
              class="rt-node-bg"
              :style="nodeStyle(node)"
            />
            <circle
              :cx="node.x + 8"
              :cy="node.y + TOP_PAD + 4"
              r="3"
              class="rt-node-dot"
              :style="{ fill: nodeColors(node).dot }"
            />
            <text :x="node.x + 16" :y="nodeIdY(node)" class="rt-node-id">{{ node.idLine }}</text>
            <text
              :x="node.x + 8"
              :y="nodeTitleStartY(node)"
              class="rt-node-title"
            >
              <tspan
                v-for="(line, li) in node.titleLines"
                :key="li"
                :x="node.x + 8"
                :dy="li === 0 ? 0 : TITLE_LH"
              >{{ line }}</tspan>
            </text>
            <text
              :x="node.x + 8"
              :y="nodeStatusY(node)"
              class="rt-node-status"
            >{{ statusLabel(node.status, node.nodeType) }}</text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { buildRequirementGraphLayout, REQUIREMENT_LAYOUT } from '../../utils/requirementGraphLayout.js'
import { requirementStatusColor, requirementStatusLabel } from '../../utils/requirementGraphModel.js'

const props = defineProps({
  rootNode: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  showLegend: { type: Boolean, default: true },
})

const emit = defineEmits(['select-node'])

const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const viewportRef = ref(null)
const panning = ref(false)
const panStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })

const VIEW_PAD = 24
const {
  TOP_PAD, HEADER_H, TITLE_BASELINE, TITLE_LH, STATUS_GAP, STATUS_H,
} = REQUIREMENT_LAYOUT

const layout = computed(() => buildRequirementGraphLayout(props.rootNode))

const viewBox = computed(() => {
  return `${-VIEW_PAD} ${-VIEW_PAD} ${layout.value.width + VIEW_PAD * 2} ${layout.value.height + VIEW_PAD * 2}`
})

const svgSize = computed(() => ({
  width: layout.value.width + VIEW_PAD * 2,
  height: layout.value.height + VIEW_PAD * 2,
}))

function nodeColors(node) {
  return requirementStatusColor(node.status, node.nodeType)
}

function nodeStyle(node) {
  const c = nodeColors(node)
  return { fill: c.bg, stroke: c.border }
}

function statusLabel(status, nodeType) {
  return requirementStatusLabel(status, nodeType)
}

function nodeIdY(node) {
  return node.y + TOP_PAD + 9
}

function nodeTitleStartY(node) {
  return node.y + TOP_PAD + HEADER_H + TITLE_BASELINE
}

function nodeStatusY(node) {
  const titleBlock = TITLE_BASELINE + Math.max(0, node.titleLines.length - 1) * TITLE_LH
  return node.y + TOP_PAD + HEADER_H + titleBlock + STATUS_GAP + STATUS_H
}

function zoomBy(delta) {
  scale.value = Math.min(2.5, Math.max(0.35, scale.value + delta))
}

function resetView() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

function onWheel(e) {
  zoomBy(e.deltaY < 0 ? 0.08 : -0.08)
}

function onPanStart(e) {
  if (e.button !== 0) return
  panning.value = true
  panStart.value = { x: e.clientX, y: e.clientY, panX: panX.value, panY: panY.value }
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
}

function onPanMove(e) {
  if (!panning.value) return
  panX.value = panStart.value.panX + (e.clientX - panStart.value.x)
  panY.value = panStart.value.panY + (e.clientY - panStart.value.y)
}

function onPanEnd() {
  panning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
}

watch(
  () => props.rootNode?.id,
  () => resetView(),
)
</script>

<style scoped>
.requirement-topology-canvas {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.rt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--pm-border);
  flex-shrink: 0;
  background: #fff;
}
.rt-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  font-size: 11px;
  color: var(--pm-text-secondary);
}
.rt-legend-title {
  font-weight: 700;
  color: var(--pm-text);
}
.rt-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.rt-legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot.ir { background: #3b82f6; }
.dot.sr { background: #22c55e; }
.dot.ar { background: #8b5cf6; }
.dot.repo { background: #06b6d4; }
.rt-legend-item .line {
  width: 16px;
  height: 0;
  border-top: 2px dashed #f97316;
  display: inline-block;
}
.rt-toolbar-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.rt-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
.rt-btn:hover {
  border-color: var(--pm-accent-requirements);
  color: var(--pm-accent-requirements);
}
.rt-viewport {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #fafbfc;
  cursor: grab;
}
.rt-viewport:active {
  cursor: grabbing;
}
.rt-svg {
  display: block;
}
.rt-edge {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1.5;
}
.rt-edge-link {
  fill: none;
  stroke: #f97316;
  stroke-width: 1.5;
  stroke-dasharray: 5 4;
  opacity: 0.85;
}
.rt-node {
  cursor: pointer;
}
.rt-node.selected .rt-node-bg {
  stroke: var(--pm-accent-requirements) !important;
  stroke-width: 2px;
}
.rt-node-bg {
  stroke-width: 1px;
}
.rt-node-dot {
  pointer-events: none;
}
.rt-node-id {
  font-size: 8px;
  font-weight: 700;
  fill: #64748b;
  letter-spacing: 0.04em;
  pointer-events: none;
}
.rt-node-title {
  font-size: 10px;
  font-weight: 600;
  fill: #1e293b;
  pointer-events: none;
}
.rt-node-title tspan {
  font-size: 10px;
  font-weight: 600;
}
.rt-node-status {
  font-size: 8px;
  fill: #94a3b8;
  pointer-events: none;
}
.rt-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.rt-state.error {
  color: var(--pm-danger);
}
</style>
