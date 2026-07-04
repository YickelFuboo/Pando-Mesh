<template>
  <div class="requirements-workspace-page">
    <p v-if="!workspacePath.trim()" class="requirements-empty-banner">
      请先在顶栏配置<strong>作业空间路径</strong>，以加载 <code>{workspace}/requirements/</code> 需求库。
    </p>
    <template v-else>
      <RequirementTreeSidebar
        class="requirements-tree-pane"
        :tree-root="treeRoot"
        :selected-node-id="treeSelectedId"
        :loading="loading"
        :error="error"
        @select-node="selectedNodeId = $event"
        @refresh="loadRequirements"
      />
      <RequirementDetailPanel
        v-if="selectedDetailNode"
        v-model:active-tab="detailViewTab"
        class="requirements-main-pane"
        :workspace-path="workspacePath"
        :detail-node="selectedDetailNode"
        :tree-root="treeRoot"
        :selected-node-id="selectedNodeId"
        :loading="loading"
        :error="error"
        @select-node="selectedNodeId = $event"
        @reset-root="resetTopologyView"
      />
      <RequirementTopologyCanvas
        v-else
        class="requirements-main-pane"
        :root-node="topologyRoot"
        :selected-node-id="selectedNodeId"
        :loading="loading"
        :error="error"
        @select-node="selectedNodeId = $event"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import RequirementTreeSidebar from '../requirements/RequirementTreeSidebar.vue'
import RequirementTopologyCanvas from '../requirements/RequirementTopologyCanvas.vue'
import RequirementDetailPanel from '../requirements/RequirementDetailPanel.vue'
import { listRequirementsTree } from '../../api/layerApi.js'
import {
  cloneSubtree,
  findNodeById,
  isRequirementDocNode,
} from '../../utils/requirementGraphModel.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
})

const REQUIREMENTS_ROOT_ID = 'requirements_root'

const loading = ref(false)
const error = ref('')
const treeRoot = ref(null)
const selectedNodeId = ref(REQUIREMENTS_ROOT_ID)
const detailViewTab = ref('topology')

const treeSelectedId = computed(() => (
  selectedNodeId.value === REQUIREMENTS_ROOT_ID ? '' : selectedNodeId.value
))

const selectedNode = computed(() => {
  if (!treeRoot.value || selectedNodeId.value === REQUIREMENTS_ROOT_ID) return null
  return findNodeById(treeRoot.value, selectedNodeId.value)
})

const selectedDetailNode = computed(() => {
  const node = selectedNode.value
  return isRequirementDocNode(node) ? node : null
})

const topologyRoot = computed(() => {
  if (!treeRoot.value) return null
  return cloneSubtree(treeRoot.value)
})

function resetTopologyView() {
  selectedNodeId.value = REQUIREMENTS_ROOT_ID
}

async function loadRequirements() {
  const ws = props.workspacePath.trim()
  error.value = ''
  treeRoot.value = null
  if (!ws) return
  loading.value = true
  try {
    const payload = await listRequirementsTree(ws)
    treeRoot.value = payload.root || null
    selectedNodeId.value = REQUIREMENTS_ROOT_ID
  } catch (e) {
    error.value = e?.message || '加载需求库失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.workspacePath,
  () => loadRequirements(),
  { immediate: true },
)
</script>

<style scoped>
.requirements-workspace-page {
  display: flex;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.requirements-tree-pane {
  width: 300px;
  flex-shrink: 0;
}
.requirements-main-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.requirements-empty-banner {
  margin: auto;
  padding: 24px;
  font-size: 14px;
  color: var(--pm-text-secondary);
  text-align: center;
  line-height: 1.6;
}
</style>
