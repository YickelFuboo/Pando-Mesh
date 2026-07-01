<template>
  <div class="home-page">
    <header class="home-hero">
      <span class="home-badge">Pando-Mesh</span>
      <h1 class="home-title">
        软件端到端 <span class="accent">AI 自主研发</span> 交付平台
      </h1>
      <p class="home-lead">
        从特性规格、需求拆解到 Agent 编排执行，在统一 Workspace 中完成软件研发的自动化闭环。
        支持模板化工作流、多 Agent 协作与节点级交付件管理，助力团队高效、可追溯地交付软件成果。
      </p>
      <p v-if="!workspacePath.trim()" class="home-hint">
        请先在顶栏配置<strong>作业空间路径</strong>，再进入各模块开始工作。
      </p>
    </header>

    <section class="home-cards-section">
      <HubNavCards layout="horizontal" @navigate="emit('navigate', $event)" />
    </section>
  </div>
</template>

<script setup>
import HubNavCards from './HubNavCards.vue'

defineProps({
  workspacePath: { type: String, default: '' },
})

const emit = defineEmits(['navigate'])
</script>

<style scoped>
.home-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 32px 56px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  min-height: 100%;
}
.home-hero {
  text-align: left;
}
.home-badge {
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
.home-title {
  margin: 0 0 16px;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--pm-text);
  max-width: 720px;
}
.home-title .accent {
  color: var(--pm-primary);
}
.home-lead {
  margin: 0;
  font-size: 16px;
  line-height: 1.75;
  color: var(--pm-text-secondary);
  max-width: 680px;
}
.home-hint {
  margin: 16px 0 0;
  font-size: 13px;
  color: var(--pm-text-muted);
  line-height: 1.6;
}
.home-cards-section {
  width: 100%;
}
@media (max-width: 900px) {
  .home-page {
    padding: 32px 20px 40px;
    gap: 28px;
  }
}
</style>
