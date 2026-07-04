<template>
  <div class="architecture-interfaces-panel">
    <div class="aip-body">
      <div v-if="loading" class="aip-state">加载接口关系…</div>
      <div v-else-if="error" class="aip-state error">{{ error }}</div>
      <div v-else-if="!hasData" class="aip-state">暂无 interfaces.yaml / dependencies.yaml</div>
      <div v-else class="aip-scroll">
        <div v-if="summaryText" class="aip-summary">{{ summaryText }}</div>
        <section v-if="provided.length" class="aip-section">
          <h3>提供的接口 <span class="aip-count">{{ provided.length }}</span></h3>
          <p v-if="interfacesPath" class="aip-source-path">{{ interfacesPath }}</p>
          <div class="aip-table-wrap">
            <table class="aip-table">
              <thead>
                <tr>
                  <th>接口 ID</th>
                  <th>接口名</th>
                  <th>协议</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in provided" :key="row.if_id || row.if_name">
                  <td>{{ row.if_id || '—' }}</td>
                  <td>{{ row.if_name || '—' }}</td>
                  <td>{{ row.protocol || '—' }}</td>
                  <td>{{ row.summary || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section v-if="internal.length || external.length" class="aip-section">
          <h3>依赖的接口 <span class="aip-count">{{ internal.length + external.length }}</span></h3>
          <p v-if="dependenciesPath" class="aip-source-path">{{ dependenciesPath }}</p>
          <div v-if="internal.length" class="aip-subblock">
            <h4>系统内依赖 <span class="aip-count">{{ internal.length }}</span></h4>
            <div class="aip-table-wrap">
              <table class="aip-table">
                <thead>
                  <tr>
                    <th>依赖 ID</th>
                    <th>提供方元素</th>
                    <th>协议</th>
                    <th>用途</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in internal" :key="row.if_ext_id || `${row.provider_element}-${row.protocol}`">
                    <td>{{ row.if_ext_id || '—' }}</td>
                    <td>
                      <button
                        v-if="row.provider_element"
                        type="button"
                        class="aip-link-btn"
                        @click="emit('select-element', row.provider_element)"
                      >{{ row.provider_element }}</button>
                      <span v-else>—</span>
                    </td>
                    <td>{{ row.protocol || '—' }}</td>
                    <td>{{ row.purpose || '—' }}</td>
                    <td>{{ formatOperations(row.operations) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-if="external.length" class="aip-subblock">
            <h4>外部依赖 <span class="aip-count">{{ external.length }}</span></h4>
            <div class="aip-table-wrap">
              <table class="aip-table">
                <thead>
                  <tr>
                    <th>依赖 ID</th>
                    <th>提供方</th>
                    <th>类别</th>
                    <th>协议</th>
                    <th>用途</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in external" :key="row.if_ext_id || row.provider">
                    <td>{{ row.if_ext_id || '—' }}</td>
                    <td>{{ row.provider || '—' }}</td>
                    <td>{{ row.category || '—' }}</td>
                    <td>{{ row.protocol || '—' }}</td>
                    <td>{{ row.purpose || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
        <p v-if="contractIndex" class="aip-footnote">完整契约索引：{{ contractIndex }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { getArchitectureElementInterfaces } from '../../api/layerApi.js'
import { elementWorkspaceFilePath } from '../../utils/architectureTreeModel.js'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  elementNode: { type: Object, default: null },
})

const emit = defineEmits(['select-element'])

const loading = ref(false)
const error = ref('')
const payload = ref(null)

const provided = computed(() => payload.value?.provided_interfaces || [])
const internal = computed(() => payload.value?.system_internal_dependencies || [])
const external = computed(() => payload.value?.external_dependencies || [])
const contractIndex = computed(() => String(payload.value?.full_contract_index || '').trim())
const interfacesPath = computed(() => String(payload.value?.interfaces_path || '').trim())
const dependenciesPath = computed(() => String(payload.value?.dependencies_path || '').trim())
const hasData = computed(() => (
  provided.value.length || internal.value.length || external.value.length
))

const summaryText = computed(() => {
  const summary = payload.value?.summary
  if (!summary || typeof summary !== 'object') return ''
  const parts = []
  if (summary.system_internal_count != null) parts.push(`系统内 ${summary.system_internal_count}`)
  if (summary.external_count != null) parts.push(`外部 ${summary.external_count}`)
  if (summary.total != null) parts.push(`合计 ${summary.total}`)
  return parts.length ? parts.join(' · ') : ''
})

function formatOperations(value) {
  if (Array.isArray(value)) return value.join('\n')
  return String(value || '—')
}

async function loadInterfaces() {
  const ws = props.workspacePath.trim()
  const node = props.elementNode
  error.value = ''
  payload.value = null
  if (!ws || !node) return
  const specPath = elementWorkspaceFilePath(node)
  if (!specPath) {
    error.value = '未配置 spec 路径'
    return
  }
  loading.value = true
  try {
    payload.value = await getArchitectureElementInterfaces(ws, specPath)
  } catch (e) {
    error.value = e?.message || '加载接口关系失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.workspacePath, props.elementNode?.id],
  () => loadInterfaces(),
  { immediate: true },
)
</script>

<style scoped>
.architecture-interfaces-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: #fafbfc;
}
.aip-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.aip-scroll {
  height: 100%;
  overflow: auto;
  padding: 16px 20px 28px;
}
.aip-summary {
  margin: 0 0 14px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--pm-border);
  font-size: 12px;
  color: var(--pm-text-secondary);
}
.aip-section + .aip-section {
  margin-top: 20px;
}
.aip-section h3 {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--pm-text);
}
.aip-subblock + .aip-subblock {
  margin-top: 16px;
}
.aip-subblock h4 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--pm-text);
}
.aip-source-path {
  margin: 0 0 10px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--pm-text-muted);
  font-family: ui-monospace, SFMono-Regular, Monaco, Consolas, monospace;
  word-break: break-all;
}
.aip-count {
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--pm-surface-muted);
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-text-secondary);
}
.aip-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--pm-border);
  border-radius: 8px;
  background: #fff;
}
.aip-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.aip-table th,
.aip-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--pm-border);
  text-align: left;
  vertical-align: top;
  line-height: 1.5;
  word-break: break-word;
}
.aip-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: var(--pm-text-secondary);
  white-space: nowrap;
}
.aip-table tbody tr:last-child td {
  border-bottom: none;
}
.aip-table tbody tr:nth-child(even) {
  background: #fafbfc;
}
.aip-link-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #0d9488;
  font-size: inherit;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
.aip-link-btn:hover {
  color: #0f766e;
}
.aip-footnote {
  margin: 16px 0 0;
  font-size: 11px;
  color: var(--pm-text-muted);
  word-break: break-all;
}
.aip-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  color: var(--pm-text-secondary);
  font-size: 14px;
}
.aip-state.error {
  color: var(--pm-danger);
}
</style>
