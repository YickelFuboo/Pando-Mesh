<template>
  <div class="feature-scenario-doc">
    <header class="fsd-head">
      <div class="fsd-head-main">
        <span class="fsd-badge">场景</span>
        <h2>{{ scenarioNode?.name || '场景文档' }}</h2>
      </div>
      <div class="fsd-head-actions">
        <button
          type="button"
          class="fsd-home-btn"
          title="全部特性拓扑"
          @click="emit('reset-root')"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M2.5 6.5L8 2l5.5 4.5V13a1 1 0 0 1-1 1h-3.5v-4H7v4H3.5a1 1 0 0 1-1-1V6.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          </svg>
          <span>全部拓扑</span>
        </button>
        <button
          v-if="parentNodeId"
          type="button"
          class="fsd-back-btn"
          @click="emit('show-parent', parentNodeId)"
        >
          返回特性拓扑
        </button>
      </div>
    </header>
    <TreeNodeInfoBar
      :node="scenarioNode"
      node-type="scenario"
      :meta="fileMeta"
      collapsible
    />
    <div class="fsd-body">
      <DocFileTabs
        v-if="scenarioDocTabItems.length"
        model-value="scenario"
        accent="feature"
        :items="scenarioDocTabItems"
      />
      <div v-if="loading" class="fsd-state">加载场景文档…</div>
      <div v-else-if="error" class="fsd-state error">{{ error }}</div>
      <div v-else-if="!fileContent.trim()" class="fsd-state">场景文档暂无内容</div>
      <template v-else>
        <div class="fsd-markdown-wrap">
          <MarkdownWithMeta
            :content="fileContent"
            :meta="fileMeta"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import TreeNodeInfoBar from '../common/TreeNodeInfoBar.vue'
import DocFileTabs from '../common/DocFileTabs.vue'
import { getMetaWorkspaceFile } from '../../api/layerApi.js'
import { scenarioWorkspaceFilePath } from '../../utils/featureTreeModel.js'
import { workspaceFileDisplayPath, workspacePathBasename } from '../../utils/workspacePath.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  scenarioNode: { type: Object, default: null },
  parentNodeId: { type: String, default: '' },
})

const emit = defineEmits(['show-parent', 'reset-root'])

const loading = ref(false)
const error = ref('')
const fileContent = ref('')
const fileMeta = ref({})
const resolvedPath = ref('')

const scenarioWorkspacePath = computed(() => scenarioWorkspaceFilePath(props.scenarioNode))

const scenarioDocTabItems = computed(() => {
  const path = scenarioWorkspacePath.value
  if (!path) return []
  return [{
    id: 'scenario',
    label: workspacePathBasename(path),
    title: resolvedPath.value || path,
  }]
})

async function loadScenarioDoc() {
  const ws = props.workspacePath.trim()
  const node = props.scenarioNode
  error.value = ''
  fileContent.value = ''
  fileMeta.value = {}
  resolvedPath.value = ''
  if (!ws || !node) return
  const filePath = scenarioWorkspaceFilePath(node)
  if (!filePath) {
    error.value = '场景未配置文档路径'
    return
  }
  loading.value = true
  try {
    const data = await getMetaWorkspaceFile(ws, filePath)
    fileContent.value = data?.content || ''
    fileMeta.value = data?.meta || {}
    resolvedPath.value = workspaceFileDisplayPath(data, filePath)
  } catch (e) {
    error.value = e?.message || '加载场景文档失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.workspacePath, props.scenarioNode?.id],
  () => loadScenarioDoc(),
  { immediate: true },
)
</script>

<style scoped>
.feature-scenario-doc {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.fsd-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.fsd-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.fsd-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #6d28d9;
  background: #f5f3ff;
}
.fsd-head-main h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--pm-text);
  word-break: break-word;
}
.fsd-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.fsd-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
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
.fsd-home-btn svg {
  display: block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.fsd-home-btn span {
  line-height: 1;
}
.fsd-home-btn:hover {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.fsd-back-btn {
  flex-shrink: 0;
  padding: 7px 12px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  color: var(--pm-text-secondary);
  font-size: 12px;
  cursor: pointer;
}
.fsd-back-btn:hover {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.fsd-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
}
.fsd-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  padding: 24px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.fsd-state.error {
  color: var(--pm-danger);
}
.fsd-markdown-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.fsd-path {
  margin: 0 0 12px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
}
</style>
