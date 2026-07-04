<template>
  <aside class="feature-tree-sidebar">
    <header class="fts-head">
      <div class="fts-head-main">
        <span class="fts-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 3L4 8v8l8 5 8-5V8l-8-5z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M12 12l8-5M12 12L4 7M12 12v13" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
          </svg>
        </span>
        <div class="fts-head-text">
          <h2>特性树</h2>
          <p>Features</p>
        </div>
      </div>
      <button type="button" class="fts-btn" :disabled="loading" title="刷新" @click="emit('refresh')">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M13.5 8A5.5 5.5 0 1 1 8 2.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          <path d="M8 1v3h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </header>
    <p v-if="error" class="fts-error">{{ error }}</p>
    <p v-else-if="loading" class="fts-loading">加载特性树…</p>
    <p v-else-if="!topLevelNodes.length" class="fts-empty">暂无数据</p>
    <ul v-else-if="topLevelNodes.length" class="fts-tree">
      <FeatureTreeNode
        v-for="child in topLevelNodes"
        :key="child.id"
        :node="child"
        :depth="0"
        :expanded-ids="expandedIds"
        :selected-id="selectedNodeId"
        @toggle="toggleExpand"
        @select="emit('select-node', $event)"
      />
    </ul>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import FeatureTreeNode from './FeatureTreeNode.vue'
import { collectExpandIdsFromChildren } from '../../utils/featureTreeModel.js'

const props = defineProps({
  treeRoot: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['select-node', 'refresh'])

const expandedIds = ref(new Set())
const topLevelNodes = computed(() => props.treeRoot?.children || [])

function toggleExpand(nodeId) {
  const next = new Set(expandedIds.value)
  if (next.has(nodeId)) next.delete(nodeId)
  else next.add(nodeId)
  expandedIds.value = next
}

watch(
  () => props.treeRoot,
  (root) => {
    expandedIds.value = collectExpandIdsFromChildren(root, 2)
  },
  { immediate: true },
)
</script>

<style scoped>
.feature-tree-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: linear-gradient(180deg, #fbfcfd 0%, #f7faf9 100%);
  border-right: 1px solid var(--pm-border);
}
.fts-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 12px 12px;
  border-bottom: 1px solid var(--pm-border);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(6px);
}
.fts-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.fts-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--pm-accent-features-icon);
  color: var(--pm-accent-features);
  flex-shrink: 0;
}
.fts-icon svg {
  width: 18px;
  height: 18px;
}
.fts-head-text {
  min-width: 0;
}
.fts-head-text h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--pm-text);
  line-height: 1.2;
}
.fts-head-text p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--pm-text-muted);
  letter-spacing: 0.03em;
}
.fts-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--pm-border-strong);
  border-radius: 8px;
  background: #fff;
  color: var(--pm-text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.fts-btn svg {
  width: 15px;
  height: 15px;
}
.fts-btn:hover:not(:disabled) {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.fts-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.fts-error {
  margin: 12px 14px;
  font-size: 12px;
  color: var(--pm-danger);
}
.fts-loading {
  margin: 20px 14px;
  font-size: 13px;
  color: var(--pm-text-secondary);
  text-align: center;
}
.fts-empty {
  margin: 20px 14px;
  font-size: 13px;
  color: var(--pm-text-secondary);
  text-align: center;
}
.fts-tree {
  list-style: none;
  margin: 0;
  padding: 10px 0 14px;
  overflow: auto;
  flex: 1;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}
.fts-tree::-webkit-scrollbar {
  width: 6px;
}
.fts-tree::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}
.fts-tree::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
