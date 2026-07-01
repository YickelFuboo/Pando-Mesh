<template>
  <div class="feature-scenario-doc">
    <header class="fsd-head">
      <div class="fsd-head-main">
        <span class="fsd-badge">场景</span>
        <div class="fsd-title-wrap">
          <h2>{{ scenarioNode?.name || '场景文档' }}</h2>
          <p v-if="scenarioNode?.scenario_type" class="fsd-meta">{{ scenarioNode.scenario_type }}</p>
        </div>
      </div>
      <button
        v-if="parentNodeId"
        type="button"
        class="fsd-back-btn"
        @click="emit('show-parent', parentNodeId)"
      >
        返回特性拓扑
      </button>
    </header>
    <div class="fsd-body">
      <div v-if="loading" class="fsd-state">加载场景文档…</div>
      <div v-else-if="error" class="fsd-state error">{{ error }}</div>
      <div v-else-if="!fileContent.trim()" class="fsd-state">场景文档暂无内容</div>
      <div v-else class="fsd-markdown-wrap">
        <MarkdownWithMeta
          :content="fileContent"
          :meta="fileMeta"
          :file-path="resolvedPath"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import { getMetaWorkspaceFile } from '../../api/layerApi.js'
import { scenarioWorkspaceFilePath } from '../../utils/featureTreeModel.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  scenarioNode: { type: Object, default: null },
  parentNodeId: { type: String, default: '' },
})

const emit = defineEmits(['show-parent'])

const loading = ref(false)
const error = ref('')
const fileContent = ref('')
const fileMeta = ref({})
const resolvedPath = ref('')

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
    resolvedPath.value = data?.resolved_path || filePath
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
}
.fsd-head-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.fsd-badge {
  flex-shrink: 0;
  margin-top: 2px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #6d28d9;
  background: #f5f3ff;
}
.fsd-title-wrap {
  min-width: 0;
}
.fsd-title-wrap h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--pm-text);
  word-break: break-word;
}
.fsd-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--pm-text-secondary);
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
  overflow: auto;
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
  max-width: 920px;
  margin: 0 auto;
  padding: 20px 24px 32px;
}
.fsd-path {
  margin: 0 0 12px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
}
</style>
