<template>
  <section class="doc-panel">
    <div v-if="loading" class="panel-empty">加载中…</div>
    <div v-else-if="error && !content" class="panel-empty error">{{ error }}</div>
    <div v-else class="doc-body">
      <p v-if="error && content" class="fallback-hint">{{ error }}</p>
      <div class="doc-meta">
        <span class="doc-title">{{ viewTitle }}</span>
        <span v-if="viewPath" class="doc-path">{{ viewPath }}</span>
        <span v-if="activeView === 'doc' && generated" class="doc-tag">自动生成</span>
        <span v-if="activeView === 'ref' && activeRef?.kind === 'glob'" class="doc-tag">通配 {{ activeRef.match_count }} 项</span>
        <span v-if="activeView === 'ref' && activeRef?.kind === 'dir'" class="doc-tag">目录</span>
        <span v-if="activeView === 'ref' && activeRef && !activeRef.exists" class="doc-tag missing-tag">不存在</span>
      </div>

      <div v-if="activeView === 'ref' && activeRef?.kind === 'glob' && !activeRef.matches?.length" class="dir-empty">
        通配路径未匹配到任何文件
      </div>

      <div v-else-if="activeView === 'ref' && activeRef?.kind === 'glob' && activeRef.matches?.length" class="glob-previews">
        <section
          v-for="(match, mi) in activeRef.matches"
          :key="mi"
          class="glob-preview-item"
        >
          <h3 class="glob-preview-title">{{ globMatchLabel(match) }}</h3>
          <MarkdownWithMeta v-if="match.preview" :content="match.preview" />
        </section>
      </div>

      <div v-else-if="activeView === 'ref' && activeRef?.kind === 'dir'" class="dir-list">
        <p v-if="!activeRef.entries?.length" class="dir-empty">目录为空或不可读</p>
        <ul v-else>
          <li v-for="(entry, ei) in activeRef.entries" :key="ei">
            <span class="entry-kind">{{ entry.kind === 'dir' ? '📁' : entry.kind === 'more' ? '…' : '📄' }}</span>
            <span class="entry-name">{{ entry.name }}</span>
          </li>
        </ul>
      </div>

      <div v-else-if="activeView === 'ref' && activeRef && !activeRef.exists" class="panel-empty inline-empty">
        路径尚未生成或不可访问：{{ activeRef.path }}
      </div>

      <MarkdownWithMeta
        v-else-if="activeView === 'ref' && activeRef?.preview"
        :content="activeRef.preview"
      />

      <template v-else-if="activeView === 'doc' || !activeRef">
        <TreeNodeInfoBar
          v-if="Object.keys(docMeta || {}).length"
          :meta="docMeta"
          collapsible
        />
        <DocFilePath :path="viewPath" />
        <MarkdownWithMeta
          :content="content"
          :meta="docMeta"
        />
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { getNodeDoc, getRequirementDoc } from '../../api/layerApi.js'
import {
  buildLocalNodeDoc,
  buildLocalRequirementDocHint,
  formatDocLoadError,
} from '../../utils/nodeDocFallback.js'
import MarkdownWithMeta from '../common/MarkdownWithMeta.vue'
import TreeNodeInfoBar from '../common/TreeNodeInfoBar.vue'
import DocFilePath from '../common/DocFilePath.vue'
import { normalizeWorkspaceRelativePath } from '../../utils/workspacePath.js'

const props = defineProps({
  workflowId: { type: String, default: '' },
  graphSpec: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  nodeOutputs: { type: Object, default: () => ({}) },
  viewFocus: { type: Object, default: null },
})

const activeNodeId = ref('')
const loading = ref(false)
const error = ref('')
const content = ref('')
const docMeta = ref({})
const docTitle = ref('')
const sourcePath = ref('')
const generated = ref(false)
const workspaceRefs = ref([])
const activeView = ref('doc')
const activeRefIndex = ref(-1)

function applyViewFocus(focus) {
  if (!focus?.type) return
  if (focus.type === 'ref' && focus.refIndex != null) {
    showRefView(focus.refIndex)
    return
  }
  showDocView()
}

const activeRef = computed(() => {
  if (activeRefIndex.value < 0) return null
  return workspaceRefs.value[activeRefIndex.value] || null
})

const viewTitle = computed(() => {
  if (activeView.value === 'ref' && activeRef.value) {
    return activeRef.value.label || activeRef.value.path
  }
  return docTitle.value
})

const viewPath = computed(() => {
  if (activeView.value === 'ref' && activeRef.value) {
    return normalizeWorkspaceRelativePath(activeRef.value.path)
  }
  return normalizeWorkspaceRelativePath(sourcePath.value)
})

function globMatchLabel(match) {
  const path = normalizeWorkspaceRelativePath(match?.path)
  if (path) return path
  const resolved = String(match?.resolved_path || '')
  if (!resolved) return '未命名'
  const parts = resolved.replace(/\\/g, '/').split('/')
  return parts.slice(-2).join('/') || resolved
}

function resetView() {
  activeView.value = 'doc'
  activeRefIndex.value = -1
}

function showDocView() {
  activeView.value = 'doc'
  activeRefIndex.value = -1
}

function showRefView(index) {
  activeView.value = 'ref'
  activeRefIndex.value = index
}

function applyLocalFallback() {
  if (activeNodeId.value) {
    const output = props.nodeOutputs?.[activeNodeId.value] || ''
    const local = buildLocalNodeDoc(props.graphSpec, activeNodeId.value, output)
    if (local) {
      applyDoc(local)
      return true
    }
  } else {
    applyDoc(buildLocalRequirementDocHint(props.graphSpec?.requirement_id || ''))
    return true
  }
  return false
}

async function loadDoc() {
  if (!props.workflowId) return
  loading.value = true
  error.value = ''
  try {
    if (!activeNodeId.value) {
      const doc = await getRequirementDoc(props.workflowId)
      applyDoc(doc)
      return
    }
    const doc = await getNodeDoc(props.workflowId, activeNodeId.value)
    applyDoc(doc)
  } catch (e) {
    const hint = formatDocLoadError(e?.message)
    if (applyLocalFallback()) {
      error.value = hint
      return
    }
    content.value = ''
    docMeta.value = {}
    workspaceRefs.value = []
    error.value = hint || '加载文档失败'
  } finally {
    loading.value = false
    if (props.viewFocus?.type) {
      applyViewFocus(props.viewFocus)
    }
  }
}

function applyDoc(doc) {
  content.value = doc?.content || ''
  docMeta.value = doc?.meta || {}
  docTitle.value = doc?.label || doc?.node_id || '文档'
  sourcePath.value = doc?.source_path || ''
  generated.value = Boolean(doc?.generated)
  workspaceRefs.value = Array.isArray(doc?.workspace_refs) ? doc.workspace_refs : []
  if (activeView.value === 'ref') {
    const ref = activeRef.value
    if (!ref || (activeRefIndex.value >= workspaceRefs.value.length)) {
      resetView()
    }
  }
}

watch(
  () => props.viewFocus,
  (focus) => {
    if (!focus?.type || loading.value) return
    applyViewFocus(focus)
  },
)

watch(
  () => [props.workflowId, props.selectedNodeId],
  () => {
    if (props.selectedNodeId) {
      activeNodeId.value = props.selectedNodeId
    }
    resetView()
    loadDoc()
  },
  { immediate: true },
)

defineExpose({ reload: loadDoc })
</script>

<style scoped>
.doc-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: #fff;
  border: none;
  border-radius: 0;
  overflow: hidden;
}
.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #80868b;
  font-size: 13px;
  padding: 16px;
}
.panel-empty.error {
  color: #80868b;
}
.fallback-hint {
  margin: 0 0 10px;
  padding: 8px 10px;
  font-size: 12px;
  color: #b06000;
  background: #fef7e0;
  border-radius: 6px;
}
.inline-empty {
  flex: unset;
  min-height: 120px;
}
.doc-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 14px;
}
.doc-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.doc-title {
  font-size: 14px;
  font-weight: 600;
}
.doc-path {
  font-size: 11px;
  color: #80868b;
  word-break: break-all;
}
.doc-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fef7e0;
  color: #b06000;
}
.doc-tag.missing-tag {
  background: #fce8e6;
  color: #c5221f;
}
.dir-list {
  font-size: 13px;
}
.dir-list ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
}
.dir-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #f1f3f4;
}
.entry-name {
  word-break: break-all;
}
.dir-empty {
  color: #80868b;
  margin: 0 0 12px;
}
.glob-previews {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.glob-preview-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--pm-text);
}
</style>
