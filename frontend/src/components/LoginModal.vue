<template>
  <div class="mask">
    <div class="card">
      <div class="title">{{ mode === 'login' ? '登录' : '注册' }}</div>
      <div class="sub" v-if="mode === 'login'">使用测试账号：lfm / 123456</div>
      <div class="sub" v-else>注册后会自动登录</div>

      <div class="form">
        <label class="label">Username</label>
        <input class="input" v-model.trim="username" placeholder="lfm" />

        <template v-if="mode === 'register'">
          <label class="label">Email</label>
          <input class="input" v-model.trim="email" placeholder="test@example.com" />
        </template>

        <label class="label">Password</label>
        <input class="input" v-model.trim="password" type="password" placeholder="123456" />

        <div v-if="error" class="error">{{ error }}</div>

        <button class="btn" type="button" @click="onSubmit" :disabled="loading">
          {{ loading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? 'Login' : 'Register') }}
        </button>

        <button class="link" type="button" :disabled="loading" @click="toggleMode">
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
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

const emit = defineEmits(['submit', 'mode-change'])

const mode = ref('login') // 'login' | 'register'

const username = ref('lfm')
const email = ref('')
const password = ref('123456')

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  emit('mode-change', mode.value)
}

function onSubmit() {
  emit('submit', {
    mode: mode.value,
    username: username.value,
    email: email.value,
    password: password.value
  })
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

.link {
  margin-top: 8px;
  border: none;
  background: transparent;
  color: #2563eb;
  font-weight: 800;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
  text-align: center;
}

.link:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

