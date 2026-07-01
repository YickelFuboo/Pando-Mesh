<template>
  <div class="hub-nav-cards">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="hub-nav-card"
      :class="[item.tone, { active: activeTab === item.id }]"
      @click="emit('navigate', item.id)"
    >
      <span class="hub-nav-icon" aria-hidden="true">
        <component :is="item.icon" />
      </span>
      <span class="hub-nav-body">
        <span class="hub-nav-label">{{ item.label }}</span>
        <span class="hub-nav-title">{{ item.title }}</span>
        <span class="hub-nav-desc">{{ item.desc }}</span>
      </span>
      <span class="hub-nav-chevron" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M9.29 6.71a1 1 0 0 1 1.42 0L15.59 12l-4.88 5.29a1 1 0 0 1-1.42-1.42L12.17 12 9.29 9.12a1 1 0 0 1 0-1.41z" />
        </svg>
      </span>
    </button>
  </div>
</template>

<script setup>
import { h } from 'vue'

defineProps({
  activeTab: { type: String, default: 'features' },
})

const emit = defineEmits(['navigate'])

const IconFeatures = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: 22, height: 22 }, [
      h('path', { fill: 'currentColor', d: 'M4 6h7v7H4V6zm9 0h7v7h-7V6zM4 15h7v7H4v-7zm9 0h7v7h-7v-7z' }),
    ])
  },
}

const IconRequirements = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: 22, height: 22 }, [
      h('path', { fill: 'currentColor', d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM8 13h8v2H8v-2zm0 4h8v2H8v-2z' }),
    ])
  },
}

const IconWorkflow = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: 22, height: 22 }, [
      h('path', { fill: 'currentColor', d: 'M4 6c0-1.1.9-2 2-2h3v2H6v3H4V6zm14-2h-3v2h3v3h2V6c0-1.1-.9-2-2-2zM4 18v-3H2v3c0 1.1.9 2 2 2h3v-2H4zm16 0h-3v2h3c1.1 0 2-.9 2-2v-3h-2v3zM9 10h6v4H9v-4z' }),
    ])
  },
}

const items = [
  {
    id: 'features',
    tone: 'tone-features',
    label: 'FEATURE LIBRARY',
    title: 'Features',
    desc: '浏览 Workspace 下的特性库与规格文档。',
    icon: IconFeatures,
  },
  {
    id: 'requirements',
    tone: 'tone-requirements',
    label: 'REQUIREMENT HUB',
    title: 'Requirements',
    desc: '配置 Workspace、模板与需求 Session。',
    icon: IconRequirements,
  },
  {
    id: 'workflow',
    tone: 'tone-workflow',
    label: 'WORKFLOW STUDIO',
    title: 'WorkFlow',
    desc: '编排拓扑、对话交互与节点交付件。',
    icon: IconWorkflow,
  },
]
</script>

<style scoped>
.hub-nav-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hub-nav-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid var(--pm-border);
  border-radius: var(--pm-radius-lg);
  background: var(--pm-surface);
  box-shadow: var(--pm-shadow);
  cursor: pointer;
  text-align: left;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
}
.hub-nav-card:hover {
  box-shadow: var(--pm-shadow-md);
  transform: translateY(-1px);
}
.hub-nav-card.active {
  border-color: transparent;
  box-shadow: var(--pm-shadow-md);
}
.hub-nav-card.tone-features.active {
  background: var(--pm-accent-features-soft);
}
.hub-nav-card.tone-requirements.active {
  background: var(--pm-accent-requirements-soft);
}
.hub-nav-card.tone-workflow.active {
  background: var(--pm-accent-workflow-soft);
}
.hub-nav-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  color: var(--pm-text);
}
.tone-features .hub-nav-icon {
  background: var(--pm-accent-features-icon);
  color: var(--pm-accent-features);
}
.tone-requirements .hub-nav-icon {
  background: var(--pm-accent-requirements-icon);
  color: var(--pm-accent-requirements);
}
.tone-workflow .hub-nav-icon {
  background: var(--pm-accent-workflow-icon);
  color: var(--pm-accent-workflow);
}
.hub-nav-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.hub-nav-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--pm-text-muted);
}
.hub-nav-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--pm-text);
  line-height: 1.3;
}
.hub-nav-desc {
  font-size: 13px;
  color: var(--pm-text-secondary);
  line-height: 1.45;
  margin-top: 2px;
}
.hub-nav-chevron {
  flex-shrink: 0;
  align-self: center;
  color: var(--pm-text-muted);
}
.hub-nav-card.active .hub-nav-chevron {
  color: var(--pm-text-secondary);
}
</style>
