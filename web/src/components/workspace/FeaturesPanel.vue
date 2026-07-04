<template>
  <div class="features-workspace-page">
    <p v-if="!workspacePath.trim()" class="features-empty-banner">
      请先在顶栏配置<strong>作业空间路径</strong>，以加载 <code>{workspace}/features/</code> 特性库。
    </p>
    <template v-else>
      <FeatureTreeSidebar
        class="features-tree-pane"
        :style="{ width: `${treePaneWidth}px` }"
        :tree-root="treeRoot"
        :selected-node-id="treeSelectedId"
        :loading="treeLoading"
        :error="error"
        @select-node="selectedNodeId = $event"
        @refresh="loadFeatures(true)"
      />
      <div
        class="features-tree-resize-handle"
        :class="{ dragging: treePaneResizing }"
        title="拖动调整特性树宽度"
        @mousedown.prevent="startResizeTreePane"
      >
        <span class="features-tree-resize-bar" aria-hidden="true" />
      </div>
      <FeatureScenarioDocPanel
        v-if="selectedScenarioNode"
        class="features-topology-pane"
        :workspace-path="workspacePath"
        :scenario-node="selectedScenarioNode"
        :parent-node-id="scenarioParentId"
        @show-parent="selectedNodeId = $event"
        @reset-root="resetTopologyView"
      />
      <FeatureDetailPanel
        v-else-if="selectedFeatureNode"
        v-model:active-tab="featureDetailViewTab"
        class="features-topology-pane"
        :workspace-path="workspacePath"
        :feature-node="selectedFeatureNode"
        :summary-only="featureSummaryOnly"
        :selected-node-id="selectedNodeId"
        :loading="treeLoading"
        :topology-busy="topologyBusy"
        :error="error"
        :arch-name-map="archNameMap"
        @select-node="onTopologySelectNode"
        @reset-root="resetTopologyView"
      />
      <FeatureTopologyCanvas
        v-else
        class="features-topology-pane"
        :root-node="topologyRoot"
        :selected-node-id="selectedNodeId"
        :is-full-view="isFullTopology"
        :loading="treeLoading"
        :topology-busy="topologyBusy"
        :error="error"
        :arch-name-map="archNameMap"
        @select-node="onTopologySelectNode"
        @reset-root="resetTopologyView"
      />
    </template>
  </div>
</template>

<script setup>
defineOptions({ name: 'FeaturesPanel' })

import { computed, ref, watch } from 'vue'
import FeatureTreeSidebar from '../features/FeatureTreeSidebar.vue'
import FeatureTopologyCanvas from '../features/FeatureTopologyCanvas.vue'
import FeatureScenarioDocPanel from '../features/FeatureScenarioDocPanel.vue'
import FeatureDetailPanel from '../features/FeatureDetailPanel.vue'
import { listFeatures, listArchitecturesTree } from '../../api/layerApi.js'
import {
  cloneSubtree,
  findNodeById,
  findParentNode,
  isFeatureBranchNode,
} from '../../utils/featureTreeModel.js'
import { flattenElements, normalizeElementRow } from '../../utils/architectureTreeModel.js'

const TREE_PANE_WIDTH_KEY = 'pando_mesh_features_tree_width'
const TREE_PANE_MIN_W = 220
const TREE_PANE_MAX_W = 560
const TREE_PANE_DEFAULT_W = 300

function readTreePaneWidth() {
  const raw = Number(localStorage.getItem(TREE_PANE_WIDTH_KEY))
  if (!Number.isFinite(raw)) return TREE_PANE_DEFAULT_W
  return Math.min(TREE_PANE_MAX_W, Math.max(TREE_PANE_MIN_W, Math.round(raw)))
}

const FEATURE_ROOT_ID = 'feature_root'

const props = defineProps({
  workspacePath: { type: String, default: '' },
})

const treeLoading = ref(false)
const topologyBusy = ref(false)
const error = ref('')
const treeRoot = ref(null)
const loadedWorkspace = ref('')
const selectedNodeId = ref(FEATURE_ROOT_ID)
const featureDetailViewTab = ref('topology')
const treePaneWidth = ref(readTreePaneWidth())
const treePaneResizing = ref(false)
const archNameMap = ref({})

const treeSelectedId = computed(() => (
  selectedNodeId.value === FEATURE_ROOT_ID ? '' : selectedNodeId.value
))

const isFullTopology = computed(() => selectedNodeId.value === FEATURE_ROOT_ID)

const selectedNode = computed(() => {
  if (!treeRoot.value || selectedNodeId.value === FEATURE_ROOT_ID) return null
  return findNodeById(treeRoot.value, selectedNodeId.value)
})

const selectedScenarioNode = computed(() => {
  const node = selectedNode.value
  return node?.node_type === 'scenario' ? node : null
})

const selectedFeatureNode = computed(() => {
  const node = selectedNode.value
  if (!node || node.node_type !== 'feature') return null
  return node
})

const featureSummaryOnly = computed(() => isFeatureBranchNode(selectedFeatureNode.value))

const scenarioParentId = computed(() => {
  if (!treeRoot.value || !selectedScenarioNode.value) return ''
  const parent = findParentNode(treeRoot.value, selectedScenarioNode.value.id)
  if (!parent || parent.id === FEATURE_ROOT_ID) return ''
  return parent.id
})

const topologyRoot = computed(() => {
  if (!treeRoot.value) return null
  if (selectedNodeId.value === FEATURE_ROOT_ID) {
    return cloneSubtree(treeRoot.value)
  }
  const node = findNodeById(treeRoot.value, selectedNodeId.value)
  return cloneSubtree(node || treeRoot.value)
})

function resetTopologyView() {
  selectedNodeId.value = FEATURE_ROOT_ID
}

function onTopologySelectNode(nodeId) {
  selectedNodeId.value = nodeId
}

function startResizeTreePane(e) {
  const startX = e.clientX
  const startW = treePaneWidth.value
  treePaneResizing.value = true
  function onMove(moveE) {
    const delta = moveE.clientX - startX
    treePaneWidth.value = Math.round(
      Math.min(TREE_PANE_MAX_W, Math.max(TREE_PANE_MIN_W, startW + delta)),
    )
  }
  function onUp() {
    treePaneResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.classList.remove('split-dragging')
    localStorage.setItem(TREE_PANE_WIDTH_KEY, String(treePaneWidth.value))
  }
  document.body.classList.add('split-dragging')
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

async function loadFeatures(force = false) {
  const ws = props.workspacePath.trim()
  error.value = ''
  if (!ws) {
    treeRoot.value = null
    loadedWorkspace.value = ''
    archNameMap.value = {}
    return
  }
  if (!force && treeRoot.value && loadedWorkspace.value === ws) return
  treeLoading.value = true
  topologyBusy.value = false
  if (force || loadedWorkspace.value !== ws) {
    treeRoot.value = null
  }
  try {
    const [payload, archPayload] = await Promise.all([
      listFeatures(ws),
      listArchitecturesTree(ws).catch(() => null),
    ])
    treeRoot.value = payload.root || null
    loadedWorkspace.value = ws
    selectedNodeId.value = FEATURE_ROOT_ID
    const map = {}
    if (archPayload?.root) {
      for (const el of flattenElements(archPayload.root)) {
        const row = normalizeElementRow(el)
        map[row.element_id] = row.name
      }
    }
    archNameMap.value = map
    if (treeRoot.value) {
      topologyBusy.value = true
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          topologyBusy.value = false
        })
      })
    }
  } catch (e) {
    error.value = e?.message || '加载特性库失败'
    treeRoot.value = null
    loadedWorkspace.value = ''
    archNameMap.value = {}
  } finally {
    treeLoading.value = false
  }
}

watch(
  () => props.workspacePath,
  () => loadFeatures(true),
  { immediate: true },
)
</script>

<style scoped>
.features-workspace-page {
  display: flex;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.features-tree-pane {
  flex-shrink: 0;
  min-width: 0;
}
.features-tree-resize-handle {
  position: relative;
  width: 6px;
  flex-shrink: 0;
  cursor: col-resize;
  touch-action: none;
  background: #fff;
  border-right: 1px solid var(--pm-border);
}
.features-tree-resize-handle:hover,
.features-tree-resize-handle.dragging {
  background: var(--pm-primary-soft);
}
.features-tree-resize-bar {
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
.features-tree-resize-handle:hover .features-tree-resize-bar,
.features-tree-resize-handle.dragging .features-tree-resize-bar {
  height: 64px;
  background: var(--pm-primary);
}
.features-topology-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.features-empty-banner {
  margin: auto;
  padding: 24px;
  font-size: 14px;
  color: var(--pm-text-secondary);
  text-align: center;
  line-height: 1.6;
}
</style>
