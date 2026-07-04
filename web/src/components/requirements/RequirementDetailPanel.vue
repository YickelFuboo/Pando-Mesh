<template>
  <div class="requirement-detail-panel">
    <header class="rdp-head">
      <div class="rdp-head-main">
        <span class="rdp-badge" :class="badgeClass">{{ badge }}</span>
        <h2>{{ detailNode?.name || '需求详情' }}</h2>
      </div>
      <div class="rdp-head-actions">
        <button
          type="button"
          class="rdp-home-btn"
          title="全部需求拓扑"
          @click="emit('reset-root')"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M2.5 6.5L8 2l5.5 4.5V13a1 1 0 0 1-1 1h-3.5v-4H7v4H3.5a1 1 0 0 1-1-1V6.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          </svg>
          <span>全部拓扑</span>
        </button>
        <nav class="rdp-tabs">
          <button
            type="button"
            class="rdp-tab"
            :class="{ active: activeTab === 'spec' }"
            @click="activeTab = 'spec'"
          >
            详情
          </button>
          <button
            type="button"
            class="rdp-tab"
            :class="{ active: activeTab === 'topology' }"
            @click="activeTab = 'topology'"
          >
            节点拓扑
          </button>
        </nav>
      </div>
    </header>

    <div v-if="activeTab === 'spec'" class="rdp-spec-pane">
      <TreeNodeInfoBar
        :node="detailNode"
        node-type="requirement"
        :meta="fileMeta"
        collapsible
      />
      <DocFileTabs
        v-if="docTabItems.length"
        v-model="activeDocMd"
        accent="requirements"
        :items="docTabItems"
      />
      <div v-if="docLoading" class="rdp-state">加载文档…</div>
      <div v-else-if="docError" class="rdp-state error">{{ docError }}</div>
      <div v-else-if="!fileContent.trim()" class="rdp-state">文档暂无内容</div>
      <div v-else class="rdp-markdown-wrap">
        <MarkdownWithMeta
          :content="fileContent"
          :meta="fileMeta"
        />
      </div>
    </div>

    <RequirementTopologyCanvas
      v-else-if="activeTab === 'topology'"
      class="rdp-topology-pane"
      :root-node="topologyRoot"
      :selected-node-id="selectedNodeId"
      :loading="loading"
      :error="error"
      @select-node="emit('select-node', $event)"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import RequirementTopologyCanvas from './RequirementTopologyCanvas.vue'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import TreeNodeInfoBar from '../common/TreeNodeInfoBar.vue'
import DocFileTabs from '../common/DocFileTabs.vue'
import { getMetaWorkspaceFile } from '../../api/layerApi.js'
import {
  buildRequirementDetailTopologyRoot,
  requirementNodeBadge,
  requirementNodeDocs,
  requirementWorkspaceFilePath,
} from '../../utils/requirementGraphModel.js'
import { workspaceFileDisplayPath, workspacePathBasename } from '../../utils/workspacePath.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  detailNode: { type: Object, default: null },
  treeRoot: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['select-node', 'reset-root'])

const activeTab = defineModel('activeTab', { type: String, default: 'topology' })
const activeDocMd = ref('')
const docLoading = ref(false)
const docError = ref('')
const fileContent = ref('')
const fileMeta = ref({})
const resolvedPath = ref('')

const badge = computed(() => requirementNodeBadge(props.detailNode))

const badgeClass = computed(() => {
  const type = String(props.detailNode?.node_type || '').toLowerCase()
  if (type === 'scenario') return 'is-sr'
  if (type === 'architecture') return 'is-ar'
  if (type === 'repo') return 'is-repo'
  return 'is-ir'
})

const topologyRoot = computed(() => (
  buildRequirementDetailTopologyRoot(props.detailNode, props.treeRoot)
))

const docOptions = computed(() => requirementNodeDocs(props.detailNode))

const docTabItems = computed(() => docOptions.value.map((doc) => ({
  id: doc.md,
  label: workspacePathBasename(doc.md) || doc.label,
  title: resolvedPathForDoc(doc.md),
})))

function resolvedPathForDoc(mdRel) {
  const ws = props.workspacePath.trim()
  const node = props.detailNode
  if (!ws || !node || !mdRel) return ''
  return requirementWorkspaceFilePath(node, mdRel)
}

async function loadDoc() {
  const ws = props.workspacePath.trim()
  const node = props.detailNode
  if (!ws || !node) {
    docLoading.value = false
    docError.value = ''
    fileContent.value = ''
    fileMeta.value = {}
    resolvedPath.value = ''
    return
  }
  const mdRel = activeDocMd.value || docOptions.value[0]?.md || ''
  const filePath = requirementWorkspaceFilePath(node, mdRel)
  if (!filePath) {
    docLoading.value = false
    docError.value = '未配置文档路径'
    fileContent.value = ''
    fileMeta.value = {}
    resolvedPath.value = ''
    return
  }
  docLoading.value = true
  docError.value = ''
  try {
    const data = await getMetaWorkspaceFile(ws, filePath)
    fileContent.value = data?.content || ''
    fileMeta.value = data?.meta || {}
    resolvedPath.value = workspaceFileDisplayPath(data, filePath)
  } catch (e) {
    fileContent.value = ''
    fileMeta.value = {}
    resolvedPath.value = ''
    docError.value = e?.message || '加载文档失败'
  } finally {
    docLoading.value = false
  }
}

watch(
  () => [props.detailNode?.id, props.detailNode?.md, props.detailNode?.docs],
  () => {
    activeDocMd.value = docOptions.value[0]?.md || ''
  },
  { immediate: true },
)

watch(
  () => [props.workspacePath, props.detailNode?.id, activeDocMd.value],
  () => loadDoc(),
  { immediate: true },
)
</script>

<style scoped>
.requirement-detail-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.rdp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.rdp-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.rdp-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-accent-requirements);
  background: var(--pm-accent-requirements-soft);
}
.rdp-badge.is-sr {
  color: #16a34a;
  background: #f0fdf4;
}
.rdp-badge.is-ar {
  color: #7c3aed;
  background: #f5f3ff;
}
.rdp-badge.is-repo {
  color: #0891b2;
  background: #ecfeff;
}
.rdp-head-main h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--pm-text);
  line-height: 1.35;
}
.rdp-head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.rdp-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  color: var(--pm-text-secondary);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  flex-shrink: 0;
}
.rdp-home-btn svg {
  display: block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.rdp-home-btn:hover {
  border-color: #fdba74;
  color: var(--pm-accent-requirements);
  background: var(--pm-accent-requirements-soft);
}
.rdp-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  border-radius: 10px;
  background: var(--pm-surface-muted);
  flex-shrink: 0;
}
.rdp-tab {
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--pm-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.rdp-tab.active {
  background: #fff;
  color: var(--pm-accent-requirements);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.rdp-spec-pane {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
}
.rdp-spec-pane :deep(.tree-node-info) {
  flex-shrink: 0;
}
.rdp-topology-pane {
  flex: 1;
  min-height: 0;
}
.rdp-markdown-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.rdp-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  padding: 24px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.rdp-state.error {
  color: var(--pm-danger);
}
</style>
