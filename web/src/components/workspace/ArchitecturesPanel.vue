<template>
  <div class="architectures-workspace-page">
    <p v-if="!workspacePath.trim()" class="architectures-empty-banner">
      请先在顶栏配置<strong>作业空间路径</strong>，以加载 <code>{workspace}/architectures/</code> 架构库。
    </p>
    <template v-else>
      <ArchitectureTreeSidebar
        class="architectures-tree-pane"
        :style="{ width: `${treePaneWidth}px` }"
        :tree-root="treeRoot"
        :selected-node-id="selectedNodeId"
        :loading="loading"
        :error="error"
        @select-node="selectedNodeId = $event"
        @refresh="loadArchitectures"
      />
      <div
        class="architectures-tree-resize-handle"
        :class="{ dragging: treePaneResizing }"
        title="拖动调整架构树宽度"
        @mousedown.prevent="startResizeTreePane"
      >
        <span class="architectures-tree-resize-bar" aria-hidden="true" />
      </div>
      <ArchitectureDocPanel
        v-if="selectedDocumentNode"
        class="architectures-main-pane"
        :workspace-path="workspacePath"
        :doc-node="selectedDocumentNode"
        badge="系统"
        :title="selectedDocumentNode.name"
      />
      <ArchitectureElementPanel
        v-else-if="selectedElementNode"
        v-model:active-tab="elementViewTab"
        class="architectures-main-pane"
        :workspace-path="workspacePath"
        :element-node="selectedElementNode"
        :view-elements="currentViewElements"
        @select-element="onDepSelectElement"
        @reset-root="resetDepView"
      />
      <ArchitectureDepCanvas
        v-else
        class="architectures-main-pane"
        :elements="depElements"
        :focus-element-id="depFocusId"
        :selected-node-id="depSelectedId"
        :is-full-view="isFullDepView"
        :loading="loading"
        :error="error"
        @select-node="onDepSelectElement"
        @reset-root="resetDepView"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import ArchitectureTreeSidebar from '../architectures/ArchitectureTreeSidebar.vue'
import ArchitectureDocPanel from '../architectures/ArchitectureDocPanel.vue'
import ArchitectureElementPanel from '../architectures/ArchitectureElementPanel.vue'
import ArchitectureDepCanvas from '../architectures/ArchitectureDepCanvas.vue'
import { listArchitecturesTree } from '../../api/layerApi.js'
import {
  ARCH_ROOT_ID,
  collectViewElements,
  findNodeById,
  findParentNode,
  flattenElements,
  isArchitectureRootNode,
  normalizeElementRow,
} from '../../utils/architectureTreeModel.js'

const TREE_PANE_WIDTH_KEY = 'moma_developer_architectures_tree_width'
const TREE_PANE_MIN_W = 220
const TREE_PANE_MAX_W = 560
const TREE_PANE_DEFAULT_W = 300

function readTreePaneWidth() {
  const raw = Number(localStorage.getItem(TREE_PANE_WIDTH_KEY))
  if (!Number.isFinite(raw)) return TREE_PANE_DEFAULT_W
  return Math.min(TREE_PANE_MAX_W, Math.max(TREE_PANE_MIN_W, Math.round(raw)))
}

const props = defineProps({
  workspacePath: { type: String, default: '' },
})

const loading = ref(false)
const error = ref('')
const treeRoot = ref(null)
const selectedNodeId = ref(ARCH_ROOT_ID)
const elementViewTab = ref('topology')
const treePaneWidth = ref(readTreePaneWidth())
const treePaneResizing = ref(false)

const selectedNode = computed(() => {
  if (!treeRoot.value) return null
  if (selectedNodeId.value === ARCH_ROOT_ID) return treeRoot.value
  return findNodeById(treeRoot.value, selectedNodeId.value)
})

const selectedDocumentNode = computed(() => {
  const node = selectedNode.value
  if (!node) return null
  if (isArchitectureRootNode(node) || node.node_type === 'document') return node
  return null
})

const selectedElementNode = computed(() => {
  const node = selectedNode.value
  return node?.node_type === 'element' ? node : null
})

const selectedViewNode = computed(() => {
  const node = selectedNode.value
  if (node?.node_type === 'view') return node
  if (node?.node_type === 'element' && treeRoot.value) {
    return findParentNode(treeRoot.value, node.id)
  }
  return null
})

const currentViewElements = computed(() => {
  if (selectedViewNode.value) {
    return collectViewElements(selectedViewNode.value).map(normalizeElementRow)
  }
  if (treeRoot.value) {
    return flattenElements(treeRoot.value).map(normalizeElementRow)
  }
  return []
})

const depElements = computed(() => currentViewElements.value)

const isFullDepView = computed(() => {
  const node = selectedNode.value
  if (!node || isArchitectureRootNode(node)) return false
  return node.node_type === 'view'
})

const depFocusId = computed(() => (
  selectedNode.value?.node_type === 'element' ? selectedNode.value.element_id : ''
))

const depSelectedId = computed(() => depFocusId.value)

function resetDepView() {
  if (selectedViewNode.value) {
    selectedNodeId.value = selectedViewNode.value.id
    return
  }
  selectedNodeId.value = ARCH_ROOT_ID
}

function onDepSelectElement(elementId) {
  if (!treeRoot.value) return
  for (const view of treeRoot.value.children || []) {
    if (view.node_type !== 'view') continue
    const targetId = `${view.view_id}::${elementId}`
    if (findNodeById(treeRoot.value, targetId)) {
      selectedNodeId.value = targetId
      return
    }
  }
}

async function loadArchitectures() {
  const ws = props.workspacePath.trim()
  error.value = ''
  treeRoot.value = null
  if (!ws) return
  loading.value = true
  try {
    const payload = await listArchitecturesTree(ws)
    treeRoot.value = payload.root || null
    selectedNodeId.value = ARCH_ROOT_ID
  } catch (e) {
    error.value = e?.message || '加载架构库失败'
  } finally {
    loading.value = false
  }
}

function startResizeTreePane(e) {
  treePaneResizing.value = true
  const startX = e.clientX
  const startW = treePaneWidth.value
  function onMove(ev) {
    const next = startW + (ev.clientX - startX)
    treePaneWidth.value = Math.min(TREE_PANE_MAX_W, Math.max(TREE_PANE_MIN_W, Math.round(next)))
  }
  function onUp() {
    treePaneResizing.value = false
    localStorage.setItem(TREE_PANE_WIDTH_KEY, String(treePaneWidth.value))
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

watch(
  () => props.workspacePath,
  () => loadArchitectures(),
  { immediate: true },
)
</script>

<style scoped>
.architectures-workspace-page {
  display: flex;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.architectures-tree-pane {
  flex-shrink: 0;
}
.architectures-tree-resize-handle {
  width: 6px;
  flex-shrink: 0;
  cursor: col-resize;
  display: flex;
  align-items: stretch;
  justify-content: center;
  background: transparent;
}
.architectures-tree-resize-handle:hover,
.architectures-tree-resize-handle.dragging {
  background: rgba(99, 102, 241, 0.08);
}
.architectures-tree-resize-bar {
  width: 2px;
  border-radius: 999px;
  background: var(--pm-border);
}
.architectures-tree-resize-handle:hover .architectures-tree-resize-bar,
.architectures-tree-resize-handle.dragging .architectures-tree-resize-bar {
  background: var(--pm-accent-architectures);
}
.architectures-main-pane {
  flex: 1;
  min-width: 0;
}
.architectures-empty-banner {
  margin: auto;
  padding: 24px;
  font-size: 14px;
  color: var(--pm-text-secondary);
  text-align: center;
  line-height: 1.6;
}
</style>
