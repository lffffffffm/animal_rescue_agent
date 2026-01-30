<script setup>
import { computed, onMounted, ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import LoginModal from './components/LoginModal.vue'

import {
  tokenStore,
  login as apiLogin,
  me as apiMe,
  listSessions,
  getSessionHistory,
  rescueQuery,
  updateSessionTitle,
  deleteSession
} from './services/api'

const user = ref({
  name: 'lfm',
  avatar: new URL('./assets/default-avatar.svg', import.meta.url).href
})

// 侧边栏收缩
const sidebarCollapsed = ref(false)

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 方案B：前端聚合“线程”，内部可包含多个后端 session
// thread: { id, title, createdAt, sessionIds: [], messages: [] }
const threads = ref([])
const activeId = ref(null)

const recent = computed(() => threads.value)
const last7Days = computed(() => [])

const loginVisible = ref(false)
const loginLoading = ref(false)
const loginError = ref('')

const loading = ref(false)
const error = ref('')

const activeThread = computed(() => threads.value.find(t => t.id === activeId.value) || null)
const messages = computed(() => activeThread.value?.messages || [])

function ensureThread() {
  if (activeThread.value) return activeThread.value
  const id = Date.now()
  const t = {
    id,
    title: 'New chat',
    createdAt: new Date().toISOString(),
    sessionIds: [],
    messages: []
  }
  threads.value = [t, ...threads.value]
  activeId.value = id
  return t
}

function onNewChat() {
  const id = Date.now()
  const t = {
    id,
    title: 'New chat',
    createdAt: new Date().toISOString(),
    sessionIds: [],
    messages: []
  }
  threads.value = [t, ...threads.value]
  activeId.value = id
  error.value = ''
}

async function hydrateFromBackendSessions() {
  const sessions = await listSessions().catch(() => [])
  const mapped = (sessions || [])
    .slice()
    .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
    .map(s => ({
      id: s.session_id,
      title: s.title || 'Chat',
      createdAt: s.created_at,
      sessionIds: [s.session_id],
      messages: []
    }))

  if (!threads.value.length) threads.value = mapped
  if (!activeId.value && threads.value.length) activeId.value = threads.value[0].id
}

async function loadHistory(thread) {
  if (!thread) return
  error.value = ''
  if (thread.messages.length) return

  const all = []
  for (const sid of thread.sessionIds) {
    // eslint-disable-next-line no-await-in-loop
    const hist = await getSessionHistory(sid).catch(() => [])
    for (const h of hist || []) {
      all.push({
        id: `${sid}:${h.id}:u`,
        role: 'user',
        content: h.user_input || ''
      })
      all.push({
        id: `${sid}:${h.id}:a`,
        role: 'assistant',
        content: h.agent_response || ''
      })
    }
  }
  thread.messages = all
}

async function onSelectChat(id) {
  activeId.value = id
  const t = activeThread.value
  if (t) await loadHistory(t)
}

const editingId = ref(null)

function onEditChat(id) {
  editingId.value = id
}

function onEditInput({ id, title }) {
  const t = threads.value.find(i => i.id === id)
  if (!t) return
  t.title = title
}

async function onCommitTitle({ id, title }) {
  editingId.value = null
  const next = String(title ?? '').trim()
  if (!next) return

  const t = threads.value.find(i => i.id === id)
  if (!t || t.title === next) return

  t.title = next

  const lastSid = t.sessionIds[t.sessionIds.length - 1]
  if (lastSid && typeof lastSid === 'string') {
    await updateSessionTitle(lastSid, next).catch(() => {})
  }
}

function onCancelEdit() {
  editingId.value = null
}

async function onDeleteChat(id) {
  const t = threads.value.find(i => i.id === id)
  threads.value = threads.value.filter(i => i.id !== id)
  if (activeId.value === id) activeId.value = threads.value[0]?.id ?? null

  if (t?.sessionIds?.length) {
    await Promise.allSettled(t.sessionIds.map(sid => (typeof sid === 'string' ? deleteSession(sid) : Promise.resolve())))
  }
}

function onClearGroup(key) {
  if (key !== 'recent') return
  threads.value = []
  activeId.value = null
}

const enableWeb = ref(false)
const enableMap = ref(false)

async function send(text) {
  const t = ensureThread()
  error.value = ''

  const userMsg = { id: `u:${Date.now()}`, role: 'user', content: text }
  t.messages.push(userMsg)

  const chat_history = t.messages
    .filter(m => m.role === 'user' || m.role === 'assistant')
    .slice(-10)
    .map(m => ({ role: m.role, content: m.content }))

  loading.value = true
  try {
    const resp = await rescueQuery({
      query: text,
      chat_history,
      enable_web_search: enableWeb.value,
      enable_map: enableMap.value
    })

    const answer = resp?.answer ?? ''
    t.messages.push({ id: `a:${Date.now()}`, role: 'assistant', content: answer })

    if (t.title === 'New chat') t.title = text

    const sessions = await listSessions().catch(() => [])
    const newest = (sessions || [])
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]

    if (newest?.session_id && !t.sessionIds.includes(newest.session_id)) {
      t.sessionIds.push(newest.session_id)
    }
  } catch (e) {
    error.value = e?.message || '发送失败'
  } finally {
    loading.value = false
  }
}

async function boot() {
  const token = tokenStore.get()
  if (!token) {
    loginVisible.value = true
    return
  }

  try {
    const u = await apiMe()
    user.value = {
      name: u?.username || 'User',
      avatar: new URL('./assets/default-avatar.svg', import.meta.url).href
    }

    await hydrateFromBackendSessions()
    const t = activeThread.value
    if (t) await loadHistory(t)
  } catch (e) {
    tokenStore.clear()
    loginVisible.value = true
  }
}

async function onLoginSubmit({ username, password }) {
  loginError.value = ''
  loginLoading.value = true
  try {
    await apiLogin(username, password)
    loginVisible.value = false
    await boot()
  } catch (e) {
    loginError.value = e?.message || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

function onLogout() {
  tokenStore.clear()
  threads.value = []
  activeId.value = null
  error.value = ''
  loginVisible.value = true
}

onMounted(() => {
  boot()
})
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <Sidebar
      :user="user"
      :recent="recent"
      :last7-days="last7Days"
      :active-id="activeId"
      :editing-id="editingId"
      :collapsed="sidebarCollapsed"
      @toggle-collapse="toggleSidebar"
      @new-chat="onNewChat"
      @select-chat="onSelectChat"
      @edit-chat="onEditChat"
      @edit-input="onEditInput"
      @edit-commit="onCommitTitle"
      @edit-cancel="onCancelEdit"
      @delete-chat="onDeleteChat"
      @clear-group="onClearGroup"
      @logout="onLogout"
    />

    <ChatArea
      :user="user"
      :active-thread="activeThread"
      :messages="messages"
      :loading="loading"
      :error="error"
      v-model:enable-web="enableWeb"
      v-model:enable-map="enableMap"
      @send="send"
      @edit-current="() => activeId && onEditChat(activeId)"
    />

    <LoginModal
      v-if="loginVisible"
      :loading="loginLoading"
      :error="loginError"
      @submit="onLoginSubmit"
    />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  align-items: stretch;
  justify-content: flex-start;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #ffffff;
  margin: 0;
  padding: 0;
}

:global(html),
:global(body) {
  margin: 0;
  padding: 0;
}

:global(#app) {
  height: 100vh;
}
</style>
