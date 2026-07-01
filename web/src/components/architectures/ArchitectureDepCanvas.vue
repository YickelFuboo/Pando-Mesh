<template>
  <div class="architecture-dep-canvas">
    <header class="adc-toolbar">
      <div v-if="showLegend" class="adc-legend">
        <span class="adc-legend-title">图例</span>
        <span class="adc-legend-item"><i class="dot high" />高置信</span>
        <span class="adc-legend-item"><i class="dot medium" />中置信</span>
        <span class="adc-legend-item"><i class="dot low" />低置信</span>
        <span class="adc-legend-item"><i class="line" />depends_on</span>
      </div>
      <div class="adc-toolbar-actions">
        <button
          type="button"
          class="adc-btn adc-btn-home"
          :class="{ active: isFullView }"
          title="全部元素依赖"
          @click="emit('reset-root')"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M2.5 6.5L8 2l5.5 4.5V13a1 1 0 0 1-1 1h-3.5v-4H7v4H3.5a1 1 0 0 1-1-1V6.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          </svg>
        </button>
        <button type="button" class="adc-btn" title="放大" @click="zoomBy(0.12)">+</button>
        <button type="button" class="adc-btn" title="缩小" @click="zoomBy(-0.12)">−</button>
        <button type="button" class="adc-btn" title="适应视图" @click="fitToView">⊡</button>
      </div>
    </header>

    <div
      ref="viewportRef"
      class="adc-viewport"
      @wheel.prevent="onWheel"
      @mousedown="onPanStart"
    >
      <div v-if="loading" class="adc-state">加载架构库…</div>
      <div v-else-if="error" class="adc-state error">{{ error }}</div>
      <div v-else-if="!layout.nodes.length" class="adc-state">暂无架构元素</div>
      <div v-else class="adc-stage">
        <svg
          class="adc-svg"
          :width="displaySize.width"
          :height="displaySize.height"
          :viewBox="viewBox"
        >
          <g :transform="`translate(${panX}, ${panY})`">
            <g v-for="(edge, i) in layout.edges" :key="'e-' + i">
              <path :d="edge.path" class="adc-edge" marker-end="url(#adc-arrow)" />
            </g>
            <defs>
              <marker id="adc-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
              </marker>
            </defs>
            <g
              v-for="node in layout.nodes"
              :key="node.id"
              class="adc-node"
              :class="{ selected: node.id === selectedNodeId || node.id === focusElementId }"
              @click.stop="emit('select-node', node.id)"
            >
              <rect
                :x="node.x"
                :y="node.y"
                :width="node.w"
                :height="node.h"
                rx="8"
                ry="8"
                class="adc-node-bg"
                :style="nodeStyle(node)"
              />
              <text :x="node.x + 8" :y="node.y + 14" class="adc-node-id">{{ node.id }}</text>
              <text
                v-for="(line, li) in node.titleLines"
                :key="li"
                :x="node.x + 8"
                :y="node.y + 28 + li * 12"
                class="adc-node-title"
              >{{ line }}</text>
              <text
                :x="node.x + 8"
                :y="node.y + node.h - 6"
                class="adc-node-status"
              >{{ elementStatusLabel(node) }}</text>
            </g>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { buildArchitectureDepLayout } from '../../utils/architectureDepLayout.js'
import { elementStatusColor, elementStatusLabel } from '../../utils/architectureTreeModel.js'

const props = defineProps({
  elements: { type: Array, default: () => [] },
  focusElementId: { type: String, default: '' },
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

const layout = computed(() => buildArchitectureDepLayout(props.elements, props.focusElementId))

const viewBox = computed(() => `${-VIEW_PAD} ${-VIEW_PAD} ${layout.value.width + VIEW_PAD * 2} ${layout.value.height + VIEW_PAD * 2}`)

const svgSize = computed(() => ({
  width: layout.value.width + VIEW_PAD * 2,
  height: layout.value.height + VIEW_PAD * 2,
}))

const displaySize = computed(() => ({
  width: Math.max(1, Math.round(svgSize.value.width * scale.value)),
  height: Math.max(1, Math.round(svgSize.value.height * scale.value)),
}))

function nodeStyle(node) {
  const c = elementStatusColor(node)
  return { fill: c.bg, stroke: c.border }
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
  () => [props.elements, props.focusElementId],
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
.architecture-dep-canvas {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.adc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
}
.adc-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  font-size: 11px;
  color: var(--pm-text-secondary);
}
.adc-legend-title {
  font-weight: 700;
  color: var(--pm-text);
}
.adc-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.adc-legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot.high { background: #3b82f6; }
.dot.medium { background: #f97316; }
.dot.low { background: #eab308; }
.adc-legend-item .line {
  width: 16px;
  height: 0;
  border-top: 2px solid #94a3b8;
}
.adc-toolbar-actions {
  display: flex;
  gap: 6px;
}
.adc-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.adc-btn-home {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.adc-btn-home svg {
  width: 14px;
  height: 14px;
}
.adc-btn-home.active {
  border-color: var(--pm-accent-architectures);
  color: var(--pm-accent-architectures);
  background: var(--pm-accent-architectures-soft);
}
.adc-viewport {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #fafbfc;
  cursor: grab;
}
.adc-stage {
  padding: 20px;
  min-width: 100%;
  min-height: 100%;
}
.adc-svg {
  display: block;
  overflow: visible;
}
.adc-edge {
  fill: none;
  stroke: #94a3b8;
  stroke-width: 1.5;
}
.adc-node {
  cursor: pointer;
}
.adc-node.selected .adc-node-bg {
  stroke: var(--pm-accent-architectures) !important;
  stroke-width: 2px;
}
.adc-node-bg {
  stroke-width: 1.2;
}
.adc-node-id {
  font-size: 9px;
  font-weight: 700;
  fill: #64748b;
  letter-spacing: 0.04em;
}
.adc-node-title {
  font-size: 11px;
  font-weight: 600;
  fill: #1e293b;
}
.adc-node-status {
  font-size: 9px;
  fill: #94a3b8;
}
.adc-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--pm-text-secondary);
}
.adc-state.error {
  color: var(--pm-danger);
}
</style>
