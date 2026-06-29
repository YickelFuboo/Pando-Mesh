<template>
  <section v-if="nodeId && isCli" class="revise-panel">
    <header class="revise-header">
      <h3>步骤对话 · {{ nodeLabel }}</h3>
      <code class="node-id">{{ nodeId }}</code>
    </header>

    <div v-if="nodeOutput" class="output-block">
      <span class="block-label">当前产出</span>
      <pre class="output-text">{{ nodeOutput }}</pre>
    </div>
    <p v-else class="empty-hint">该步骤尚无执行产出，可直接从拓扑图 ▶ 执行。</p>

    <label class="feedback-field">
      修正意见
      <textarea
        v-model="feedbackLocal"
        rows="4"
        placeholder="描述哪里不满意、希望如何修改…"
        :disabled="busy || disabled"
      />
    </label>

    <div class="revise-actions">
      <button
        type="button"
        class="btn btn-primary"
        :disabled="busy || disabled || !feedbackLocal.trim()"
        @click="$emit('revise', feedbackLocal.trim())"
      >
        {{ busy ? '提交中…' : '修正并重跑' }}
      </button>
      <span v-if="iterations > 1" class="iter-hint">已执行 {{ iterations }} 次</span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { findGraphNode, isCliGraphNode } from '../../utils/planGraphState.js'

const props = defineProps({
  nodeId: { type: String, default: '' },
  graphSpec: { type: Object, default: null },
  snapshot: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

defineEmits(['revise'])

const feedbackLocal = ref('')

watch(
  () => props.nodeId,
  () => {
    feedbackLocal.value = ''
  },
)

const isCli = computed(() => isCliGraphNode(props.snapshot, props.nodeId))

const nodeLabel = computed(() => {
  const node = findGraphNode(props.graphSpec, props.nodeId)
  return node?.label || props.nodeId
})

const nodeOutput = computed(() => {
  const out = props.snapshot?.nodeOutputs?.[props.nodeId]
  return typeof out === 'string' ? out : ''
})

const iterations = computed(() => {
  const n = Number.parseInt(props.snapshot?.nodeIterations?.[props.nodeId], 10)
  return Number.isFinite(n) && n > 0 ? n : 0
})
</script>

<style scoped>
.revise-panel {
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 14px;
}
.revise-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.revise-header h3 {
  margin: 0;
  font-size: 14px;
}
.node-id {
  font-size: 11px;
  color: #5f6368;
  background: #f1f3f4;
  padding: 2px 6px;
  border-radius: 4px;
}
.block-label {
  display: block;
  font-size: 11px;
  color: #5f6368;
  margin-bottom: 4px;
}
.output-block {
  margin-bottom: 10px;
}
.output-text {
  margin: 0;
  max-height: 200px;
  overflow: auto;
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #e8eaed;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
.empty-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #80868b;
}
.feedback-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #5f6368;
}
.feedback-field textarea {
  padding: 8px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  font-family: inherit;
  resize: vertical;
}
.revise-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn {
  padding: 6px 14px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}
.btn-primary {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.iter-hint {
  font-size: 11px;
  color: #80868b;
}
</style>
