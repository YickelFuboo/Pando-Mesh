<template>
  <li class="atn-item">
    <div
      class="atn-row"
      :class="rowClass"
      :title="node.name || node.id"
      @click="emit('select', node.id)"
    >
      <button
        v-if="hasChildren"
        type="button"
        class="atn-toggle"
        :aria-expanded="expanded"
        @click.stop="emit('toggle', node.id)"
      >
        <svg class="atn-chevron" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <span v-else class="atn-toggle-spacer" />
      <span class="atn-kind-icon" :class="kindClass">
        <svg v-if="isRoot" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M4 2.5h5.5L12 5v8.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1z" fill="currentColor" opacity="0.16" />
          <path d="M9.5 2.5V5H12M5 8h6M5 10.5h6M5 13h4" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
        </svg>
        <svg v-else-if="isDocument" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M4 2.5h5.5L12 5v8.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1z" fill="currentColor" opacity="0.16" />
          <path d="M9.5 2.5V5H12M5 8h6M5 10.5h6M5 13h4" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
        </svg>
        <svg v-else-if="isView" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M2.5 4.5h11v7h-11z" fill="currentColor" opacity="0.14" />
          <path d="M2.5 4.5h11v7h-11M5.5 7.5h5M5.5 9.5h3.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round" />
        </svg>
        <svg v-else viewBox="0 0 16 16" aria-hidden="true">
          <rect x="3.5" y="3.5" width="9" height="9" rx="1.5" fill="currentColor" opacity="0.16" />
          <path d="M6 8h4M8 6v4" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
        </svg>
      </span>
      <span class="atn-name">{{ node.name || node.id }}</span>
    </div>
    <ul v-if="hasChildren && expanded" class="atn-children">
      <ArchitectureTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :expanded-ids="expandedIds"
        :selected-id="selectedId"
        @toggle="emit('toggle', $event)"
        @select="emit('select', $event)"
      />
    </ul>
  </li>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  expandedIds: { type: Object, required: true },
  selectedId: { type: String, default: '' },
  showAsRoot: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'select'])

const hasChildren = computed(() => (props.node.children || []).length > 0)
const expanded = computed(() => props.expandedIds.has(props.node.id))
const isRoot = computed(() => props.showAsRoot || props.node.node_type === 'root')
const isDocument = computed(() => props.node.node_type === 'document')
const isView = computed(() => props.node.node_type === 'view')
const isElement = computed(() => props.node.node_type === 'element')

const kindClass = computed(() => ({
  'atn-kind-root': isRoot.value,
  'atn-kind-document': isDocument.value,
  'atn-kind-view': isView.value,
  'atn-kind-element': isElement.value,
}))

const rowClass = computed(() => ({
  selected: props.node.id === props.selectedId,
  root: isRoot.value,
  expanded: expanded.value,
}))
</script>

<style scoped>
.atn-item {
  list-style: none;
}
.atn-row {
  display: flex;
  align-items: center;
  gap: 5px;
  min-height: 32px;
  margin: 1px 4px;
  padding: 5px 8px 5px 4px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.atn-row:hover {
  background: rgba(99, 102, 241, 0.06);
  border-color: rgba(99, 102, 241, 0.12);
}
.atn-row.selected {
  background: var(--pm-accent-architectures-soft);
  border-color: #c7d2fe;
  box-shadow: inset 3px 0 0 var(--pm-accent-architectures);
}
.atn-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--pm-text-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.atn-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--pm-text-secondary);
}
.atn-row.expanded .atn-chevron {
  transform: rotate(90deg);
}
.atn-chevron {
  width: 12px;
  height: 12px;
  transition: transform 0.15s ease;
}
.atn-toggle-spacer {
  width: 16px;
  flex-shrink: 0;
}
.atn-kind-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.atn-kind-icon svg {
  width: 14px;
  height: 14px;
}
.atn-kind-root {
  color: var(--pm-accent-architectures);
}
.atn-kind-document {
  color: #0ea5e9;
}
.atn-kind-view {
  color: var(--pm-accent-architectures);
}
.atn-kind-element {
  color: #7c3aed;
}
.atn-row.root .atn-name {
  font-weight: 700;
}
.atn-name {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--pm-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.atn-children {
  list-style: none;
  margin: 0 0 0 12px;
  padding: 0 0 0 6px;
  border-left: 1px solid rgba(99, 102, 241, 0.14);
}
</style>
