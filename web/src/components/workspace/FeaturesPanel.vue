<template>
  <div class="hub-page">
    <div class="hub-layout">
      <header class="hub-hero">
        <span class="hub-badge">Pando-Mesh</span>
        <h1 class="hub-title">
          Browse and manage <span class="accent">features</span> in your workspace.
        </h1>
        <p class="hub-lead">
          特性库集中存放功能规格与变更说明，作为需求分析与编排的输入来源。
        </p>
      </header>
      <HubNavCards :active-tab="activeTab" @navigate="emit('navigate', $event)" />
    </div>

    <section class="hub-content-card">
      <h2 class="content-card-title">特性库路径</h2>
      <p v-if="!workspacePath.trim()" class="content-empty">
        请先在顶栏配置<strong>作业空间路径</strong>。
      </p>
      <template v-else>
        <p class="content-path">
          <code>{{ featuresPath }}</code>
        </p>
        <p class="content-hint">
          特性文档位于 <code>{workspace}/features/</code> 目录树中，后续可在此页直接浏览与检索。
        </p>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import HubNavCards from './HubNavCards.vue'

const props = defineProps({
  workspacePath: { type: String, default: '' },
  activeTab: { type: String, default: 'features' },
})

const emit = defineEmits(['navigate'])

const featuresPath = computed(() => {
  const ws = String(props.workspacePath || '').trim().replace(/[/\\]+$/, '')
  if (!ws) return ''
  return `${ws}/features/`
})
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
  background: var(--pm-primary-soft);
  color: var(--pm-primary);
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
  color: var(--pm-accent-features);
}
.hub-lead {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--pm-text-secondary);
  max-width: 520px;
}
.hub-content-card {
  padding: 24px 28px;
  border-radius: var(--pm-radius-lg);
  border: 1px solid var(--pm-border);
  background: var(--pm-surface);
  box-shadow: var(--pm-shadow);
}
.content-card-title {
  margin: 0 0 14px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--pm-text-muted);
}
.content-empty {
  margin: 0;
  font-size: 14px;
  color: var(--pm-text-secondary);
  line-height: 1.6;
}
.inline-link {
  border: none;
  padding: 0;
  background: none;
  color: var(--pm-primary);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.content-path {
  margin: 0 0 12px;
  font-size: 14px;
  word-break: break-all;
}
.content-path code {
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--pm-surface-muted);
  font-size: 13px;
}
.content-hint {
  margin: 0;
  font-size: 13px;
  color: var(--pm-text-secondary);
  line-height: 1.6;
}
.content-hint code {
  font-size: 12px;
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
