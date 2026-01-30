<template>
  <div class="mask">
    <div class="card">
      <div class="title">登录</div>
      <div class="sub">使用测试账号：lfm / 123456</div>

      <div class="form">
        <label class="label">Username</label>
        <input class="input" v-model.trim="username" placeholder="lfm" />

        <label class="label">Password</label>
        <input class="input" v-model.trim="password" type="password" placeholder="123456" />

        <div v-if="error" class="error">{{ error }}</div>

        <button class="btn" type="button" @click="onSubmit" :disabled="loading">
          {{ loading ? '登录中...' : 'Login' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['submit'])

const username = ref('lfm')
const password = ref('123456')

function onSubmit() {
  emit('submit', { username: username.value, password: password.value })
}
</script>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 50;
}

.card {
  width: min(420px, 92vw);
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 18px 18px 16px;
  box-shadow: 0 20px 60px rgba(2, 6, 23, 0.18);
}

.title {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
}

.sub {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
}

.form {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 12px;
  font-weight: 800;
  color: #334155;
}

.input {
  height: 42px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  padding: 0 12px;
  font-size: 14px;
  font-weight: 700;
  outline: none;
  color: #0f172a;
}

.error {
  margin-top: 4px;
  color: #ef4444;
  font-weight: 800;
  font-size: 12px;
}

.btn {
  margin-top: 10px;
  height: 44px;
  border-radius: 12px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

