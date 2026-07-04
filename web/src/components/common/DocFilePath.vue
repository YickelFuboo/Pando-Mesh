<template>
  <p v-if="normalized" class="doc-file-path">{{ normalized }}</p>
</template>

<script setup>
import { computed } from 'vue'
import { normalizeWorkspaceRelativePath } from '../../utils/workspacePath.js'

const props = defineProps({
  path: { type: String, default: '' },
})

const normalized = computed(() => normalizeWorkspaceRelativePath(props.path))
</script>

<style scoped>
.doc-file-path {
  flex-shrink: 0;
  margin: 0;
  padding: 10px 20px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
  font-family: ui-monospace, monospace;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
}
</style>
