<template>
  <section class="chat-panel">
    <header class="panel-tabs">
      <button
        type="button"
        class="panel-tab"
        :class="{ active: activeTab === 'chat' }"
        @click="activeTab = 'chat'"
      >
        对话
      </button>
      <button
        type="button"
        class="panel-tab"
        :class="{ active: activeTab === 'deliverables' }"
        @click="activeTab = 'deliverables'"
      >
        交付件
      </button>
    </header>

    <div v-show="activeTab === 'chat'" ref="scrollEl" class="chat-body">
      <div v-if="!chatItems.length && !loading" class="empty-hint">
        {{ emptyHint }}
      </div>
      <article
        v-for="(item, i) in chatItems"
        :key="i"
        class="chat-item"
        :class="item.role"
      >
        <div class="bubble">
          <div class="bubble-meta">{{ item.label }}</div>
          <div class="bubble-text pm-markdown" v-html="renderMarkdown(item.content)"></div>
        </div>
      </article>
    </div>

    <NodeDeliverablesPanel
      v-show="activeTab === 'deliverables'"
      :workflow-id="workflowId"
      :graph-spec="graphSpec"
      :selected-node-id="selectedNodeId"
      :node-output="nodeOutput"
    />

    <footer v-show="activeTab === 'chat'" class="chat-input-bar">
      <div class="chat-input-float" :class="{ 'is-readonly': inputReadonly }">
        <textarea
          v-model="inputLocal"
          class="chat-input"
          rows="1"
          :placeholder="inputPlaceholder"
          :readonly="inputReadonly || disabled || busy"
          :disabled="disabled && !inputReadonly"
          @keydown.enter.exact.prevent="submitInput"
        />
        <div class="chat-input-toolbar">
          <span v-if="inputReadonly" class="input-tip">只读查看</span>
          <button
            type="button"
            class="chat-send-btn"
            :disabled="sendDisabled"
            @click="submitInput"
          >
            {{ sendLabel }}
          </button>
        </div>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { getNodeMessages, getWorkflowMessages } from '../../api/layerApi.js'
import { renderMarkdown } from '../../utils/markdown.js'
import NodeDeliverablesPanel from './NodeDeliverablesPanel.vue'
import {
  isCliGraphNode,
  resolveNodeSessionId,
} from '../../utils/planGraphState.js'

const props = defineProps({
  workflowId: { type: String, default: '' },
  graphSpec: { type: Object, default: null },
  snapshot: { type: Object, default: null },
  selectedNodeId: { type: String, default: '' },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  executing: { type: Boolean, default: false },
  messageCount: { type: Number, default: 0 },
})

const emit = defineEmits(['revise', 'send'])

const loading = ref(false)
const activeTab = ref('chat')
const chatItems = ref([])
const inputLocal = ref('')
const scrollEl = ref(null)

const nodeOutput = computed(() => {
  const nodeId = props.selectedNodeId
  if (!nodeId) return ''
  return String(props.snapshot?.nodeOutputs?.[nodeId] || '').trim()
})

const isCliNode = computed(() => isCliGraphNode(props.snapshot, props.selectedNodeId))
const nodeHasSession = computed(() => Boolean(resolveNodeSessionId(props.snapshot, props.selectedNodeId)))
const nodeHasOutput = computed(() => Boolean(String(props.snapshot?.nodeOutputs?.[props.selectedNodeId] || '').trim()))
const showRevise = computed(() => Boolean(
  props.selectedNodeId
  && isCliNode.value
  && (nodeHasSession.value || nodeHasOutput.value || (props.snapshot?.runningNodeIds || []).includes(props.selectedNodeId)),
))

const inputMode = computed(() => {
  if (!props.selectedNodeId) return 'orchestration'
  if (showRevise.value) return 'revise'
  return 'readonly'
})

const inputReadonly = computed(() => inputMode.value === 'readonly')

const inputPlaceholder = computed(() => {
  if (inputMode.value === 'orchestration') {
    return props.executing ? '编排执行中…' : '输入「开始执行」或任务指令，Enter 发送'
  }
  if (inputMode.value === 'revise') {
    return '输入修正意见，提交后将重跑当前步骤…'
  }
  return '步骤只读查看中，返回编排视图后可发送指令'
})

const sendLabel = computed(() => {
  if (props.busy) return '提交中…'
  if (inputMode.value === 'revise') return '修正并重跑'
  if (props.executing) return '执行中…'
  return '发送'
})

const sendDisabled = computed(() => {
  if (inputReadonly.value) return true
  if (props.busy) return true
  if (inputMode.value === 'orchestration' && props.executing) return true
  if (props.disabled && inputMode.value !== 'revise') return true
  return !inputLocal.value.trim()
})

const emptyHint = computed(() => {
  if (!props.workflowId) return '请先打开 Workflow Session'
  if (props.selectedNodeId) return '该步骤尚无会话记录，执行后将在此展示'
  return '暂无 Session 执行日志'
})

function placeholder(content, label = '提示') {
  return { role: 'assistant', label, content }
}

function normalizeMessages(rawList, scopeLabel) {
  return (rawList || []).map((msg) => ({
    role: String(msg?.role || 'assistant').toLowerCase(),
    label: msg?.create_time ? `${scopeLabel} · ${msg.create_time}` : scopeLabel,
    content: String(msg?.content || '').trim(),
  })).filter((item) => item.content)
}

async function loadMessagesForView() {
  if (!props.workflowId) {
    chatItems.value = []
    return
  }
  const showLoading = !chatItems.value.length
  if (showLoading) loading.value = true
  try {
    const nodeId = props.selectedNodeId
    if (!nodeId) {
      const msgs = await getWorkflowMessages(props.workflowId)
      chatItems.value = normalizeMessages(msgs, 'Session')
      return
    }
    if (isCliGraphNode(props.snapshot, nodeId)) {
      const nodeSid = resolveNodeSessionId(props.snapshot, nodeId)
      if (!nodeSid) {
        chatItems.value = [placeholder('该步骤尚未执行，暂无 CLI 会话记录。')]
        return
      }
      try {
        const msgs = await getNodeMessages(props.workflowId, nodeId)
        if (!msgs?.length) {
          chatItems.value = [placeholder('CLI 会话暂无可见消息，或会话文件尚未生成。')]
          return
        }
        chatItems.value = normalizeMessages(msgs, 'CLI')
      } catch (err) {
        chatItems.value = [placeholder(
          err?.message
            ? `无法读取 CLI 会话历史：${err.message}`
            : '无法读取 CLI 会话历史，请确认工作目录与会话文件一致。',
        )]
      }
      return
    }
    const output = String(props.snapshot?.nodeOutputs?.[nodeId] || '').trim()
    if (output) {
      chatItems.value = [{
        role: 'assistant',
        label: '步骤产出',
        content: output,
      }]
      return
    }
    if (!resolveNodeSessionId(props.snapshot, nodeId)) {
      chatItems.value = [placeholder('该步骤尚未执行，暂无会话记录。')]
      return
    }
    chatItems.value = [placeholder('该步骤暂无可见 Agent 对话记录。')]
  } finally {
    loading.value = false
    await nextTick()
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  }
}

function submitInput() {
  if (sendDisabled.value) return
  const text = inputLocal.value.trim()
  if (!text) return
  if (inputMode.value === 'revise') {
    emit('revise', text)
  } else if (inputMode.value === 'orchestration') {
    emit('send', text)
  }
  inputLocal.value = ''
}

watch(
  () => props.selectedNodeId,
  () => {
    inputLocal.value = ''
  },
)

watch(
  () => props.selectedNodeId,
  (nodeId) => {
    if (!nodeId && activeTab.value === 'deliverables') {
      activeTab.value = 'chat'
    }
  },
)

watch(
  () => {
    const nodeId = props.selectedNodeId
    const base = [props.workflowId, nodeId]
    if (!nodeId) {
      return [...base, props.messageCount, props.snapshot?.phase]
    }
    return [
      ...base,
      props.messageCount,
      props.snapshot?.nodeOutputs?.[nodeId],
      props.snapshot?.nodeSessionIds?.[nodeId],
      props.snapshot?.phase,
    ]
  },
  () => loadMessagesForView(),
  { immediate: true },
)

defineExpose({ reload: loadMessagesForView })
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  background: var(--pm-surface, #fff);
  overflow: hidden;
}
.panel-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px 0;
  flex-shrink: 0;
  background: var(--pm-surface, #fff);
}
.panel-tab {
  padding: 6px 12px;
  border: none;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: #5f6368;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.panel-tab.active {
  color: var(--pm-primary, #1677ff);
  background: #f5f8ff;
  box-shadow: inset 0 -2px 0 var(--pm-primary, #1677ff);
}
.loading-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--pm-primary, #1677ff);
}
.chat-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px;
  background: var(--pm-surface, #fff);
}
.empty-hint {
  color: #80868b;
  font-size: 13px;
  text-align: center;
  padding: 24px 12px;
}
.chat-item {
  display: flex;
  margin-bottom: 10px;
}
.chat-item.user {
  justify-content: flex-end;
}
.chat-item.assistant,
.chat-item.system {
  justify-content: flex-start;
}
.bubble {
  max-width: 92%;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 10px;
  padding: 8px 10px;
}
.chat-item.user .bubble {
  background: var(--pm-primary-soft, #e6f4ff);
  border-color: #bae0ff;
}
.bubble-meta {
  font-size: 10px;
  color: #80868b;
  margin-bottom: 4px;
}
.bubble-text {
  margin: 0;
  word-break: break-word;
  font-size: 13px;
  font-family: inherit;
}
.bubble-text.pm-markdown {
  line-height: 1.7;
}
.chat-foot,
.chat-input-bar {
  padding: 8px 12px 10px;
  background: var(--pm-surface, #fff);
  flex-shrink: 0;
}
.chat-input-float {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 8px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}
.chat-input-float.is-readonly {
  background: #fafbfc;
  box-shadow: 0 1px 8px rgba(15, 23, 42, 0.05);
}
.chat-input-bar textarea,
.chat-foot textarea,
.chat-input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px 2px;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.4;
  resize: none;
  min-height: 34px;
  max-height: 120px;
  background: transparent;
  color: #202124;
}
.chat-input::placeholder {
  color: #9aa0a6;
}
.chat-input:read-only {
  color: #80868b;
  cursor: not-allowed;
}
.chat-input-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 0 8px 6px 10px;
}
.input-tip {
  margin-right: auto;
  font-size: 12px;
  color: #80868b;
}
.chat-send-btn {
  flex-shrink: 0;
  padding: 4px 14px;
  border: none;
  border-radius: 999px;
  background: var(--pm-primary, #1677ff);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.3;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(22, 119, 255, 0.25);
  transition: opacity 0.15s, transform 0.1s;
}
.chat-send-btn:hover:not(:disabled) {
  opacity: 0.92;
}
.chat-send-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.chat-send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
