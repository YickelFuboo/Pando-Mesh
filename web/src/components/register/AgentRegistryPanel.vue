<template>
  <div class="agent-panel">
    <div class="panel-toolbar">
      <div>
        <h2>Agent 注册</h2>
        <p class="hint">
          内置 Agent 默认在 <code>app/register/seed.py</code>；
          <code>data/agents/</code> 仅存放您<strong>保存过的修改</strong>（如 <code>claude_code.json</code>）。
        </p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreate">注册 Agent</button>
    </div>

    <div v-if="loading" class="empty-state">加载中…</div>
    <div v-else-if="loadError" class="empty-state error">{{ loadError }}</div>
    <div v-else-if="!agents.length" class="empty-state">暂无 Agent，请先注册。</div>
    <div v-else class="agent-grid">
      <article
        v-for="agent in agents"
        :key="agent.agent_id"
        class="agent-card"
        :class="{ builtin: agent.builtin }"
      >
        <header class="card-head">
          <div>
            <h3>{{ agent.name || agent.agent_id }}</h3>
            <code>{{ agent.agent_id }}</code>
          </div>
          <span class="kind-badge">{{ kindLabel(agent.kind) }}</span>
        </header>
        <p class="desc">{{ agent.description || '无描述' }}</p>
        <div class="card-meta">
          <div class="card-tags">
            <span v-if="agent.builtin" class="tag tag-builtin">内置</span>
            <span v-else class="tag tag-custom">自定义</span>
          </div>
          <div class="switch-row">
            <span class="switch-label">启用</span>
            <label class="toggle" :class="{ disabled: togglingId === agent.agent_id }">
              <input
                type="checkbox"
                class="toggle-input"
                :checked="isAgentEnabled(agent)"
                :disabled="togglingId === agent.agent_id"
                @change="onToggleChange(agent, $event)"
              />
              <span class="toggle-track" aria-hidden="true" />
            </label>
          </div>
        </div>
        <footer class="card-actions">
          <button type="button" class="btn" @click="openEdit(agent)">编辑配置</button>
          <button
            v-if="!agent.builtin"
            type="button"
            class="btn btn-danger"
            :disabled="deletingId === agent.agent_id"
            @click="onDelete(agent)"
          >
            {{ deletingId === agent.agent_id ? '删除中…' : '删除' }}
          </button>
        </footer>
      </article>
    </div>

    <div v-if="dialogVisible" class="overlay" @mousedown.self="closeDialog">
      <div class="dialog" role="dialog">
        <header class="dialog-head">
          <h3>{{ dialogMode === 'create' ? '注册 Agent' : '编辑 Agent' }}</h3>
          <button type="button" class="close-btn" aria-label="关闭" @click="closeDialog">×</button>
        </header>
        <form class="dialog-body" @submit.prevent="onSubmit">
          <div class="field">
            <label for="ar-id">Agent ID</label>
            <input
              id="ar-id"
              v-model="form.agent_id"
              type="text"
              :readonly="dialogMode === 'edit'"
              placeholder="my_custom_agent"
            />
          </div>
          <div class="field">
            <label for="ar-name">名称</label>
            <input
              id="ar-name"
              v-model="form.name"
              type="text"
              :readonly="false"
              placeholder="显示名称"
            />
          </div>
          <div class="field">
            <label for="ar-kind">类型</label>
            <select
              id="ar-kind"
              v-model="form.kind"
              :disabled="dialogMode === 'edit' && viewing?.builtin"
              @change="onKindChange"
            >
              <option value="native">自研 (native)</option>
              <option value="codex_sdk">Codex SDK</option>
              <option value="claude_code_cli">Claude Code CLI</option>
              <option value="api">第三方 API</option>
            </select>
          </div>
          <div class="field">
            <label for="ar-desc">描述</label>
            <textarea
              id="ar-desc"
              v-model="form.description"
              rows="2"
              :readonly="false"
              placeholder="Agent 用途说明"
            />
          </div>
          <div v-if="isReactKind" class="field">
            <label>执行器</label>
            <p class="field-hint">
              ReAct 类型 Agent，只需指定 <code>agent_type</code>，<strong>无需 URL / Body</strong>。
              第三方模型接入请在顶栏「模型设置」统一配置。
            </p>
            <input type="text" class="mono" readonly :value="reactAgentTypeLabel" />
          </div>
          <div v-else class="field">
            <label for="ar-exec">Executor 模板 (JSON)</label>
            <p v-if="showCliSessionFields" class="field-hint">
              仅含命令、工作目录、超时等；<code>cli.session</code> 在下方两框单独编辑，保存时自动合并。
            </p>
            <textarea
              id="ar-exec"
              v-model="form.executor_template_text"
              class="mono"
              rows="10"
              spellcheck="false"
              placeholder='{"kind":"cli","cli":{...}}'
            />
          </div>
          <div v-if="showCliSessionFields" class="field">
            <label for="ar-session">CLI Session 续跑（cli.session）</label>
            <p class="field-hint">
              含 <code>enabled</code>、<code>resume_args</code>、
              <code>read_session_id_from_json</code> 等；保存时写入 <code>cli.session</code>。
            </p>
            <textarea
              id="ar-session"
              v-model="form.session_config_text"
              class="mono"
              rows="5"
              spellcheck="false"
              :readonly="false"
            />
          </div>
          <div v-if="showCliSessionFields" class="field">
            <label for="ar-history-dir">Claude 配置目录（config_dir）</label>
            <input
              id="ar-history-dir"
              v-model="form.history_config_dir"
              type="text"
              class="mono"
              placeholder="~/.claude"
            />
            <p class="field-hint">
              从 Claude Code JSONL 会话文件读取历史；数据根目录默认 <code>~/.claude</code>，也可设环境变量
              <code>CLAUDE_CONFIG_DIR</code>（显式填写优先）。路径：
              <code>{config_dir}/projects/{工作目录编码}/{session_id}.jsonl</code>
            </p>
          </div>
          <div class="switch-row dialog-switch">
            <span class="switch-label">{{ dialogMode === 'create' ? '注册后启用' : '启用' }}</span>
            <label class="toggle">
              <input v-model="form.enabled" type="checkbox" class="toggle-input" />
              <span class="toggle-track" aria-hidden="true" />
            </label>
          </div>
          <p v-if="dialogMode === 'edit'" class="field-hint save-hint">
            保存后写入 <code>data/agents/{{ form.agent_id || 'agent_id' }}.json</code>（覆盖 seed 默认）；
            未保存过则仍使用 seed.py 内置模板。
          </p>
          <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
          <footer class="dialog-foot">
            <button type="button" class="btn" @click="closeDialog">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '保存中…' : (dialogMode === 'create' ? '注册' : '保存') }}
            </button>
          </footer>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getAgentKindDefaults, listAgents, registerAgent, unregisterAgent, updateAgent } from '../../api/layerApi.js'
import { applyKindDefaultsToForm, fillAgentForm, historyConfigFromForm, mergeCliSessionIntoExecutor } from '../../utils/agentRegistryForm.js'

const emit = defineEmits(['changed'])

const agents = ref([])
const loading = ref(false)
const loadError = ref('')
const dialogVisible = ref(false)
const dialogMode = ref('create')
const viewing = ref(null)
const submitting = ref(false)
const deletingId = ref('')
const togglingId = ref('')
const errorMsg = ref('')

const form = reactive({
  agent_id: '',
  name: '',
  kind: 'claude_code_cli',
  description: '',
  executor_template_text: '',
  session_config_text: '{}',
  history_config_dir: '~/.claude',
  history_config_text: '{}',
  enabled: true,
})

const KIND_LABELS = {
  native: '自研',
  codex_sdk: 'Codex SDK',
  claude_code_cli: 'Claude Code CLI',
  api: '第三方 API',
}

function kindLabel(kind) {
  return KIND_LABELS[kind] || kind
}

const isReactKind = computed(() => form.kind === 'api' || form.kind === 'native')
const showCliSessionFields = computed(() => form.kind === 'claude_code_cli')

const reactAgentTypeLabel = computed(() => {
  if (form.kind === 'api') {
    return 'ThirdPartyApi（kind: react）'
  }
  return 'AiDeveloper（kind: react）'
})

function buildReactExecutorTemplate() {
  return {
    kind: 'react',
    agent_type: form.kind === 'api' ? 'ThirdPartyApi' : 'AiDeveloper',
  }
}

function isAgentEnabled(agent) {
  return agent?.enabled !== false
}

async function applyKindDefaults(kind) {
  const defaults = await getAgentKindDefaults(kind)
  applyKindDefaultsToForm(form, defaults)
}

async function resetForm(kind = 'claude_code_cli') {
  form.agent_id = ''
  form.name = ''
  form.kind = kind
  form.description = ''
  form.enabled = true
  errorMsg.value = ''
  try {
    await applyKindDefaults(kind)
  } catch (e) {
    errorMsg.value = e?.message || '加载默认模板失败'
  }
}

async function onKindChange() {
  if (dialogMode.value !== 'create') {
    return
  }
  const agentId = form.agent_id
  const name = form.name
  const description = form.description
  const enabled = form.enabled
  const kind = form.kind
  await resetForm(kind)
  form.agent_id = agentId
  form.name = name
  form.description = description
  form.enabled = enabled
}

function fillFormFromAgent(agent) {
  fillAgentForm(form, agent)
  errorMsg.value = ''
}

async function refresh() {
  loading.value = true
  loadError.value = ''
  try {
    agents.value = await listAgents()
  } catch (e) {
    agents.value = []
    loadError.value = e?.message || '加载 Agent 列表失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  viewing.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(agent) {
  dialogMode.value = 'edit'
  viewing.value = agent
  fillFormFromAgent(agent)
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
  errorMsg.value = ''
}

function parseJsonField(text, fieldName) {
  const raw = String(text || '').trim()
  if (!raw || raw === '{}') return {}
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error(`${fieldName} 必须是 JSON 对象`)
    }
    return parsed
  } catch (e) {
    throw new Error(`${fieldName} JSON 无效：${e.message}`)
  }
}

async function onSubmit() {
  errorMsg.value = ''
  if (!String(form.agent_id || '').trim()) {
    errorMsg.value = '请填写 Agent ID'
    return
  }
  submitting.value = true
  try {
    let executorTemplate
    let sessionConfig = {}
    let historyConfig = {}
    if (isReactKind.value) {
      executorTemplate = buildReactExecutorTemplate()
    } else {
      sessionConfig = parseJsonField(form.session_config_text, 'Session 配置')
      historyConfig = historyConfigFromForm(form)
      executorTemplate = mergeCliSessionIntoExecutor(
        parseJsonField(form.executor_template_text, 'Executor 模板'),
        sessionConfig,
        historyConfig,
      )
    }
    if (dialogMode.value === 'create') {
      const payload = {
        agent_id: form.agent_id.trim(),
        name: form.name.trim(),
        kind: form.kind,
        description: form.description.trim(),
        executor_template: executorTemplate,
        session_config: sessionConfig,
        history_config: historyConfig,
        enabled: form.enabled,
      }
      await registerAgent(payload)
    } else {
      const payload = {
        name: form.name.trim(),
        kind: form.kind,
        description: form.description.trim(),
        executor_template: executorTemplate,
        session_config: sessionConfig,
        history_config: historyConfig,
        enabled: form.enabled,
      }
      await updateAgent(form.agent_id.trim(), payload)
    }
    closeDialog()
    await refresh()
    emit('changed')
  } catch (e) {
    errorMsg.value = e?.message || (dialogMode.value === 'create' ? '注册失败' : '保存失败')
  } finally {
    submitting.value = false
  }
}

async function onToggleChange(agent, event) {
  if (!agent?.agent_id || togglingId.value) return
  const input = event.target
  const nextEnabled = input.checked
  const prevEnabled = isAgentEnabled(agent)
  if (nextEnabled === prevEnabled) return
  togglingId.value = agent.agent_id
  try {
    const updated = await updateAgent(agent.agent_id, { enabled: nextEnabled })
    const enabled = updated.enabled !== false
    agent.enabled = enabled
    if (viewing.value?.agent_id === agent.agent_id) {
      viewing.value = { ...viewing.value, enabled }
      form.enabled = enabled
    }
    await refresh()
    emit('changed')
  } catch (e) {
    input.checked = prevEnabled
    alert(e?.message || '更新启用状态失败')
  } finally {
    togglingId.value = ''
  }
}

async function onDelete(agent) {
  if (!agent?.agent_id || agent.builtin) return
  if (!window.confirm(`确定删除 Agent「${agent.name || agent.agent_id}」？`)) return
  deletingId.value = agent.agent_id
  try {
    await unregisterAgent(agent.agent_id)
    await refresh()
    emit('changed')
  } catch (e) {
    alert(e?.message || '删除失败')
  } finally {
    deletingId.value = ''
  }
}

onMounted(refresh)

defineExpose({ refresh })
</script>

<style scoped>
.agent-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}
.panel-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 16px;
}
.panel-toolbar h2 {
  margin: 0 0 4px;
  font-size: 16px;
}
.save-hint {
  margin-top: 4px;
}

.field-hint {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-muted, #8c8c8c);
}

.field-hint code {
  font-size: 11px;
}

.hint {
  margin: 0;
  font-size: 13px;
  color: #5f6368;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.agent-card {
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.agent-card.builtin {
  border-color: #c6dafc;
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}
.card-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
}
.card-head code {
  font-size: 11px;
  color: #5f6368;
  background: #f1f3f4;
  padding: 2px 6px;
  border-radius: 4px;
}
.kind-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e8f0fe;
  color: #1557b0;
  white-space: nowrap;
}
.desc {
  margin: 0;
  font-size: 13px;
  color: #3c4043;
  line-height: 1.5;
  flex: 1;
}
.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.switch-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.switch-label {
  font-size: 12px;
  color: #5f6368;
}
.dialog-switch {
  margin-bottom: 8px;
}
.toggle {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
  cursor: pointer;
}
.toggle.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-input:disabled + .toggle-track {
  opacity: 0.55;
  cursor: not-allowed;
}
.toggle-track {
  position: relative;
  display: block;
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: #dadce0;
  transition: background 0.2s;
}
.toggle-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s;
}
.toggle-input:checked + .toggle-track {
  background: #1a73e8;
}
.toggle-input:checked + .toggle-track::after {
  transform: translateX(16px);
}
.toggle-input:focus-visible + .toggle-track {
  box-shadow: 0 0 0 2px #e8f0fe;
}
.tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f3f4;
  color: #5f6368;
}
.tag-builtin { background: #e8f0fe; color: #1557b0; }
.tag-custom { background: #fef7e0; color: #b06000; }
.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.empty-state {
  padding: 48px;
  text-align: center;
  color: #80868b;
  background: #fff;
  border: 1px dashed #dadce0;
  border-radius: 8px;
}
.empty-state.error {
  color: #c5221f;
  border-color: #f28b82;
  background: #fce8e6;
}
.btn {
  padding: 6px 14px;
  border: 1px solid #dadce0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
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
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(32, 33, 36, 0.48);
}
.dialog {
  width: min(640px, 100%);
  max-height: min(90vh, 760px);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.dialog-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #e8eaed;
}
.dialog-head h3 {
  margin: 0;
  font-size: 16px;
}
.close-btn {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #5f6368;
}
.dialog-body {
  padding: 16px 18px;
  overflow: auto;
}
.field {
  margin-bottom: 12px;
}
.field label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #3c4043;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
}
.mono {
  font-family: ui-monospace, Consolas, "Cascadia Mono", monospace;
  font-size: 12px;
}
.error-msg {
  margin: 0 0 8px;
  color: #c5221f;
  font-size: 13px;
}
.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
}
</style>
