<template>
  <li class="rtn-item">
    <div
      class="rtn-row"
      :class="rowClass"
      :title="node.name || node.id"
      @click="emit('select', node.id)"
    >
      <button
        v-if="hasChildren"
        type="button"
        class="rtn-toggle"
        :aria-expanded="expanded"
        @click.stop="emit('toggle', node.id)"
      >
        <svg class="rtn-chevron" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <span v-else class="rtn-toggle-spacer" />
      <span class="rtn-dot-wrap" :style="{ background: colors.bg, borderColor: colors.border }">
        <span class="rtn-dot" :style="{ background: colors.dot }" />
      </span>
      <span class="rtn-name">{{ node.name || node.id }}</span>
      <span v-if="levelBadge" class="rtn-badge" :class="`rtn-badge-${levelBadge.tone}`">{{ levelBadge.text }}</span>
    </div>
    <ul v-if="hasChildren && expanded" class="rtn-children">
      <RequirementTreeNode
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
import { requirementStatusColor } from '../../utils/requirementGraphModel.js'

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
const colors = computed(() => requirementStatusColor(props.node.status, props.node.node_type))

const rowClass = computed(() => ({
  selected: props.node.id === props.selectedId,
  root: props.showAsRoot || props.node.node_type === 'root',
  expanded: expanded.value,
}))

const levelBadge = computed(() => {
  const level = String(props.node.level || '').trim().toUpperCase()
  const nodeType = props.node.node_type
  if (nodeType === 'root') return null
  if (level === 'IR') return { text: 'IR', tone: 'ir' }
  if (level === 'SR') return { text: 'SR', tone: 'sr' }
  if (level === 'AR') return { text: 'AR', tone: 'ar' }
  if (level === 'REPO') return { text: 'Repo', tone: 'repo' }
  if (level) return { text: level, tone: 'default' }
  return null
})
</script>

<style scoped>
.rtn-item {
  list-style: none;
}
.rtn-row {
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
.rtn-row:hover {
  background: rgba(249, 115, 22, 0.06);
  border-color: rgba(249, 115, 22, 0.12);
}
.rtn-row.selected {
  background: var(--pm-accent-requirements-soft);
  border-color: #fed7aa;
  box-shadow: inset 3px 0 0 var(--pm-accent-requirements);
}
.rtn-row.root .rtn-name {
  font-weight: 700;
}
.rtn-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--pm-text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.rtn-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--pm-text-secondary);
}
.rtn-row.expanded .rtn-chevron {
  transform: rotate(90deg);
}
.rtn-chevron {
  width: 12px;
  height: 12px;
  transition: transform 0.15s ease;
}
.rtn-toggle-spacer {
  width: 16px;
  flex-shrink: 0;
}
.rtn-dot-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 1px solid;
  flex-shrink: 0;
}
.rtn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.rtn-name {
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
.rtn-badge {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.2;
}
.rtn-badge-ir {
  color: #1d4ed8;
  background: #eff6ff;
}
.rtn-badge-sr {
  color: #15803d;
  background: #f0fdf4;
}
.rtn-badge-ar {
  color: #6d28d9;
  background: #f5f3ff;
}
.rtn-badge-repo {
  color: #0e7490;
  background: #ecfeff;
}
.rtn-badge-default {
  color: var(--pm-text-secondary);
  background: var(--pm-surface-muted);
}
.rtn-children {
  list-style: none;
  margin: 0 0 0 12px;
  padding: 0 0 0 6px;
  border-left: 1px solid rgba(249, 115, 22, 0.14);
}
</style>
