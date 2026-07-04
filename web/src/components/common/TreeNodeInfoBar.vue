<template>
  <section
    v-if="hasContent"
    class="tree-node-info"
    :class="{
      'summary-mode': isSummaryMode,
      collapsible,
      collapsed: collapsible && collapsed,
    }"
  >
    <div v-if="collapsible" class="tni-bar">
      <button type="button" class="tni-toggle" @click="collapsed = !collapsed">
        <svg
          class="tni-chevron"
          viewBox="0 0 16 16"
          aria-hidden="true"
          :class="{ open: !collapsed }"
        >
          <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>{{ collapsed ? '展开属性' : '收起属性' }}</span>
      </button>
      <span v-if="collapsed && name" class="tni-collapsed-hint">{{ name }}</span>
    </div>
    <div v-show="!collapsible || !collapsed" class="tni-content">
      <dl class="tni-grid">
        <div v-if="showName" class="tni-row">
          <dt>名称</dt>
          <dd>{{ name }}</dd>
        </div>
        <div v-if="showElementId" class="tni-row">
          <dt>元素 ID</dt>
          <dd>{{ elementId }}</dd>
        </div>
        <div v-if="showNodeId" class="tni-row">
          <dt>ID</dt>
          <dd>{{ nodeId }}</dd>
        </div>
        <div v-if="showLevel" class="tni-row">
          <dt>层级</dt>
          <dd>{{ levelLabel }}</dd>
        </div>
        <div v-if="showStatus" class="tni-row">
          <dt>状态</dt>
          <dd>{{ statusText }}</dd>
        </div>
        <div v-if="showScenarioType" class="tni-row">
          <dt>场景类型</dt>
          <dd>{{ scenarioType }}</dd>
        </div>
        <div v-for="entry in docMetaEntries" :key="entry.key" class="tni-row">
          <dt>{{ entry.label }}</dt>
          <dd>{{ entry.value }}</dd>
        </div>
      </dl>
      <div v-if="showDescription" class="tni-desc-row">
        <dt>描述</dt>
        <dd>{{ description }}</dd>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { statusLabel } from '../../utils/featureTreeModel.js'
import { buildDisplayMetaEntries } from '../../utils/markdown.js'

const props = defineProps({
  node: { type: Object, default: null },
  nodeType: { type: String, default: 'feature' },
  meta: { type: Object, default: null },
  displayMode: { type: String, default: 'full' },
  collapsible: { type: Boolean, default: false },
  defaultCollapsed: { type: Boolean, default: false },
})

const collapsed = ref(props.defaultCollapsed)

const isSummaryMode = computed(() => props.displayMode === 'summary')

const name = computed(() => String(props.node?.name || '').trim())
const nodeId = computed(() => String(props.node?.id || '').trim())
const elementId = computed(() => {
  const eid = String(props.node?.element_id || '').trim()
  if (!eid || eid === nodeId.value) return ''
  return eid
})
const description = computed(() => String(props.node?.description || '').trim())
const levelLabel = computed(() => String(props.node?.level || '').trim())
const scenarioType = computed(() => {
  if (props.nodeType !== 'scenario') return ''
  return String(props.node?.scenario_type || '').trim()
})
const statusText = computed(() => {
  const status = props.node?.status
  if (!status || props.nodeType === 'scenario') return ''
  return statusLabel(status, props.node?.node_type || props.nodeType, props.node?.scenario_type)
})

const docMetaEntries = computed(() => {
  if (isSummaryMode.value) return []
  return buildDisplayMetaEntries(props.meta, { hasNode: Boolean(props.node) })
})

const showName = computed(() => name.value)
const showElementId = computed(() => !isSummaryMode.value && elementId.value)
const showNodeId = computed(() => !isSummaryMode.value && nodeId.value)
const showLevel = computed(() => !isSummaryMode.value && levelLabel.value)
const showStatus = computed(() => statusText.value)
const showScenarioType = computed(() => !isSummaryMode.value && scenarioType.value)
const showDescription = computed(() => description.value)

const hasContent = computed(() => (
  showName.value
  || showNodeId.value
  || showElementId.value
  || showDescription.value
  || showLevel.value
  || showStatus.value
  || showScenarioType.value
  || docMetaEntries.value.length
))

watch(
  () => props.node?.id,
  () => {
    collapsed.value = props.defaultCollapsed
  },
)
</script>

<style scoped>
.tree-node-info {
  flex-shrink: 0;
  padding: 14px 20px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
}
.tree-node-info.collapsible {
  padding: 0;
}
.tree-node-info.collapsible.collapsed {
  padding-bottom: 0;
}
.tree-node-info.summary-mode {
  flex: 1;
  border-bottom: none;
}
.tree-node-info.summary-mode.collapsible {
  padding: 0;
}
.tni-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  min-height: 40px;
  border-bottom: 1px solid var(--pm-border);
  background: #fafbfc;
}
.tree-node-info.collapsed .tni-bar {
  border-bottom: none;
}
.tni-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  margin: -4px -8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--pm-text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.tni-toggle:hover {
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.tni-chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  transition: transform 0.15s ease;
}
.tni-chevron.open {
  transform: rotate(90deg);
}
.tni-collapsed-hint {
  min-width: 0;
  font-size: 12px;
  color: var(--pm-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tni-content {
  padding: 14px 20px;
}
.tni-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px 20px;
  margin: 0;
}
.summary-mode .tni-content {
  padding: 14px 20px;
}
.summary-mode .tni-grid {
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  max-width: 480px;
}
.tni-row {
  min-width: 0;
}
.tni-row dt {
  margin: 0 0 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-text-muted);
  letter-spacing: 0.02em;
}
.tni-row dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--pm-text);
  word-break: break-word;
}
.tni-desc-row {
  margin: 10px 0 0;
  min-width: 0;
}
.tni-desc-row dt {
  margin: 0 0 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-text-muted);
  letter-spacing: 0.02em;
}
.tni-desc-row dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--pm-text);
  word-break: break-word;
}
.summary-mode .tni-desc-row {
  max-width: 720px;
}
</style>
