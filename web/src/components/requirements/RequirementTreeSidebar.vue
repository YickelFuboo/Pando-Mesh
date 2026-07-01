<template>
  <aside class="requirement-tree-sidebar">
    <header class="rts-head">
      <div class="rts-head-main">
        <span class="rts-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M7 4h10v16H7z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M9 8h6M9 12h6M9 16h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <div class="rts-head-text">
          <h2>需求树</h2>
          <p>Requirements</p>
        </div>
      </div>
      <button type="button" class="rts-btn" :disabled="loading" title="刷新" @click="emit('refresh')">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M13.5 8A5.5 5.5 0 1 1 8 2.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          <path d="M8 1v3h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </header>
    <p v-if="error" class="rts-error">{{ error }}</p>
    <p v-else-if="!loading && !topLevelNodes.length" class="rts-empty">暂无数据</p>
    <ul v-else class="rts-tree">
      <RequirementTreeNode
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
import RequirementTreeNode from './RequirementTreeNode.vue'
import { collectExpandIdsFromChildren } from '../../utils/requirementGraphModel.js'

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
.requirement-tree-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: linear-gradient(180deg, #fbfcfd 0%, #faf8f6 100%);
  border-right: 1px solid var(--pm-border);
}
.rts-head {
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
.rts-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.rts-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--pm-accent-requirements-icon);
  color: var(--pm-accent-requirements);
  flex-shrink: 0;
}
.rts-icon svg {
  width: 18px;
  height: 18px;
}
.rts-head-text h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--pm-text);
  line-height: 1.2;
}
.rts-head-text p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--pm-text-muted);
  letter-spacing: 0.03em;
}
.rts-btn {
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
.rts-btn svg {
  width: 15px;
  height: 15px;
}
.rts-btn:hover:not(:disabled) {
  border-color: #fdba74;
  color: var(--pm-accent-requirements);
  background: var(--pm-accent-requirements-soft);
}
.rts-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.rts-error {
  margin: 12px 14px;
  font-size: 12px;
  color: var(--pm-danger);
}
.rts-empty {
  margin: 20px 14px;
  font-size: 13px;
  color: var(--pm-text-secondary);
  text-align: center;
}
.rts-tree {
  list-style: none;
  margin: 0;
  padding: 10px 0 14px;
  overflow: auto;
  flex: 1;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}
.rts-tree::-webkit-scrollbar {
  width: 6px;
}
.rts-tree::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}
.rts-tree::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
