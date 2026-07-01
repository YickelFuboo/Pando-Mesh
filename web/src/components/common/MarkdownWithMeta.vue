<template>
  <div class="markdown-with-meta">
    <p v-if="filePath" class="mwm-path">{{ filePath }}</p>
    <dl v-if="metaEntries.length" class="mwm-meta">
      <div v-for="entry in metaEntries" :key="entry.key" class="mwm-meta-row">
        <dt>{{ entry.label }}</dt>
        <dd>{{ entry.value }}</dd>
      </div>
    </dl>
    <div v-if="html" class="pm-markdown" v-html="html" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMarkdownDocument } from '../../utils/markdown.js'

const props = defineProps({
  content: { type: String, default: '' },
  meta: { type: Object, default: null },
  filePath: { type: String, default: '' },
})

const docView = computed(() => renderMarkdownDocument(props.content, props.meta))

const metaEntries = computed(() => docView.value.metaEntries)
const html = computed(() => docView.value.html)
</script>

<style scoped>
.markdown-with-meta {
  min-width: 0;
}
.mwm-path {
  margin: 0 0 12px;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
  font-family: ui-monospace, monospace;
}
.mwm-meta {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px 16px;
  margin: 0 0 18px;
  padding: 14px 16px;
  border: 1px solid var(--pm-border);
  border-radius: 12px;
  background: #f8fafc;
}
.mwm-meta-row {
  min-width: 0;
}
.mwm-meta-row dt {
  margin: 0 0 3px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-text-muted);
  letter-spacing: 0.02em;
}
.mwm-meta-row dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--pm-text);
  word-break: break-word;
}
</style>
