<template>
  <div class="feature-detail-panel">
    <header class="fdp-head">
      <div class="fdp-head-main">
        <span class="fdp-badge">{{ featureNode?.level || '特性' }}</span>
        <h2>{{ featureNode?.name || '特性详情' }}</h2>
      </div>
      <nav class="fdp-tabs">
        <button
          type="button"
          class="fdp-tab"
          :class="{ active: activeTab === 'spec' }"
          @click="activeTab = 'spec'"
        >
          Spec.md
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
    </header>

    <div v-if="activeTab === 'spec'" class="fdp-spec-pane">
      <div v-if="specLoading" class="fdp-state">加载 Spec.md…</div>
      <div v-else-if="specError" class="fdp-state error">{{ specError }}</div>
      <div v-else-if="!specContent.trim()" class="fdp-state">Spec.md 暂无内容</div>
      <div v-else class="fdp-markdown-wrap">
        <MarkdownWithMeta
          :content="specContent"
          :meta="specMeta"
          :file-path="specResolvedPath"
        />
      </div>
    </div>

    <FeatureTopologyCanvas
      v-else
      class="fdp-topology-pane"
      :root-node="topologyRoot"
      :selected-node-id="selectedNodeId"
      :is-full-view="false"
      :loading="loading"
      :error="error"
      @select-node="emit('select-node', $event)"
      @reset-root="emit('reset-root')"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import FeatureTopologyCanvas from './FeatureTopologyCanvas.vue'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import { getMetaWorkspaceFile } from '../../api/layerApi.js'
import { cloneSubtree, featureSpecWorkspaceFilePath } from '../../utils/featureTreeModel.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  featureNode: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['select-node', 'reset-root'])

const activeTab = ref('spec')
const specLoading = ref(false)
const specError = ref('')
const specContent = ref('')
const specMeta = ref({})
const specResolvedPath = ref('')

const topologyRoot = computed(() => cloneSubtree(props.featureNode))

async function loadSpecDoc() {
  const ws = props.workspacePath.trim()
  const node = props.featureNode
  specError.value = ''
  specContent.value = ''
  specMeta.value = {}
  specResolvedPath.value = ''
  if (!ws || !node) return
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
    specResolvedPath.value = data?.resolved_path || filePath
  } catch (e) {
    specError.value = e?.message || '加载 Spec.md 失败'
  } finally {
    specLoading.value = false
  }
}

watch(
  () => props.featureNode?.id,
  () => {
    activeTab.value = 'spec'
    loadSpecDoc()
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
  overflow: auto;
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
  max-width: 920px;
  margin: 0 auto;
  padding: 20px 24px 32px;
}
.fdp-path {
  margin: 0 0 12px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
}
</style>
