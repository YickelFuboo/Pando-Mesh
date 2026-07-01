<template>
  <div class="model-settings-panel">
    <section class="status-row">
      <span class="status-badge" :class="{ on: config?.available }">
        {{ config?.available ? 'LLM 可用' : 'LLM 未配置' }}
      </span>
      <span v-if="config?.resolved?.provider" class="resolved">
        当前：{{ config.resolved.provider }} / {{ config.resolved.model }}
      </span>
    </section>

    <p v-if="config?.models_file" class="file-hint">
      配置文件：<code>{{ config.models_file }}</code>
    </p>

    <div v-if="loading" class="panel-empty">加载中…</div>
    <div v-else-if="loadError" class="panel-empty error">{{ loadError }}</div>
    <form v-else class="settings-form" @submit.prevent="onSave">
      <section class="form-section">
        <h3>默认模型</h3>
        <div class="field-row">
          <label>
            Provider
            <select v-model="form.defaultProvider">
              <option value="">请选择</option>
              <option v-for="id in providerIds" :key="'d-' + id" :value="id">
                {{ providerLabel(id) }}
              </option>
            </select>
          </label>
          <label>
            Model
            <select v-model="form.defaultModel" :disabled="!form.defaultProvider">
              <option value="">请选择</option>
              <option
                v-for="modelId in modelsForProvider(form.defaultProvider)"
                :key="'dm-' + modelId"
                :value="modelId"
              >
                {{ modelId }}
              </option>
            </select>
          </label>
        </div>
      </section>

      <section class="form-section">
        <h3>降级模型</h3>
        <div class="field-row">
          <label>
            Provider
            <select v-model="form.fallbackProvider">
              <option value="">请选择</option>
              <option v-for="id in providerIds" :key="'f-' + id" :value="id">
                {{ providerLabel(id) }}
              </option>
            </select>
          </label>
          <label>
            Model
            <select v-model="form.fallbackModel" :disabled="!form.fallbackProvider">
              <option value="">请选择</option>
              <option
                v-for="modelId in modelsForProvider(form.fallbackProvider)"
                :key="'fm-' + modelId"
                :value="modelId"
              >
                {{ modelId }}
              </option>
            </select>
          </label>
        </div>
      </section>

      <section class="form-section">
        <h3>Provider 配置</h3>
        <p class="section-hint">启用 Provider 并填写 API Key 后，AI 建图与 Judge 方可使用对应模型。</p>
        <article
          v-for="provId in providerIds"
          :key="provId"
          class="provider-card"
          :class="{ enabled: providerForms[provId]?.is_valid }"
        >
          <header class="provider-head">
            <label class="toggle-check">
              <input v-model="providerForms[provId].is_valid" type="checkbox" />
              <strong>{{ providerLabel(provId) }}</strong>
            </label>
            <code>{{ provId }}</code>
          </header>
          <p v-if="providerForms[provId].description" class="provider-desc">
            {{ providerForms[provId].description }}
          </p>
          <label class="field-full">
            Base URL
            <input v-model="providerForms[provId].base_url" type="text" class="mono" />
          </label>
          <label class="field-full">
            API Key
            <input
              v-model="providerForms[provId].api_key"
              type="password"
              class="mono"
              :placeholder="providerForms[provId].api_key_set ? '已配置，留空则不修改' : '填写 API Key'"
              autocomplete="off"
            />
          </label>
        </article>
      </section>

      <p v-if="saveError" class="save-error">{{ saveError }}</p>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { getLlmConfig, updateLlmConfig } from '../../api/layerApi.js'

const API_KEY_MASK = '********'

const emit = defineEmits(['saved'])

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const saveError = ref('')
const config = ref(null)

const form = reactive({
  defaultProvider: '',
  defaultModel: '',
  fallbackProvider: '',
  fallbackModel: '',
})

const providerForms = reactive({})

const providerIds = computed(() => {
  const models = config.value?.config?.models || {}
  return Object.keys(models)
})

function providerLabel(id) {
  const desc = config.value?.config?.models?.[id]?.description
  return desc ? `${desc}` : id
}

function modelsForProvider(provId) {
  if (!provId) return []
  const instances = config.value?.config?.models?.[provId]?.instances || {}
  return Object.keys(instances)
}

function resetProviderForms(rawModels) {
  Object.keys(providerForms).forEach((key) => {
    delete providerForms[key]
  })
  for (const [provId, prov] of Object.entries(rawModels || {})) {
    providerForms[provId] = {
      description: prov.description || '',
      base_url: prov.base_url || '',
      api_key: prov.api_key_set ? API_KEY_MASK : '',
      api_key_set: Boolean(prov.api_key_set),
      is_valid: Number(prov.is_valid) === 1,
    }
  }
}

function fillFormFromConfig(data) {
  const cfg = data?.config || {}
  form.defaultProvider = cfg.default?.provider || ''
  form.defaultModel = cfg.default?.model || ''
  form.fallbackProvider = cfg.fallback?.provider || ''
  form.fallbackModel = cfg.fallback?.model || ''
  resetProviderForms(cfg.models)
}

async function loadConfig() {
  loading.value = true
  loadError.value = ''
  saveError.value = ''
  try {
    const data = await getLlmConfig()
    config.value = data
    fillFormFromConfig(data)
  } catch (e) {
    loadError.value = e?.message || '加载模型配置失败'
    config.value = null
  } finally {
    loading.value = false
  }
}

function buildPayload() {
  const models = {}
  for (const provId of providerIds.value) {
    const row = providerForms[provId]
    if (!row) continue
    models[provId] = {
      description: row.description,
      base_url: row.base_url,
      is_valid: row.is_valid ? 1 : 0,
      api_key: row.api_key || (row.api_key_set ? API_KEY_MASK : ''),
    }
  }
  return {
    config: {
      default: {
        provider: form.defaultProvider,
        model: form.defaultModel,
      },
      fallback: {
        provider: form.fallbackProvider,
        model: form.fallbackModel,
      },
      models,
    },
  }
}

async function onSave() {
  if (saving.value) return false
  saveError.value = ''
  saving.value = true
  try {
    const data = await updateLlmConfig(buildPayload())
    config.value = data
    fillFormFromConfig(data)
    emit('saved', data)
    return true
  } catch (e) {
    saveError.value = e?.message || '保存失败'
    return false
  } finally {
    saving.value = false
  }
}

defineExpose({
  loadConfig,
  onSave,
  saving,
  loading,
})
</script>

<style scoped>
.status-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.status-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  background: #fce8e6;
  color: #c5221f;
}
.status-badge.on {
  background: #e8f5e9;
  color: #2e7d32;
}
.resolved {
  font-size: 12px;
  color: #5f6368;
}
.file-hint {
  margin: 0 0 16px;
  font-size: 11px;
  color: #80868b;
  word-break: break-all;
}
.file-hint code {
  font-size: 10px;
}
.panel-empty {
  padding: 32px 12px;
  text-align: center;
  color: #80868b;
}
.panel-empty.error {
  color: #c5221f;
}
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.form-section h3 {
  margin: 0 0 10px;
  font-size: 14px;
}
.section-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #80868b;
  line-height: 1.5;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.field-row label,
.field-full {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #5f6368;
}
.field-row select,
.field-full input {
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 13px;
}
.mono {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
}
.provider-card {
  border: 1px solid #e8eaed;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafbfc;
}
.provider-card.enabled {
  border-color: #c6dafc;
  background: #f8fbff;
}
.provider-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.provider-head code {
  font-size: 10px;
  color: #80868b;
}
.provider-desc {
  margin: 0 0 8px;
  font-size: 12px;
  color: #5f6368;
}
.toggle-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.save-error {
  margin: 0;
  color: #c5221f;
  font-size: 13px;
}
</style>
