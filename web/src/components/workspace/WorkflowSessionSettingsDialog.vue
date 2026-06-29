<template>
  <div v-if="visible" class="overlay" @mousedown.self="$emit('close')">
    <div class="dialog-card" role="dialog" aria-modal="true" aria-labelledby="session-settings-title">
      <header class="dialog-head">
        <h3 id="session-settings-title">Session 配置</h3>
        <button type="button" class="close-btn" aria-label="关闭" @click="$emit('close')">×</button>
      </header>
      <form class="dialog-body" @submit.prevent="onSubmit">
        <label class="dialog-field">
          任务目标
          <textarea
            v-model="goalLocal"
            rows="4"
            placeholder="描述本需求的任务要求…"
          />
        </label>
        <label v-if="showJudge" class="dialog-field">
          Judge
          <select v-model="judgeLocal">
            <option value="">auto</option>
            <option value="llm">llm</option>
            <option value="json">json</option>
            <option value="auto">auto</option>
          </select>
        </label>
        <p v-if="error" class="dialog-error">{{ error }}</p>
        <footer class="dialog-foot">
          <button type="button" class="btn" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  userGoal: { type: String, default: '' },
  judgeMode: { type: String, default: '' },
  showJudge: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save'])

const goalLocal = ref('')
const judgeLocal = ref('')
const error = ref('')

watch(
  () => [props.visible, props.userGoal, props.judgeMode],
  () => {
    if (!props.visible) return
    goalLocal.value = props.userGoal || ''
    judgeLocal.value = props.judgeMode || ''
    error.value = ''
  },
  { immediate: true },
)

function onSubmit() {
  error.value = ''
  emit('save', {
    user_goal: goalLocal.value.trim(),
    judge_mode: judgeLocal.value,
  })
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  padding: 16px;
}
.dialog-card {
  width: min(520px, 100%);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #ebebeb;
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
  color: #8c8c8c;
}
.dialog-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dialog-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #8c8c8c;
}
.dialog-field textarea,
.dialog-field select {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
}
.dialog-error {
  margin: 0;
  font-size: 13px;
  color: #c5221f;
}
.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
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
  background: var(--pm-primary, #1677ff);
  border-color: var(--pm-primary, #1677ff);
  color: #fff;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
