<template>
  <div class="feature-detail-panel">
    <header class="fdp-head">
      <div class="fdp-head-main">
        <span class="fdp-badge">{{ featureNode?.level || '特性' }}</span>
        <h2>{{ featureNode?.name || '特性详情' }}</h2>
      </div>
      <div class="fdp-head-actions">
        <button
          type="button"
          class="fdp-home-btn"
          title="全部特性拓扑"
          @click="emit('reset-root')"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M2.5 6.5L8 2l5.5 4.5V13a1 1 0 0 1-1 1h-3.5v-4H7v4H3.5a1 1 0 0 1-1-1V6.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          </svg>
          <span>全部拓扑</span>
        </button>
        <nav class="fdp-tabs">
        <button
          type="button"
          class="fdp-tab"
          :class="{ active: activeTab === 'spec' }"
          @click="activeTab = 'spec'"
        >
          详情
        </button>
        <button
          type="button"
          class="fdp-tab"
          :class="{ active: activeTab === 'topology' }"
          @click="activeTab = 'topology'"
        >
          节点拓扑
        </button>
        </nav>
      </div>
    </header>

    <TreeNodeInfoBar
      v-if="activeTab === 'spec'"
      :node="featureNode"
      node-type="feature"
      :display-mode="summaryOnly ? 'summary' : 'full'"
      :meta="!summaryOnly ? specMeta : null"
      :collapsible="!summaryOnly"
    />

    <div v-if="activeTab === 'spec' && !summaryOnly" class="fdp-spec-pane">
      <DocFileTabs
        v-if="specDocTabItems.length"
        model-value="spec"
        accent="feature"
        :items="specDocTabItems"
      />
      <div v-if="specLoading" class="fdp-state">加载 Spec.md…</div>
      <div v-else-if="specError" class="fdp-state error">{{ specError }}</div>
      <div v-else-if="!specContent.trim()" class="fdp-state">Spec.md 暂无内容</div>
      <div v-else class="fdp-markdown-wrap">
        <MarkdownWithMeta
          :content="specContent"
          :meta="specMeta"
        />
      </div>
    </div>

    <FeatureTopologyCanvas
      v-else-if="activeTab === 'topology'"
      class="fdp-topology-pane"
      :root-node="topologyRoot"
      :selected-node-id="selectedNodeId"
      :is-full-view="false"
      :loading="loading"
      :topology-busy="topologyBusy"
      :error="error"
      :arch-name-map="archNameMap"
      :show-reset-home="false"
      @select-node="emit('select-node', $event)"
      @reset-root="emit('reset-root')"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import FeatureTopologyCanvas from './FeatureTopologyCanvas.vue'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import TreeNodeInfoBar from '../common/TreeNodeInfoBar.vue'
import DocFileTabs from '../common/DocFileTabs.vue'
import { getMetaWorkspaceFile } from '../../api/layerApi.js'
import { cloneSubtree, featureSpecWorkspaceFilePath } from '../../utils/featureTreeModel.js'
import { workspaceFileDisplayPath, workspacePathBasename } from '../../utils/workspacePath.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  featureNode: { type: Object, default: null },
  summaryOnly: { type: Boolean, default: false },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  topologyBusy: { type: Boolean, default: false },
  error: { type: String, default: '' },
  archNameMap: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['select-node', 'reset-root'])

const activeTab = defineModel('activeTab', { type: String, default: 'topology' })
const specLoading = ref(false)
const specError = ref('')
const specContent = ref('')
const specMeta = ref({})
const specResolvedPath = ref('')

const topologyRoot = computed(() => cloneSubtree(props.featureNode))

const specWorkspacePath = computed(() => featureSpecWorkspaceFilePath(props.featureNode))

const specDocTabItems = computed(() => {
  const path = specWorkspacePath.value
  if (!path) return []
  return [{
    id: 'spec',
    label: workspacePathBasename(path),
    title: specResolvedPath.value || path,
  }]
})

async function loadSpecDoc() {
  const ws = props.workspacePath.trim()
  const node = props.featureNode
  specError.value = ''
  specContent.value = ''
  specMeta.value = {}
  specResolvedPath.value = ''
  if (!ws || !node || props.summaryOnly) return
  const filePath = featureSpecWorkspaceFilePath(node)
  if (!filePath) {
    specError.value = '特性未配置 Spec 路径'
    return
  }
  specLoading.value = true
  try {
    const data = await getMetaWorkspaceFile(ws, filePath)
    specContent.value = data?.content || ''
    specMeta.value = data?.meta || {}
    specResolvedPath.value = workspaceFileDisplayPath(data, filePath)
  } catch (e) {
    specError.value = e?.message || '加载 Spec.md 失败'
  } finally {
    specLoading.value = false
  }
}

watch(
  () => [props.featureNode?.id, props.summaryOnly],
  () => {
    if (!props.summaryOnly) loadSpecDoc()
    else {
      specLoading.value = false
      specError.value = ''
      specContent.value = ''
      specMeta.value = {}
      specResolvedPath.value = ''
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.feature-detail-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.fdp-head {
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
.fdp-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.fdp-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.fdp-head-main h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--pm-text);
  line-height: 1.35;
}
.fdp-head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.fdp-home-btn {
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
.fdp-home-btn svg {
  display: block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.fdp-home-btn span {
  line-height: 1;
}
.fdp-home-btn:hover {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.fdp-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  border-radius: 10px;
  background: var(--pm-surface-muted);
  flex-shrink: 0;
}
.fdp-tab {
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--pm-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.fdp-tab.active {
  background: #fff;
  color: var(--pm-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.fdp-spec-pane {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
}
.fdp-topology-pane {
  flex: 1;
  min-height: 0;
}
.fdp-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  padding: 24px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.fdp-state.error {
  color: var(--pm-danger);
}
.fdp-markdown-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.fdp-path {
  margin: 0 0 12px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
}
</style>
