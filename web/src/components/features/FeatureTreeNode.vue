<template>
  <li class="ftn-item">
    <div
      class="ftn-row"
      :class="rowClass"
      :title="node.name || node.id"
      @click="emit('select', node.id)"
    >
      <button
        v-if="hasChildren"
        type="button"
        class="ftn-toggle"
        :aria-expanded="expanded"
        @click.stop="emit('toggle', node.id)"
      >
        <svg class="ftn-chevron" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <span v-else class="ftn-toggle-spacer" />
      <span class="ftn-kind-icon" :class="isScenario ? 'ftn-kind-scenario' : 'ftn-kind-feature'">
        <svg v-if="isScenario" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="8" cy="8" r="5.5" fill="currentColor" opacity="0.18" />
          <path d="M5.5 8.2l1.8 1.8 3.4-3.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else viewBox="0 0 16 16" aria-hidden="true">
          <path d="M3 5.5L8 2.5l5 3v5.5L8 14l-5-3.5V5.5z" fill="currentColor" opacity="0.16" />
          <path d="M3 5.5L8 2.5l5 3M8 2.5v11.5M3 5.5l5 3 5-3" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
        </svg>
      </span>
      <span class="ftn-name">{{ node.name || node.id }}</span>
    </div>
    <ul v-if="hasChildren && expanded" class="ftn-children">
      <FeatureTreeNode
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
const isScenario = computed(() => props.node.node_type === 'scenario')

const rowClass = computed(() => ({
  selected: props.node.id === props.selectedId,
  root: props.showAsRoot || props.node.node_type === 'root',
  expanded: expanded.value,
}))
</script>

<style scoped>
.ftn-item {
  list-style: none;
}
.ftn-row {
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
.ftn-row:hover {
  background: rgba(0, 184, 148, 0.06);
  border-color: rgba(0, 184, 148, 0.12);
}
.ftn-row.selected {
  background: var(--pm-primary-soft);
  border-color: var(--pm-primary-muted);
  box-shadow: inset 3px 0 0 var(--pm-primary);
}
.ftn-row.root .ftn-name {
  font-weight: 700;
  color: var(--pm-text);
}
.ftn-toggle {
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
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.ftn-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--pm-text-secondary);
}
.ftn-row.expanded .ftn-chevron {
  transform: rotate(90deg);
}
.ftn-chevron {
  width: 12px;
  height: 12px;
  transition: transform 0.15s ease;
}
.ftn-toggle-spacer {
  width: 16px;
  flex-shrink: 0;
}
.ftn-kind-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.ftn-kind-icon svg {
  width: 14px;
  height: 14px;
}
.ftn-kind-feature {
  color: var(--pm-primary);
}
.ftn-kind-scenario {
  color: #7c3aed;
}
.ftn-name {
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
.ftn-children {
  list-style: none;
  margin: 0 0 0 12px;
  padding: 0 0 0 6px;
  border-left: 1px solid rgba(0, 184, 148, 0.14);
}
</style>
