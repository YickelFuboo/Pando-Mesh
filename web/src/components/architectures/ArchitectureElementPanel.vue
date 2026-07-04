<template>
  <div class="architecture-element-panel">
    <header class="aep-head">
      <div class="aep-head-main">
        <span class="aep-badge">{{ elementNode?.element_id || '元素' }}</span>
        <h2>{{ elementNode?.name || '架构元素' }}</h2>
      </div>
      <nav class="aep-tabs">
        <button
          type="button"
          class="aep-tab"
          :class="{ active: activeTab === 'spec' }"
          @click="activeTab = 'spec'"
        >
          详情
        </button>
        <button
          type="button"
          class="aep-tab"
          :class="{ active: activeTab === 'interfaces' }"
          @click="activeTab = 'interfaces'"
        >
          接口关系
        </button>
        <button
          type="button"
          class="aep-tab"
          :class="{ active: activeTab === 'topology' }"
          @click="activeTab = 'topology'"
        >
          依赖拓扑
        </button>
      </nav>
    </header>

    <ArchitectureDocPanel
      v-if="activeTab === 'spec'"
      class="aep-spec-pane"
      :workspace-path="workspacePath"
      :doc-node="elementNode"
      badge="元素"
      :title="elementNode?.name || ''"
    />

    <ArchitectureInterfacesPanel
      v-else-if="activeTab === 'interfaces'"
      class="aep-interfaces-pane"
      :workspace-path="workspacePath"
      :element-node="elementNode"
      @select-element="emit('select-element', $event)"
    />

    <ArchitectureDepCanvas
      v-else
      class="aep-topology-pane"
      :elements="viewElements"
      :focus-element-id="elementNode?.element_id || ''"
      :selected-node-id="elementNode?.element_id || ''"
      :is-full-view="false"
      :show-legend="true"
      @select-node="emit('select-element', $event)"
      @reset-root="emit('reset-root')"
    />
  </div>
</template>

<script setup>
import ArchitectureDocPanel from './ArchitectureDocPanel.vue'
import ArchitectureInterfacesPanel from './ArchitectureInterfacesPanel.vue'
import ArchitectureDepCanvas from './ArchitectureDepCanvas.vue'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  elementNode: { type: Object, default: null },
  viewElements: { type: Array, default: () => [] },
})

const emit = defineEmits(['select-element', 'reset-root'])

const activeTab = defineModel('activeTab', { type: String, default: 'topology' })
</script>

<style scoped>
.architecture-element-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--pm-surface);
}
.aep-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--pm-border);
  background: #fff;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.aep-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.aep-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #7c3aed;
  background: #f5f3ff;
  text-transform: uppercase;
}
.aep-head-main h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.aep-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  border-radius: 10px;
  background: #f3f4f6;
}
.aep-tab {
  border: none;
  background: transparent;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--pm-text-secondary);
  cursor: pointer;
}
.aep-tab.active {
  background: #fff;
  color: var(--pm-accent-architectures);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.aep-spec-pane,
.aep-interfaces-pane,
.aep-topology-pane {
  flex: 1;
  min-height: 0;
}
.aep-spec-pane :deep(.adp-head) {
  display: none;
}
</style>
