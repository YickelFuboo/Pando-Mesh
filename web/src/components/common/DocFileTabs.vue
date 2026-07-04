<template>
  <div v-if="items.length" class="doc-file-bar" :class="`accent-${accent}`">
    <nav class="doc-file-tabs">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="doc-file-tab"
        :class="{ active: item.id === activeId }"
        :title="item.title || item.label"
        :disabled="items.length <= 1"
        @click="selectItem(item.id)"
      >
        {{ item.label }}
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
  accent: {
    type: String,
    default: 'requirements',
    validator: (value) => ['requirements', 'feature', 'architecture'].includes(value),
  },
})

const emit = defineEmits(['update:modelValue'])

const activeId = computed(() => {
  if (props.modelValue && props.items.some((item) => item.id === props.modelValue)) {
    return props.modelValue
  }
  return props.items[0]?.id || ''
})

function selectItem(id) {
  if (props.items.length <= 1 || id === activeId.value) return
  emit('update:modelValue', id)
}
</script>

<style scoped>
.doc-file-bar {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
}
.doc-file-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-width: 0;
}
.doc-file-tab {
  padding: 2px 8px;
  border: 1px solid var(--pm-border-strong);
  border-radius: 999px;
  background: #fff;
  color: var(--pm-text-secondary);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.35;
  font-family: ui-monospace, monospace;
  cursor: pointer;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.doc-file-tab:disabled {
  cursor: default;
}
.doc-file-bar.accent-requirements .doc-file-tab.active {
  border-color: #fdba74;
  color: var(--pm-accent-requirements);
  background: var(--pm-accent-requirements-soft);
}
.doc-file-bar.accent-feature .doc-file-tab.active {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
  background: var(--pm-primary-soft);
}
.doc-file-bar.accent-architecture .doc-file-tab.active {
  border-color: var(--pm-accent-architectures);
  color: var(--pm-accent-architectures);
  background: var(--pm-accent-architectures-soft);
}
</style>
