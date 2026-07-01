<template>
  <div class="knowledge-placeholder-page">
    <div class="knowledge-placeholder-card">
      <span class="knowledge-badge">预留模块</span>
      <h2>Knowledge</h2>
      <p class="knowledge-lead">
        知识库模块即将接入，用于浏览与管理 Workspace 下的
        <code>{workspace}/knowledge/</code> 资产。
      </p>
      <ul class="knowledge-plan-list">
        <li>领域知识文档索引</li>
        <li>规范、模式与最佳实践检索</li>
        <li>与 Features / Requirements / Architectures 的关联引用</li>
      </ul>
      <p v-if="!workspacePath.trim()" class="knowledge-hint">
        请先在顶栏配置<strong>作业空间路径</strong>。
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  workspacePath: { type: String, default: '' },
})
</script>

<style scoped>
.knowledge-placeholder-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 32px 24px;
  background: var(--pm-bg);
}
.knowledge-placeholder-card {
  max-width: 520px;
  width: 100%;
  padding: 32px 28px;
  border-radius: var(--pm-radius-lg);
  border: 1px dashed #d1d5db;
  background: var(--pm-surface);
  box-shadow: var(--pm-shadow);
  text-align: center;
}
.knowledge-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--pm-accent-knowledge);
  background: var(--pm-accent-knowledge-soft);
}
.knowledge-placeholder-card h2 {
  margin: 16px 0 10px;
  font-size: 24px;
  font-weight: 800;
  color: var(--pm-text);
}
.knowledge-lead {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--pm-text-secondary);
}
.knowledge-lead code {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 6px;
  background: #f3f4f6;
}
.knowledge-plan-list {
  margin: 20px 0 0;
  padding: 0;
  list-style: none;
  text-align: left;
  font-size: 13px;
  color: var(--pm-text-secondary);
  line-height: 1.7;
}
.knowledge-plan-list li {
  position: relative;
  padding-left: 16px;
}
.knowledge-plan-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.65em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--pm-accent-knowledge);
}
.knowledge-hint {
  margin: 18px 0 0;
  font-size: 13px;
  color: var(--pm-text-muted);
}
</style>
