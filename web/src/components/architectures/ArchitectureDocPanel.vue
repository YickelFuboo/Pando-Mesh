<template>
  <div class="architecture-doc-panel">
    <header class="adp-head">
      <div class="adp-head-main">
        <span class="adp-badge">{{ badge }}</span>
        <h2>{{ title }}</h2>
      </div>
    </header>
    <TreeNodeInfoBar
      :node="docNode"
      :meta="fileMeta"
      collapsible
    />
    <div class="adp-body">
      <DocFileTabs
        v-if="docTabItems.length"
        model-value="doc"
        accent="architecture"
        :items="docTabItems"
      />
      <div v-if="loading" class="adp-state">加载文档…</div>
      <div v-else-if="error" class="adp-state error">{{ error }}</div>
      <div v-else-if="!fileContent.trim()" class="adp-state">文档暂无内容</div>
      <template v-else>
        <div class="adp-markdown-wrap">
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
import { elementWorkspaceFilePath } from '../../utils/architectureTreeModel.js'
import { workspaceFileDisplayPath, workspacePathBasename } from '../../utils/workspacePath.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  docNode: { type: Object, default: null },
  badge: { type: String, default: '文档' },
  title: { type: String, default: '' },
  filePath: { type: String, default: '' },
})

const loading = ref(false)
const error = ref('')
const fileContent = ref('')
const fileMeta = ref({})
const resolvedPath = ref('')

const docWorkspacePath = computed(() => {
  const node = props.docNode
  return props.filePath || elementWorkspaceFilePath(node) || String(node?.path || '').trim()
})

const docTabItems = computed(() => {
  const path = docWorkspacePath.value
  if (!path) return []
  return [{
    id: 'doc',
    label: workspacePathBasename(path),
    title: resolvedPath.value || path,
  }]
})

async function loadDoc() {
  const ws = props.workspacePath.trim()
  const node = props.docNode
  error.value = ''
  fileContent.value = ''
  fileMeta.value = {}
  resolvedPath.value = ''
  if (!ws || (!node && !props.filePath)) return
  const filePath = docWorkspacePath.value
  if (!filePath) {
    error.value = '未配置文档路径'
    return
  }
  loading.value = true
  try {
    const data = await getMetaWorkspaceFile(ws, filePath)
    fileContent.value = data?.content || ''
    fileMeta.value = data?.meta || {}
    resolvedPath.value = workspaceFileDisplayPath(data, filePath)
  } catch (e) {
    error.value = e?.message || '加载文档失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.workspacePath, props.docNode?.id, props.filePath],
  () => loadDoc(),
  { immediate: true },
)
</script>

<style scoped>
.architecture-doc-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.adp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
}
.adp-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.adp-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-accent-architectures);
  background: var(--pm-accent-architectures-soft);
}
.adp-head-main h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--pm-text);
}
.adp-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.adp-markdown-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.adp-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--pm-text-secondary);
}
.adp-state.error {
  color: var(--pm-danger);
}
</style>
