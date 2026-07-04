<template>
  <div class="markdown-with-meta">
    <div class="mwm-body" :class="{ 'has-toc': toc.length }">
      <aside v-if="toc.length" class="mwm-toc">
        <p class="mwm-toc-title">目录</p>
        <nav class="mwm-toc-nav">
          <button
            v-for="item in toc"
            :key="item.id"
            type="button"
            class="mwm-toc-item"
            :class="[`level-${item.level}`, { active: item.id === activeHeadingId }]"
            @click="scrollToHeading(item.id)"
          >
            {{ item.title }}
          </button>
        </nav>
      </aside>
      <div ref="mainRef" class="mwm-main">
        <div v-if="html" ref="markdownRef" class="pm-markdown" v-html="html" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { renderMarkdownDocument } from '../../utils/markdown.js'

const props = defineProps({
  content: { type: String, default: '' },
  meta: { type: Object, default: null },
})

const mainRef = ref(null)
const markdownRef = ref(null)
const activeHeadingId = ref('')

const docView = computed(() => renderMarkdownDocument(props.content, props.meta))

const html = computed(() => docView.value.html)
const toc = computed(() => docView.value.headings || [])

function getScrollContainer() {
  if (toc.value.length && mainRef.value) return mainRef.value
  let node = markdownRef.value
  while (node) {
    const style = window.getComputedStyle(node)
    if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 8) {
      return node
    }
    node = node.parentElement
  }
  return document.scrollingElement || document.documentElement
}

function scrollToHeading(id) {
  const root = markdownRef.value
  if (!root || !id) return
  const selector = `#${CSS.escape(id)}`
  const target = root.querySelector(selector)
  if (!target) return
  activeHeadingId.value = id
  const container = getScrollContainer()
  if (!container) return
  const offset = elementTopInContainer(target, container) - 16
  container.scrollTo({ top: Math.max(0, offset), behavior: 'smooth' })
}

function elementTopInContainer(el, container) {
  const elRect = el.getBoundingClientRect()
  const containerRect = container.getBoundingClientRect()
  return elRect.top - containerRect.top + container.scrollTop
}

function updateActiveHeading() {
  const root = markdownRef.value
  if (!root || !toc.value.length) return
  const container = getScrollContainer()
  const marker = container.scrollTop + 80
  let current = toc.value[0].id
  for (const item of toc.value) {
    const el = root.querySelector(`#${CSS.escape(item.id)}`)
    if (!el) continue
    if (elementTopInContainer(el, container) <= marker) current = item.id
    else break
  }
  activeHeadingId.value = current
}

let scrollContainer = null

function bindScrollSpy() {
  unbindScrollSpy()
  if (!markdownRef.value || !toc.value.length) return
  scrollContainer = getScrollContainer()
  scrollContainer.addEventListener('scroll', updateActiveHeading, { passive: true })
  updateActiveHeading()
}

function unbindScrollSpy() {
  scrollContainer?.removeEventListener('scroll', updateActiveHeading)
  scrollContainer = null
}

watch(
  () => [props.content, props.meta, html.value],
  async () => {
    activeHeadingId.value = toc.value[0]?.id || ''
    await nextTick()
    bindScrollSpy()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  unbindScrollSpy()
})
</script>

<style scoped>
.markdown-with-meta {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.mwm-body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
}
.mwm-body.has-toc .mwm-main {
  background: #fff;
}
.mwm-toc {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 14px 24px;
  border-right: 1px solid var(--pm-border);
  background: linear-gradient(180deg, #f8fafc 0%, #f3f6f9 100%);
}
.mwm-toc-title {
  margin: 0 0 12px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--pm-text-muted);
  text-transform: uppercase;
}
.mwm-toc-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.mwm-toc-item {
  display: block;
  width: 100%;
  padding: 6px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--pm-text-secondary);
  font-size: 12px;
  line-height: 1.45;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.mwm-toc-item:hover {
  background: rgba(0, 184, 148, 0.08);
  color: var(--pm-text);
}
.mwm-toc-item.active {
  background: var(--pm-primary-soft);
  color: var(--pm-primary);
  font-weight: 600;
}
.mwm-toc-item.level-1 { padding-left: 10px; font-weight: 600; }
.mwm-toc-item.level-2 { padding-left: 18px; }
.mwm-toc-item.level-3 { padding-left: 26px; font-size: 11px; }
.mwm-toc-item.level-4 { padding-left: 34px; font-size: 11px; }
.mwm-toc-item.level-5 { padding-left: 42px; font-size: 11px; }
.mwm-toc-item.level-6 { padding-left: 50px; font-size: 11px; }
.mwm-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 28px 36px;
}
@media (max-width: 960px) {
  .mwm-body.has-toc {
    flex-direction: column;
  }
  .mwm-toc {
    width: 100%;
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--pm-border);
  }
  .mwm-main {
    padding: 16px 18px 28px;
  }
}
</style>
