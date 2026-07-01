<template>
  <div class="hub-page">
    <div class="hub-layout">
      <header class="hub-hero">
        <span class="hub-badge">Pando-Mesh</span>
        <h1 class="hub-title">
          Manage <span class="accent">requirements</span> and workspace sessions.
        </h1>
        <p class="hub-lead">
          配置工作流模板，并浏览需求目录以创建或打开 Session。作业空间路径请在顶栏配置。
        </p>
      </header>
      <HubNavCards :active-tab="activeTab" @navigate="emit('navigate', $event)" />
    </div>

    <div class="hub-sections">
      <section class="hub-content-card">
        <h2 class="content-card-title">工作流模板</h2>
        <div class="switch-row">
          <span class="switch-label">使用工作流模板</span>
          <label class="toggle">
            <input
              :checked="useWorkflow"
              type="checkbox"
              class="toggle-input"
              @change="emit('update:useWorkflow', $event.target.checked); emit('use-workflow-change')"
            />
            <span class="toggle-track" aria-hidden="true" />
          </label>
        </div>
        <select
          v-if="useWorkflow"
          :value="defaultTemplateId"
          class="field-input template-select"
          @change="emit('update:defaultTemplateId', $event.target.value); emit('default-template-change')"
        >
          <option value="">请选择模板…</option>
          <option v-for="tpl in workflowTemplates" :key="tpl.template_id" :value="tpl.template_id">
            {{ tpl.name }}
          </option>
        </select>
        <p class="content-hint">
          {{ useWorkflow
            ? '新建 Session 时引用所选模板；已有 Session 可点「初始化」套用新模板；模板编辑请在右上角「配置」中管理'
            : '关闭后由 AI 动态规划生成编排拓扑' }}
        </p>
      </section>

      <section class="hub-content-card hub-content-card-grow">
        <div class="section-head">
          <h2 class="content-card-title">需求列表</h2>
          <button type="button" class="btn btn-small" :disabled="reqLoading" @click="emit('refresh')">
            {{ reqLoading ? '…' : '刷新' }}
          </button>
        </div>
        <p v-if="reqError" class="page-error">{{ reqError }}</p>
        <div v-else-if="requirements.length" class="req-batch-bar">
          <label class="req-select-all" @click.stop>
            <input
              type="checkbox"
              :checked="allRequirementsChecked"
              :disabled="batchBusy"
              @change="emit('toggle-select-all')"
            />
            <span>全选</span>
          </label>
          <div class="req-actions">
            <button
              type="button"
              class="btn-play"
              :disabled="!checkedRequirementCount || batchBusy"
              title="批量启动"
              @click="emit('batch-start')"
            >
              <svg class="play-icon" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M5 3.5v9l7-4.5z" fill="currentColor" />
              </svg>
            </button>
            <button
              v-if="useWorkflow && defaultTemplateId"
              type="button"
              class="btn btn-init"
              :disabled="!checkedRequirementCount || batchBusy"
              title="批量初始化"
              @click="emit('batch-init')"
            >
              {{ batchBusy ? '…' : '初始化' }}
            </button>
          </div>
        </div>
        <ul v-if="!reqError" class="req-list">
          <li
            v-for="item in requirements"
            :key="item.requirement_id"
            :class="{ active: item.requirement_id === selectedRequirementId, checked: isRequirementChecked(item.requirement_id) }"
            @click="emit('select-requirement', item)"
          >
            <label class="req-check" @click.stop>
              <input
                type="checkbox"
                :checked="isRequirementChecked(item.requirement_id)"
                :disabled="batchBusy"
                @change="emit('toggle-check', item.requirement_id)"
              />
            </label>
            <div class="req-main">
              <span class="req-name">{{ item.name }}</span>
              <span v-if="item.summary" class="req-summary">{{ item.summary }}</span>
            </div>
            <div class="req-badges">
              <div v-if="item.has_session || (useWorkflow && defaultTemplateId)" class="req-row-actions">
                <button
                  v-if="item.has_session && !item.running"
                  type="button"
                  class="btn-play"
                  :disabled="reqStartId === item.requirement_id || reqOpeningId === item.requirement_id || batchBusy || (item.workflow_id === workflowId && (executing || awaitingPending))"
                  title="启动本需求工作流"
                  @click.stop="emit('start-requirement', item)"
                >
                  <svg class="play-icon" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M5 3.5v9l7-4.5z" fill="currentColor" />
                  </svg>
                </button>
                <button
                  v-if="useWorkflow && defaultTemplateId"
                  type="button"
                  class="btn btn-init"
                  :disabled="reqInitId === item.requirement_id || batchBusy"
                  @click.stop="emit('init-requirement', item)"
                >
                  {{ reqInitId === item.requirement_id ? '…' : '初始化' }}
                </button>
              </div>
              <span v-if="item.running" class="wf-badge">执行中</span>
              <span v-else-if="item.has_session" class="req-tag">Session</span>
            </div>
          </li>
        </ul>
        <p v-if="!reqLoading && !reqError && workspacePath && !requirements.length" class="page-empty">
          未找到需求子目录
        </p>
        <p class="content-hint req-list-hint">需求来自 <code>{workspace}/requirements/</code> 子目录；点击需求将打开 WorkFlow 视图</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import HubNavCards from './HubNavCards.vue'

defineProps({
  workspacePath: { type: String, default: '' },
  useWorkflow: { type: Boolean, default: true },
  defaultTemplateId: { type: String, default: '' },
  workflowTemplates: { type: Array, default: () => [] },
  requirements: { type: Array, default: () => [] },
  selectedRequirementId: { type: String, default: '' },
  workflowId: { type: String, default: '' },
  reqLoading: { type: Boolean, default: false },
  reqError: { type: String, default: '' },
  reqOpeningId: { type: String, default: '' },
  reqInitId: { type: String, default: '' },
  reqStartId: { type: String, default: '' },
  batchBusy: { type: Boolean, default: false },
  checkedRequirementCount: { type: Number, default: 0 },
  allRequirementsChecked: { type: Boolean, default: false },
  executing: { type: Boolean, default: false },
  awaitingPending: { type: Boolean, default: false },
  activeTab: { type: String, default: 'requirements' },
  isRequirementChecked: { type: Function, required: true },
})

const emit = defineEmits([
  'update:workspacePath',
  'update:useWorkflow',
  'update:defaultTemplateId',
  'workspace-change',
  'use-workflow-change',
  'default-template-change',
  'refresh',
  'toggle-select-all',
  'toggle-check',
  'select-requirement',
  'start-requirement',
  'init-requirement',
  'batch-start',
  'batch-init',
  'navigate',
])
</script>

<style scoped>
.hub-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 40px 32px 48px;
}
.hub-layout {
  display: grid;
  grid-template-columns: 1fr min(400px, 42%);
  gap: 48px 40px;
  align-items: start;
  margin-bottom: 32px;
}
.hub-hero {
  padding-top: 8px;
}
.hub-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--pm-accent-requirements-soft);
  color: var(--pm-accent-requirements);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 20px;
}
.hub-title {
  margin: 0 0 16px;
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--pm-text);
}
.hub-title .accent {
  color: var(--pm-accent-requirements);
}
.hub-lead {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--pm-text-secondary);
  max-width: 520px;
}
.hub-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hub-content-card {
  padding: 24px 28px;
  border-radius: var(--pm-radius-lg);
  border: 1px solid var(--pm-border);
  background: var(--pm-surface);
  box-shadow: var(--pm-shadow);
}
.hub-content-card-grow {
  flex: 1;
}
.content-card-title {
  margin: 0 0 14px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--pm-text-muted);
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.section-head .content-card-title {
  margin: 0;
}
.field-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--pm-border-strong);
  border-radius: var(--pm-radius);
  font-size: 13px;
  background: var(--pm-surface);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus {
  outline: none;
  border-color: var(--pm-primary);
  box-shadow: 0 0 0 3px var(--pm-primary-soft);
}
.content-hint {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--pm-text-secondary);
  line-height: 1.6;
}
.content-hint code {
  font-size: 12px;
}
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.switch-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--pm-text);
}
.template-select {
  margin-top: 4px;
}
.toggle {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
  cursor: pointer;
}
.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-track {
  position: relative;
  display: block;
  width: 40px;
  height: 22px;
  border-radius: 999px;
  background: var(--pm-border-strong);
  transition: background 0.2s;
}
.toggle-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s;
}
.toggle-input:checked + .toggle-track {
  background: var(--pm-primary);
}
.toggle-input:checked + .toggle-track::after {
  transform: translateX(18px);
}
.page-error {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--pm-danger);
}
.page-empty {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--pm-text-secondary);
}
.req-list-hint {
  margin-top: 14px;
}
.btn-small {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--pm-border-strong);
  border-radius: var(--pm-radius);
  background: var(--pm-surface);
  cursor: pointer;
}
.btn-small:hover:not(:disabled) {
  border-color: var(--pm-primary-muted);
  color: var(--pm-primary);
}
.req-batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: var(--pm-radius);
  background: var(--pm-surface-muted);
  border: 1px solid var(--pm-border);
}
.req-select-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--pm-text-secondary);
  cursor: pointer;
}
.req-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.req-list li {
  padding: 12px 14px;
  border-radius: var(--pm-radius);
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;
}
.req-list li:hover {
  background: var(--pm-surface-muted);
}
.req-list li.active {
  background: var(--pm-primary-soft);
  border-color: var(--pm-primary-muted);
}
.req-check {
  padding-top: 2px;
  flex-shrink: 0;
  cursor: pointer;
}
.req-main {
  flex: 1;
  min-width: 0;
}
.req-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--pm-text);
}
.req-summary {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--pm-text-secondary);
  line-height: 1.4;
}
.req-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}
.req-row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.btn-play {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: var(--pm-primary-soft);
  color: var(--pm-primary);
  cursor: pointer;
}
.btn-play:hover:not(:disabled) {
  background: var(--pm-primary-muted);
}
.play-icon {
  width: 14px;
  height: 14px;
}
.btn-init {
  padding: 3px 10px;
  font-size: 11px;
  border-radius: 999px;
  border: 1px solid var(--pm-primary-muted);
  background: var(--pm-primary-soft);
  color: var(--pm-primary-hover);
  cursor: pointer;
}
.wf-badge {
  font-size: 10px;
  color: var(--pm-accent-workflow);
  background: var(--pm-accent-workflow-soft);
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.req-tag {
  font-size: 10px;
  color: var(--pm-text-secondary);
  background: var(--pm-surface-muted);
  padding: 2px 8px;
  border-radius: 999px;
}
@media (max-width: 900px) {
  .hub-layout {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .hub-page {
    padding: 24px 20px 32px;
  }
}
</style>
