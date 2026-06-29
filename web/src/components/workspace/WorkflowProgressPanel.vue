<template>
  <section class="progress-panel">
    <header class="progress-head">
      <h3>交付进展</h3>
      <span class="phase-tag" :class="phaseClass">{{ phaseLabel }}</span>
    </header>

    <ul v-if="steps.length" class="progress-list">
      <li
        v-for="step in steps"
        :key="step.id"
        class="progress-item"
        :class="[step.status, { selected: step.id === selectedNodeId }]"
        @click="$emit('select-node', step.id)"
      >
        <span class="status-dot" aria-hidden="true" />
        <div class="progress-body">
          <span class="node-label">{{ step.label }}</span>
          <span class="node-status">{{ step.statusText }}</span>
        </div>
      </li>
    </ul>
    <p v-else class="progress-empty">暂无编排步骤</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { resolveGraphNodeLabel } from '../../utils/planGraphState.js'

const props = defineProps({
  graphSpec: { type: Object, default: null },
  snapshot: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
})

defineEmits(['select-node'])

const phaseLabel = computed(() => {
  const phase = props.snapshot?.phase || 'idle'
  const map = {
    idle: '待执行',
    executing: '执行中',
    done: '已完成',
    awaiting_human: '人工卡点',
    awaiting_expand: '待分裂',
  }
  return map[phase] || phase
})

const phaseClass = computed(() => {
  const phase = props.snapshot?.phase || 'idle'
  if (phase === 'executing') return 'running'
  if (phase === 'done') return 'done'
  if (phase === 'awaiting_human' || phase === 'awaiting_expand') return 'pending'
  return 'idle'
})

function resolveStatus(nodeId) {
  const running = new Set(props.snapshot?.runningNodeIds || [])
  const completed = new Set(props.snapshot?.completedNodeIds || [])
  if (running.has(nodeId)) return 'running'
  if (completed.has(nodeId)) return 'done'
  return 'pending'
}

const steps = computed(() => {
  const nodes = props.graphSpec?.nodes || []
  return nodes.map((node) => {
    const id = node.id
    const status = resolveStatus(id)
    const statusText = status === 'done' ? '已完成' : status === 'running' ? '执行中' : '待执行'
    return {
      id,
      label: resolveGraphNodeLabel(props.graphSpec, id) || id,
      status,
      statusText,
    }
  })
})
</script>

<style scoped>
.progress-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--pm-border, #ebebeb);
}
.progress-head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--pm-text, #1f1f1f);
}
.phase-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f5f5f5;
  color: #8c8c8c;
}
.phase-tag.running {
  background: #e6f4ff;
  color: #1677ff;
}
.phase-tag.done {
  background: #f6ffed;
  color: #52c41a;
}
.phase-tag.pending {
  background: #fff7e6;
  color: #fa8c16;
}
.progress-list {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  overflow: auto;
  flex: 1;
  min-height: 0;
}
.progress-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.progress-item:hover {
  background: #fafafa;
}
.progress-item.selected {
  background: #e6f4ff;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
  background: #d9d9d9;
}
.progress-item.running .status-dot {
  background: #1677ff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.15);
}
.progress-item.done .status-dot {
  background: #52c41a;
}
.progress-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.node-label {
  font-size: 13px;
  color: #1f1f1f;
  line-height: 1.4;
}
.node-status {
  font-size: 11px;
  color: #8c8c8c;
}
.progress-item.running .node-status {
  color: #1677ff;
}
.progress-item.done .node-status {
  color: #52c41a;
}
.progress-empty {
  margin: 0;
  padding: 24px 16px;
  text-align: center;
  font-size: 13px;
  color: #8c8c8c;
}
</style>
