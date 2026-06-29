<template>
  <section v-if="visible" class="pending-panel">
    <div v-if="mode === 'human'" class="pending-card">
      <h3>人工卡点：{{ gateLabel }}</h3>
      <pre class="pending-summary">{{ gateSummary }}</pre>
      <label class="pending-comment">
        意见（驳回必填）
        <textarea v-model="commentLocal" rows="3" placeholder="填写确认或驳回说明" />
      </label>
      <div class="pending-actions">
        <button type="button" class="btn btn-primary" :disabled="busy" @click="$emit('approve', commentLocal)">
          通过并继续
        </button>
        <button type="button" class="btn btn-danger" :disabled="busy" @click="$emit('reject', commentLocal)">
          驳回
        </button>
      </div>
    </div>

    <div v-else-if="mode === 'expand'" class="pending-card">
      <h3>任务分裂确认</h3>
      <p class="pending-hint">上游步骤已产出 {{ tasks.length }} 个子任务，确认后将插入并行分支并继续执行。</p>
      <ul class="task-list">
        <li v-for="(task, idx) in tasks" :key="task.id || idx">
          <strong>{{ task.label || task.id || `任务 ${idx + 1}` }}</strong>
          <span>{{ task.task }}</span>
        </li>
      </ul>
      <div class="pending-actions">
        <button type="button" class="btn btn-primary" :disabled="busy" @click="$emit('expand')">
          确认分裂并执行
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  phase: { type: String, default: 'idle' },
  pendingGate: { type: Object, default: () => ({}) },
  pendingExpand: { type: Object, default: () => ({}) },
  busy: { type: Boolean, default: false },
})

defineEmits(['approve', 'reject', 'expand'])

const commentLocal = ref('')

watch(
  () => props.pendingGate?.node_id,
  () => {
    commentLocal.value = ''
  },
)

const mode = computed(() => {
  if (props.phase === 'awaiting_human') return 'human'
  if (props.phase === 'awaiting_expand') return 'expand'
  return ''
})

const visible = computed(() => Boolean(mode.value))

const gateLabel = computed(() => props.pendingGate?.label || props.pendingGate?.node_id || '审查')
const gateSummary = computed(() => props.pendingGate?.summary || '（无摘要）')
const tasks = computed(() => (Array.isArray(props.pendingExpand?.tasks) ? props.pendingExpand.tasks : []))
</script>

<style scoped>
.pending-panel {
  margin-bottom: 12px;
}
.pending-card {
  background: #fff8e1;
  border: 1px solid #fdd663;
  border-radius: 8px;
  padding: 14px;
}
.pending-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
}
.pending-summary {
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 6px;
  padding: 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  max-height: 240px;
  overflow: auto;
}
.pending-comment {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  color: #5f6368;
}
.pending-comment textarea {
  padding: 8px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  font-family: inherit;
  resize: vertical;
}
.pending-hint {
  margin: 0 0 8px;
  font-size: 13px;
  color: #5f6368;
}
.task-list {
  margin: 0 0 10px;
  padding-left: 18px;
}
.task-list li {
  margin-bottom: 6px;
  font-size: 13px;
}
.task-list span {
  display: block;
  color: #5f6368;
  font-size: 12px;
}
.pending-actions {
  display: flex;
  gap: 8px;
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
.btn-danger {
  background: #fce8e6;
  border-color: #f28b82;
  color: #c5221f;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
