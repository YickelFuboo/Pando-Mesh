<template>
  <div class="feature-topology-canvas">
    <header class="ft-toolbar">
      <div v-if="showLegend" class="ft-legend">
        <span class="ft-legend-title">图例</span>
        <span class="ft-legend-item"><i class="dot planned" />已规划</span>
        <span class="ft-legend-item"><i class="dot partial" />部分实现</span>
        <span class="ft-legend-item"><i class="dot implemented" />已实现</span>
        <span class="ft-legend-item"><i class="dot scenario" />场景</span>
      </div>
      <div class="ft-toolbar-actions">
        <button
          type="button"
          class="ft-btn ft-btn-home"
          :class="{ active: isFullView }"
          title="全部特性拓扑"
          @click="onResetRoot"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M2.5 6.5L8 2l5.5 4.5V13a1 1 0 0 1-1 1h-3.5v-4H7v4H3.5a1 1 0 0 1-1-1V6.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          </svg>
        </button>
        <button type="button" class="ft-btn" title="放大" @click="zoomBy(0.12)">+</button>
        <button type="button" class="ft-btn" title="缩小" @click="zoomBy(-0.12)">−</button>
        <button type="button" class="ft-btn" title="适应视图" @click="fitToView">⊡</button>
      </div>
    </header>

    <div
      ref="viewportRef"
      class="ft-viewport"
      @wheel.prevent="onWheel"
      @mousedown="onPanStart"
    >
      <div v-if="loading" class="ft-state">加载特性库…</div>
      <div v-else-if="error" class="ft-state error">{{ error }}</div>
      <div v-else-if="!layout.nodes.length" class="ft-state">暂无特性数据</div>
      <div v-else class="ft-stage">
        <svg
          class="ft-svg"
          :width="displaySize.width"
          :height="displaySize.height"
          :viewBox="viewBox"
        >
          <g :transform="`translate(${panX}, ${panY})`">
            <g v-for="(edge, i) in layout.edges" :key="'e-' + i">
              <path :d="edge.path" class="ft-edge" />
            </g>
            <g
              v-for="node in layout.nodes"
              :key="node.id"
              class="ft-node"
              :class="{ selected: node.id === selectedNodeId }"
              @click.stop="emit('select-node', node.id)"
            >
              <title>{{ node.description || node.titleLines.join(' ') }}</title>
              <rect
                :x="node.x"
                :y="node.y"
                :width="node.w"
                :height="node.h"
                rx="8"
                ry="8"
                class="ft-node-bg"
                :style="nodeStyle(node)"
              />
              <g
                class="ft-node-icon"
                :transform="`translate(${node.x + 8}, ${node.y + 7}) scale(0.72)`"
              >
                <template v-if="node.nodeType === 'scenario'">
                  <circle cx="9" cy="9" r="7" :fill="nodeColors(node).dot" opacity="0.18" />
                  <path
                    d="M5.5 9.2l2 2 4-4"
                    fill="none"
                    :stroke="nodeColors(node).dot"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </template>
                <template v-else>
                  <path
                    d="M3 5.5L9 2.5l6 3v5.5L9 14.5l-6-3.5V5.5z"
                    :fill="nodeColors(node).dot"
                    opacity="0.16"
                  />
                  <path
                    d="M3 5.5L9 2.5l6 3M9 2.5v12M3 5.5l6 3 6-3"
                    fill="none"
                    :stroke="nodeColors(node).dot"
                    stroke-width="1.3"
                    stroke-linejoin="round"
                  />
                </template>
              </g>
              <text :x="node.x + 24" :y="node.y + 17" class="ft-node-id">{{ node.idLine }}</text>
              <text
                v-for="(line, li) in node.titleLines"
                :key="li"
                :x="node.x + 8"
                :y="nodeTitleY(node, li)"
                class="ft-node-title"
              >{{ line }}</text>
              <text
                :x="node.x + 8"
                :y="node.y + node.h - 6"
                class="ft-node-status"
              >{{ statusLabel(node.status, node.nodeType, node.scenarioType) }}</text>
            </g>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { buildFeatureTreeLayout, FEATURE_LAYOUT } from '../../utils/featureTreeLayout.js'
import { statusColor, statusLabel } from '../../utils/featureTreeModel.js'

const props = defineProps({
  rootNode: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  isFullView: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  showLegend: { type: Boolean, default: true },
})

const emit = defineEmits(['select-node', 'reset-root'])

const VIEW_PAD = 24
const FIT_PAD = 28

const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const viewportRef = ref(null)
const panning = ref(false)
const panStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })
let resizeObserver = null

const layout = computed(() => buildFeatureTreeLayout(props.rootNode))

const viewBox = computed(() => {
  return `${-VIEW_PAD} ${-VIEW_PAD} ${layout.value.width + VIEW_PAD * 2} ${layout.value.height + VIEW_PAD * 2}`
})

const svgSize = computed(() => ({
  width: layout.value.width + VIEW_PAD * 2,
  height: layout.value.height + VIEW_PAD * 2,
}))

const displaySize = computed(() => ({
  width: Math.max(1, Math.round(svgSize.value.width * scale.value)),
  height: Math.max(1, Math.round(svgSize.value.height * scale.value)),
}))

function nodeColors(node) {
  return statusColor(node.status, node.nodeType, node.scenarioType)
}

function nodeStyle(node) {
  const c = nodeColors(node)
  return { fill: c.bg, stroke: c.border }
}

function nodeTitleY(node, lineIndex) {
  const { TOP_PAD, HEADER_H, TITLE_LH } = FEATURE_LAYOUT
  return node.y + TOP_PAD + HEADER_H + lineIndex * TITLE_LH + 9
}

function zoomBy(delta) {
  scale.value = Math.min(2.5, Math.max(0.35, scale.value + delta))
}

function fitToView() {
  const vp = viewportRef.value
  if (!vp || !layout.value.nodes.length) return
  const contentW = svgSize.value.width
  const contentH = svgSize.value.height
  const availW = Math.max(120, vp.clientWidth - FIT_PAD * 2)
  const availH = Math.max(120, vp.clientHeight - FIT_PAD * 2)
  const fitScale = Math.min(availW / contentW, availH / contentH, 1.8)
  scale.value = Math.max(0.35, fitScale)
  panX.value = 0
  panY.value = 0
  nextTick(() => {
    vp.scrollLeft = 0
    vp.scrollTop = 0
  })
}

function onResetRoot() {
  emit('reset-root')
  panX.value = 0
  panY.value = 0
  nextTick(() => fitToView())
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
  const ratio = scale.value || 1
  panX.value = panStart.value.panX + (e.clientX - panStart.value.x) / ratio
  panY.value = panStart.value.panY + (e.clientY - panStart.value.y) / ratio
}

function onPanEnd() {
  panning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
}

watch(
  () => [props.rootNode?.id, props.isFullView],
  () => {
    panX.value = 0
    panY.value = 0
    nextTick(() => fitToView())
  },
)

watch(
  () => [layout.value.width, layout.value.height, props.loading],
  () => {
    if (!props.loading && layout.value.nodes.length) {
      nextTick(() => fitToView())
    }
  },
)

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined' && viewportRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (layout.value.nodes.length) fitToView()
    })
    resizeObserver.observe(viewportRef.value)
  }
  nextTick(() => fitToView())
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
})
</script>

<style scoped>
.feature-topology-canvas {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.ft-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--pm-border);
  flex-shrink: 0;
  background: #fff;
}
.ft-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  font-size: 11px;
  color: var(--pm-text-secondary);
}
.ft-legend-title {
  font-weight: 700;
  color: var(--pm-text);
}
.ft-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.ft-legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot.planned { background: #eab308; }
.dot.partial { background: #f97316; }
.dot.implemented { background: #3b82f6; }
.dot.scenario { background: #8b5cf6; }
.ft-toolbar-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.ft-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
.ft-btn:hover {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
}
.ft-btn-home {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ft-btn-home svg {
  width: 14px;
  height: 14px;
}
.ft-btn-home.active {
  border-color: var(--pm-primary);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.ft-viewport {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #fafbfc;
  cursor: grab;
}
.ft-viewport:active {
  cursor: grabbing;
}
.ft-stage {
  box-sizing: border-box;
  min-width: 100%;
  min-height: 100%;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
}
.ft-svg {
  display: block;
  overflow: visible;
  flex-shrink: 0;
}
.ft-edge {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1.5;
}
.ft-node {
  cursor: pointer;
}
.ft-node.selected .ft-node-bg {
  stroke: var(--pm-primary) !important;
  stroke-width: 2px;
}
.ft-node-bg {
  stroke-width: 1.2;
}
.ft-node-icon {
  pointer-events: none;
}
.ft-node-id {
  font-size: 9px;
  font-weight: 700;
  fill: #64748b;
  letter-spacing: 0.04em;
}
.ft-node-title {
  font-size: 11px;
  font-weight: 600;
  fill: #1e293b;
}
.ft-node-status {
  font-size: 9px;
  fill: #94a3b8;
}
.ft-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.ft-state.error {
  color: var(--pm-danger);
}
</style>
