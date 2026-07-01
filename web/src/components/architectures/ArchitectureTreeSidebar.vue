<template>
  <aside class="architecture-tree-sidebar">
    <header class="ats-head">
      <div class="ats-head-main">
        <span class="ats-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h10M4 17h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            <rect x="16" y="9" width="4" height="6" rx="1" stroke="currentColor" stroke-width="1.6" />
          </svg>
        </span>
        <div class="ats-head-text">
          <h2>架构树</h2>
          <p>Architectures</p>
        </div>
      </div>
      <button type="button" class="ats-btn" :disabled="loading" title="刷新" @click="emit('refresh')">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M13.5 8A5.5 5.5 0 1 1 8 2.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          <path d="M8 1v3h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </header>
    <p v-if="error" class="ats-error">{{ error }}</p>
    <p v-else-if="!loading && !treeRoot" class="ats-empty">暂无数据</p>
    <ul v-else class="ats-tree">
      <ArchitectureTreeNode
        v-if="treeRoot"
        :node="treeRoot"
        :depth="0"
        :expanded-ids="expandedIds"
        :selected-id="selectedNodeId"
        :show-as-root="true"
        @toggle="toggleExpand"
        @select="emit('select-node', $event)"
      />
    </ul>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'
import ArchitectureTreeNode from './ArchitectureTreeNode.vue'
import { collectExpandIds } from '../../utils/architectureTreeModel.js'

const props = defineProps({
  treeRoot: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['select-node', 'refresh'])

const expandedIds = ref(new Set())

function toggleExpand(nodeId) {
  const next = new Set(expandedIds.value)
  if (next.has(nodeId)) next.delete(nodeId)
  else next.add(nodeId)
  expandedIds.value = next
}

watch(
  () => props.treeRoot,
  (root) => {
    expandedIds.value = collectExpandIds(root, 2)
  },
  { immediate: true },
)
</script>

<style scoped>
.architecture-tree-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: linear-gradient(180deg, #fbfcfd 0%, #f8f8ff 100%);
  border-right: 1px solid var(--pm-border);
}
.ats-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 12px 12px;
  border-bottom: 1px solid var(--pm-border);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.72);
}
.ats-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.ats-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--pm-accent-architectures-icon);
  color: var(--pm-accent-architectures);
  flex-shrink: 0;
}
.ats-icon svg {
  width: 18px;
  height: 18px;
}
.ats-head-text h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--pm-text);
}
.ats-head-text p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--pm-text-muted);
}
.ats-btn {
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
}
.ats-btn svg {
  width: 15px;
  height: 15px;
}
.ats-btn:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: var(--pm-accent-architectures);
  background: var(--pm-accent-architectures-soft);
}
.ats-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.ats-error {
  margin: 12px 14px;
  font-size: 12px;
  color: var(--pm-danger);
}
.ats-empty {
  margin: 20px 14px;
  font-size: 13px;
  color: var(--pm-text-secondary);
  text-align: center;
}
.ats-tree {
  list-style: none;
  margin: 0;
  padding: 10px 0 14px;
  overflow: auto;
  flex: 1;
}
</style>
