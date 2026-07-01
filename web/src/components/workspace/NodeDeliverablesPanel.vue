<template>
  <div class="deliverables-panel">
    <div v-if="!selectedNodeId" class="panel-empty">
      请先在拓扑图中选择一个步骤，再查看交付件
    </div>
    <div v-else-if="loading" class="panel-empty">加载中…</div>
    <div v-else-if="!fileItems.length" class="panel-empty">
      该步骤未配置输出文档路径
    </div>
    <div v-else class="deliverables-layout">
      <header class="file-tabs">
        <button
          v-for="item in fileItems"
          :key="item.id"
          type="button"
          class="file-tab"
          :class="{ active: item.id === selectedFileId, missing: !item.exists }"
          @click="selectFile(item)"
        >
          <span class="file-name">{{ item.name }}</span>
          <span v-if="!item.exists" class="file-state">未生成</span>
        </button>
      </header>
      <div class="file-preview">
        <div v-if="!selectedFile" class="panel-empty inline-empty">
          请选择一个文件
        </div>
        <div v-else-if="contentLoading" class="panel-empty inline-empty">读取中…</div>
        <div v-else-if="contentError" class="panel-empty inline-empty error">{{ contentError }}</div>
        <div v-else-if="!fileContent.trim()" class="panel-empty inline-empty">
          文件暂无内容
        </div>
        <div v-else class="markdown-body">
          <MarkdownWithMeta
            :content="fileContent"
            :meta="fileMeta"
            :file-path="selectedFile.resolvedPath"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { getNodeDoc, getWorkspaceFile } from '../../api/layerApi.js'
import {
  buildDeliverableFileItems,
  resolveNodeOutputPatterns,
} from '../../utils/nodeDeliverables.js'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'

const props = defineProps({
  workflowId: { type: String, default: '' },
  graphSpec: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  nodeOutput: { type: String, default: '' },
})

const loading = ref(false)
const contentLoading = ref(false)
const contentError = ref('')
const fileItems = ref([])
const selectedFileId = ref('')
const fileContent = ref('')
const fileMeta = ref({})

const selectedFile = computed(() => (
  fileItems.value.find((item) => item.id === selectedFileId.value) || null
))

async function loadDeliverables() {
  if (!props.workflowId || !props.selectedNodeId) {
    fileItems.value = []
    selectedFileId.value = ''
    fileContent.value = ''
    fileMeta.value = {}
    return
  }
  loading.value = true
  contentError.value = ''
  try {
    const patterns = resolveNodeOutputPatterns(props.graphSpec, props.selectedNodeId)
    const doc = await getNodeDoc(props.workflowId, props.selectedNodeId)
    fileItems.value = buildDeliverableFileItems(doc?.workspace_refs, patterns)
    const keep = fileItems.value.some((item) => item.id === selectedFileId.value)
    if (!keep) {
      selectedFileId.value = fileItems.value[0]?.id || ''
    }
    if (selectedFileId.value) {
      await loadFileContent(selectedFile.value)
    } else {
      fileContent.value = ''
      fileMeta.value = {}
    }
  } catch (e) {
    fileItems.value = buildDeliverableFileItems(
      [],
      resolveNodeOutputPatterns(props.graphSpec, props.selectedNodeId),
    )
    selectedFileId.value = fileItems.value[0]?.id || ''
    contentError.value = e?.message || '加载交付件失败'
    fileContent.value = ''
    fileMeta.value = {}
  } finally {
    loading.value = false
  }
}

async function loadFileContent(item) {
  if (!item) {
    fileContent.value = ''
    fileMeta.value = {}
    contentError.value = ''
    return
  }
  contentLoading.value = true
  contentError.value = ''
  try {
    if (!item.exists) {
      fileContent.value = ''
      fileMeta.value = {}
      contentError.value = '文件尚未生成，请完成该步骤后查看'
      return
    }
    if (item.preview?.trim()) {
      fileContent.value = item.preview
      fileMeta.value = {}
      return
    }
    const data = await getWorkspaceFile(props.workflowId, item.path)
    fileContent.value = String(data?.content || '')
    fileMeta.value = data?.meta || {}
  } catch (e) {
    fileContent.value = ''
    fileMeta.value = {}
    contentError.value = e?.message || '读取文件失败'
  } finally {
    contentLoading.value = false
  }
}

async function selectFile(item) {
  if (!item || item.id === selectedFileId.value) return
  selectedFileId.value = item.id
  await loadFileContent(item)
}

watch(
  () => [props.workflowId, props.selectedNodeId, props.nodeOutput],
  () => {
    selectedFileId.value = ''
    loadDeliverables()
  },
  { immediate: true },
)

defineExpose({ reload: loadDeliverables })
</script>

<style scoped>
.deliverables-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--pm-surface, #fff);
}
.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  color: #80868b;
  font-size: 13px;
  text-align: center;
}
.panel-empty.error {
  color: #c5221f;
}
.inline-empty {
  flex: 1;
  min-height: 120px;
}
.deliverables-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.file-tabs {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  padding: 8px 12px 0;
  flex-shrink: 0;
  overflow-x: auto;
  border-bottom: 1px solid #e8eaed;
  background: var(--pm-surface, #fff);
}
.file-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: #5f6368;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}
.file-tab.active {
  color: var(--pm-primary, #1677ff);
  background: #f5f8ff;
  box-shadow: inset 0 -2px 0 var(--pm-primary, #1677ff);
}
.file-tab.missing {
  color: #80868b;
}
.file-tab.missing.active {
  color: var(--pm-primary, #1677ff);
}
.file-name {
  font-size: 13px;
  line-height: 1.4;
}
.file-state {
  font-size: 10px;
  color: #c5221f;
  font-weight: 400;
}
.file-preview {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}
.markdown-body {
  padding: 16px 20px;
}
.file-path {
  margin: 0 0 10px;
  font-size: 11px;
  color: #80868b;
  word-break: break-all;
}
</style>
