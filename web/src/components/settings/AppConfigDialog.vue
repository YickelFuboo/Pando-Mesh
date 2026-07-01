<template>
  <div v-if="visible" class="overlay" @mousedown.self="close">
    <div class="config-dialog" role="dialog" aria-labelledby="config-title">
      <header class="drawer-head">
        <div>
          <h2 id="config-title">配置</h2>
          <p class="sub">系统、模板与 Agent 管理</p>
        </div>
        <button type="button" class="close-btn" aria-label="关闭" @click="close">×</button>
      </header>

      <div class="drawer-layout">
        <nav class="config-nav" aria-label="配置分类">
          <button
            type="button"
            class="config-nav-btn"
            :class="{ active: configTab === 'models' }"
            @click="switchTab('models')"
          >
            模型服务
          </button>
          <button
            type="button"
            class="config-nav-btn"
            :class="{ active: configTab === 'templates' }"
            @click="switchTab('templates')"
          >
            模板管理
          </button>
          <button
            type="button"
            class="config-nav-btn"
            :class="{ active: configTab === 'agents' }"
            @click="switchTab('agents')"
          >
            Agent 注册
          </button>
        </nav>

        <div class="config-content">
          <ModelSettingsPanel
            v-show="configTab === 'models'"
            ref="modelPanelRef"
            @saved="onModelsSaved"
          />
          <WorkflowTemplatePanel
            v-if="configTab === 'templates'"
            ref="templatePanelRef"
            @changed="emit('templates-changed')"
          />
          <AgentRegistryPanel
            v-if="configTab === 'agents'"
            ref="agentPanelRef"
            @changed="emit('agents-changed')"
          />
        </div>
      </div>

      <footer v-if="configTab === 'models'" class="drawer-foot">
        <button type="button" class="btn" @click="close">取消</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="modelPanelRef?.loading || modelPanelRef?.saving"
          @click="saveModels"
        >
          {{ modelPanelRef?.saving ? '保存中…' : '保存配置' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import AgentRegistryPanel from '../register/AgentRegistryPanel.vue'
import WorkflowTemplatePanel from '../template/WorkflowTemplatePanel.vue'
import ModelSettingsPanel from './ModelSettingsPanel.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'models-saved', 'templates-changed', 'agents-changed'])

const configTab = ref('models')
const modelPanelRef = ref(null)
const templatePanelRef = ref(null)
const agentPanelRef = ref(null)

function switchTab(tab) {
  configTab.value = tab
  if (tab === 'templates') {
    nextTick(() => templatePanelRef.value?.refresh?.())
  } else if (tab === 'agents') {
    nextTick(() => agentPanelRef.value?.refresh?.())
  }
}

async function saveModels() {
  await modelPanelRef.value?.onSave?.()
}

function onModelsSaved(data) {
  emit('models-saved', data)
}

function close() {
  emit('close')
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    configTab.value = 'models'
    nextTick(() => modelPanelRef.value?.loadConfig?.())
  },
)
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1400;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(32, 33, 36, 0.42);
}
.config-dialog {
  width: min(920px, 100%);
  max-height: min(88vh, 860px);
  background: var(--pm-surface);
  display: flex;
  flex-direction: column;
  border-radius: var(--pm-radius-lg);
  box-shadow: var(--pm-shadow-lg);
  overflow: hidden;
}
.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--pm-border);
  flex-shrink: 0;
}
.drawer-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--pm-text-secondary);
}
.close-btn {
  border: none;
  background: transparent;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: #5f6368;
}
.drawer-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}
.config-nav {
  width: 148px;
  flex-shrink: 0;
  padding: 12px 10px;
  border-right: 1px solid #e8eaed;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.config-nav-btn {
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #5f6368;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}
.config-nav-btn.active {
  background: var(--pm-primary-soft);
  color: var(--pm-primary);
}
.config-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
}
.config-content :deep(.template-panel),
.config-content :deep(.agent-panel) {
  min-height: 100%;
}
.drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid #e8eaed;
  background: #fafbfc;
  flex-shrink: 0;
}
.btn {
  padding: 7px 16px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary {
  background: var(--pm-primary);
  border-color: var(--pm-primary);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: var(--pm-primary-hover);
  border-color: var(--pm-primary-hover);
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
