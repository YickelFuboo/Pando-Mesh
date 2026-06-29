<template>
  <Teleport to="body">
    <div class="overlay" @mousedown.self="emit('close')">
    <div class="card" role="dialog" aria-labelledby="pe-edit-title">
      <header class="header">
        <div class="header-text">
          <h2 id="pe-edit-title" class="title">{{ creating ? '添加连线' : '编辑连线' }}</h2>
          <code class="edge-id">{{ edgeSummary }}</code>
        </div>
        <button type="button" class="close-btn" aria-label="关闭" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </header>

      <form class="form" @submit.prevent="handleSubmit">
        <div class="form-body">
          <div class="field">
            <label for="pe-from">起点</label>
            <select id="pe-from" v-model="form.from" :disabled="fromLocked">
              <option v-if="isStartEdge" :value="START_NODE">START（入口）</option>
              <option v-for="id in nodeIds" :key="'f-' + id" :value="id">{{ nodeLabel(id) }}</option>
            </select>
          </div>
          <div class="field">
            <label for="pe-to">终点</label>
            <select id="pe-to" v-model="form.to" :disabled="isEndEdge">
              <option v-for="id in nodeIds" :key="'t-' + id" :value="id">{{ nodeLabel(id) }}</option>
              <option :value="END_NODE">END（结束）</option>
            </select>
          </div>
          <div class="field">
            <label for="pe-cond">条件</label>
            <select id="pe-cond" v-model="form.condition">
              <option value="always">顺序 (always)</option>
              <option value="pass">通过 (pass)</option>
              <option value="reject">驳回返工 (reject)</option>
            </select>
          </div>
          <p v-if="errorText" class="error">{{ errorText }}</p>
        </div>
        <footer class="footer">
          <button
            v-if="canDelete"
            type="button"
            class="btn btn-danger"
            :disabled="loading"
            @click="handleDelete"
          >
            删除连线
          </button>
          <span class="footer-spacer" />
          <button type="button" class="btn btn-secondary" :disabled="loading" @click="emit('close')">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="loading">{{ creating ? '添加' : '保存' }}</button>
        </footer>
      </form>
    </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { END_NODE, START_NODE, normalizeEdgeCondition } from '../../utils/planGraphEdit.js'
import { resolveGraphNodeLabel } from '../../utils/planGraphState.js'

const props = defineProps({
  edge: { type: Object, default: null },
  graphSpec: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  creating: { type: Boolean, default: false },
  lockFrom: { type: String, default: '' },
})

const emit = defineEmits(['close', 'save', 'delete'])

const form = reactive({
  from: '',
  to: '',
  condition: 'always',
})

watch(
  () => [props.edge, props.creating, props.lockFrom],
  () => {
    if (props.creating && props.lockFrom) {
      form.from = props.lockFrom
      form.to = defaultToTarget()
      form.condition = 'always'
      return
    }
    form.from = props.edge?.from || ''
    form.to = props.edge?.to || ''
    form.condition = normalizeEdgeCondition(props.edge?.condition)
  },
  { immediate: true },
)

function defaultToTarget() {
  const ids = (props.graphSpec?.nodes || []).map((n) => n.id).filter(Boolean)
  const other = ids.find((id) => id !== props.lockFrom)
  return other || END_NODE
}

const nodeIds = computed(() => (props.graphSpec?.nodes || []).map((n) => n.id).filter(Boolean))

const isStartEdge = computed(() => props.edge?.from === START_NODE)
const isEndEdge = computed(() => props.edge?.to === END_NODE)
const fromLocked = computed(() => isStartEdge.value || (props.creating && Boolean(props.lockFrom)))

const canDelete = computed(() => !props.creating && !isStartEdge.value && !isEndEdge.value)

const edgeSummary = computed(() => {
  if (props.creating && props.lockFrom) {
    return `${props.lockFrom} → …`
  }
  const from = props.edge?.from || '?'
  const to = props.edge?.to || '?'
  const cond = normalizeEdgeCondition(props.edge?.condition)
  return `${from} → ${to} (${cond})`
})

const errorText = computed(() => {
  if (!form.from || !form.to) return '请选择起点和终点'
  if (form.from === form.to) return '起点与终点不能相同'
  if (form.from === END_NODE || form.to === START_NODE) return '无效的连线方向'
  if (form.to !== END_NODE && !nodeIds.value.includes(form.to)) return '终点节点不存在'
  if (form.from !== START_NODE && !nodeIds.value.includes(form.from)) return '起点节点不存在'
  const dup = (props.graphSpec?.edges || []).some(
    (e) => e.from === form.from
      && e.to === form.to
      && normalizeEdgeCondition(e.condition) === form.condition,
  )
  if (dup) {
    if (props.creating) return '相同条件的连线已存在'
    const same = props.edge
      && form.from === props.edge.from
      && form.to === props.edge.to
      && normalizeEdgeCondition(form.condition) === normalizeEdgeCondition(props.edge.condition)
    if (!same) return '相同条件的连线已存在'
  }
  return ''
})

function nodeLabel(nodeId) {
  return resolveGraphNodeLabel(props.graphSpec, nodeId) || nodeId
}

function handleSubmit() {
  if (errorText.value) return
  emit('save', {
    from: form.from,
    to: form.to,
    condition: form.condition,
  })
}

function handleDelete() {
  if (!canDelete.value) return
  emit('delete')
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1500;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.card {
  width: min(420px, 100%);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #202124;
}
.edge-id {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #5f6368;
}
.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #5f6368;
  padding: 4px;
  border-radius: 6px;
}
.close-btn:hover {
  background: #f1f3f4;
}
.form-body {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #3c4043;
  margin-bottom: 4px;
}
.field select {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 13px;
}
.error {
  margin: 0;
  font-size: 12px;
  color: #c5221f;
}
.footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
.footer-spacer {
  flex: 1;
}
.btn {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-secondary {
  background: #fff;
  border-color: #dadce0;
  color: #3c4043;
}
.btn-primary {
  background: #1a73e8;
  color: #fff;
}
.btn-danger {
  background: #fce8e6;
  border-color: #f28b82;
  color: #c5221f;
}
</style>
