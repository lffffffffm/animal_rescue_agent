<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import LoginModal from './components/LoginModal.vue'

import {
  tokenStore,
  login as apiLogin,
  register as apiRegister,
  me as apiMe,
  listSessions,
  getSessionHistory,
  rescueQueryStream,
  uploadImage,
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

const thisWeek = computed(() => {
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setHours(0, 0, 0, 0)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
  return threads.value.filter(t => new Date(t.createdAt) >= sevenDaysAgo)
})

const weekBefore = computed(() => {
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setHours(0, 0, 0, 0)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
  return threads.value.filter(t => new Date(t.createdAt) < sevenDaysAgo)
})

const loginVisible = ref(false)
const loginLoading = ref(false)
const loginError = ref('')
let loginReqId = 0

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
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
      // 历史图片 URL：若后端已返回绝对 URL 则直接使用；若是相对路径则补齐 API_BASE_URL
      const images = (h.user_images || []).map((u) => (/^https?:\/\//i.test(u) ? u : `${API_BASE_URL}${u}`))

      all.push({
        id: `${sid}:${h.id}:u`,
        role: 'user',
        content: h.user_input || '',
        images: images
      })
      let assistantImages = [];
      if (h.agent_meta && h.agent_meta.images && Array.isArray(h.agent_meta.images)) {
          assistantImages = h.agent_meta.images.map(img => {
              const url = img.url || img; // 兼容 {url: '...'} 和 '...' 两种格式
              return /^https?:\/\//i.test(url) ? url : `${API_BASE_URL}${url}`;
          });
      }
      all.push({
        id: `${sid}:${h.id}:a`,
        role: 'assistant',
        content: h.agent_response || ''
      })
    }
  }
  thread.messages.splice(0, thread.messages.length, ...all)
}

async function onSelectChat(id) {
  activeId.value = id
  const t = activeThread.value
  if (t) await loadHistory(t)
}

const editingId = ref(null)

function onEditChat(id) {
  editingId.value = id
  const t = threads.value.find(i => i.id === id)
  if (!t) return
  t.draftTitle = t.title
}

function onEditInput({ id, title }) {
  const t = threads.value.find(i => i.id === id)
  if (!t) return
  t.draftTitle = title
}

async function onCommitTitle({ id, title }) {
  const t = threads.value.find(i => i.id === id)
  if (!t) {
  editingId.value = null
    return
  }

  const next = String(title ?? '').trim()
  if (!next) return

  const prev = String(t.title ?? '')

  // 先退出编辑态（避免 blur 反复触发）
  editingId.value = null

  const lastSid = t.sessionIds[t.sessionIds.length - 1]
  if (!lastSid || typeof lastSid !== 'string') {
    // 还没落库的会话（本地新会话），只能更新前端显示
    t.title = next
    t.draftTitle = undefined
    return
  }

  try {
    await updateSessionTitle(lastSid, next)
    t.title = next
    t.draftTitle = undefined
  } catch (e) {
    // 回滚
    t.title = prev
    t.draftTitle = prev
    error.value = e?.message || '更新标题失败'
  }
}

function onCancelEdit() {
  const t = threads.value.find(i => i.id === editingId.value)
  if (t) t.draftTitle = undefined
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
const location = ref('') // 用于存储经纬度

watch(enableMap, (newVal) => {
  if (newVal) {
    if (!navigator.geolocation) {
      showToast('您的浏览器不支持地理位置。', 'error')
      enableMap.value = false
      return
    }

    try {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords
          location.value = `${latitude},${longitude}`
        },
        (err) => {
          // https://developer.mozilla.org/en-US/docs/Web/API/GeolocationPositionError/code
          // 1: PERMISSION_DENIED, 2: POSITION_UNAVAILABLE, 3: TIMEOUT
          let msg = '获取不到当前地理位置信息。'
          if (err?.code === 1) msg = '已拒绝访问地理位置权限，获取不到当前地理位置信息。'
          else if (err?.code === 2) msg = '当前位置不可用，获取不到当前地理位置信息。'
          else if (err?.code === 3) msg = '获取地理位置超时，获取不到当前地理位置信息。'

          console.warn('[geolocation] failed:', err)
          alert(msg)
          enableMap.value = false
        },
        { timeout: 10000 }
      )
    } catch (e) {
      showToast('获取不到当前地理位置信息。', 'error')
      enableMap.value = false
    }
  } else {
    location.value = ''
  }
})

async function send(payload) {
  // 调试：打印接收到的数据
  console.log('App.vue received send event with payload:', payload);

  const t = ensureThread()
  error.value = ''

  const text = typeof payload === 'string' ? payload : (payload?.text || '')
  const files = typeof payload === 'string' ? [] : (payload?.files || [])
  const previews = typeof payload === 'string' ? [] : (payload?.previews || [])

  const userMsgId = `u:${Date.now()}`
  const userMsg = { id: userMsgId, role: 'user', content: text, images: previews }
  t.messages.push(userMsg)

  let chat_history = t.messages
    .filter(m => m.role === 'user' || m.role === 'assistant')
    .slice(-10)
    .map(({ role, content }) => ({ role, content }))

  if (!Array.isArray(chat_history)) {
    console.error('chat_history 不是数组:', chat_history)
    chat_history = []
  }

  loading.value = true

  const assistantId = `a:${Date.now()}`
  const assistantMsg = { id: assistantId, role: 'assistant', content: '' }
  t.messages.push(assistantMsg)

  try {
    const lastSid = t.sessionIds[t.sessionIds.length - 1]
    let session_id = typeof lastSid === 'string' ? lastSid : null

    // 先上传图片（最多4张）
    const image_ids = []
    if (Array.isArray(files) && files.length) {
      const limited = files.slice(0, 4)
      for (const f of limited) {
        // eslint-disable-next-line no-await-in-loop
        const up = await uploadImage(f, session_id)
        if (up?.session_id && !t.sessionIds.includes(up.session_id)) {
          t.sessionIds.push(up.session_id)
        }
        if (up?.session_id) session_id = up.session_id
        if (up?.image_id) image_ids.push(up.image_id)
      }
    }

    let deltaBuffer = ''
    let rafId = null

    const flush = () => {
      if (!deltaBuffer) return
      const idx = t.messages.findIndex(m => m.id === assistantId)
      if (idx >= 0) {
        const prev = t.messages[idx]
        t.messages[idx] = { ...prev, content: (prev.content || '') + deltaBuffer }
      }
      deltaBuffer = ''
      rafId = null
    }

    await rescueQueryStream({
      query: text,
      session_id,
      chat_history,
      enable_web_search: enableWeb.value,
      enable_map: enableMap.value,
      location: enableMap.value ? location.value : null,
      image_ids,
      onDelta: (payload) => {
        const delta = payload?.text ?? ''
        if (!delta) return
        deltaBuffer += delta
        if (!rafId) rafId = requestAnimationFrame(flush)
      },
      onDone: (meta) => {
        if (rafId) {
          cancelAnimationFrame(rafId)
          flush()
        }

        if (meta?.session_id && !t.sessionIds.includes(meta.session_id)) {
          t.sessionIds.push(meta.session_id)

          // 新会话：把 thread.id 切换为后端 session_id，避免后续用 Date.now() 这种本地 id 造成“会话未找到”
          if (!session_id) {
            const oldId = t.id
            t.id = meta.session_id
            if (activeId.value === oldId) activeId.value = meta.session_id
          }
        }

        // 若后端返回 images 元数据，追加到 assistant 消息以便前端展示
        if (Array.isArray(meta?.images) && meta.images.length) {
          assistantMsg.images = meta.images.map(i => i.url || i)
        }

        if (t.title === 'New chat') t.title = text
      }
    })
  } catch (e) {
    // 失败：回滚本次 user/assistant 消息，避免看起来“已经发出去了”
    t.messages = t.messages.filter(m => m.id !== assistantId && m.id !== userMsgId)
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

function onAuthModeChange() {
  loginReqId += 1
  loginError.value = ''
  loginLoading.value = false
}

async function onLoginSubmit(payload) {
  const rid = ++loginReqId
  loginError.value = ''
  loginLoading.value = true

  const mode = payload?.mode || 'login'
  const username = payload?.username
  const password = payload?.password
  const email = payload?.email

  try {
    if (mode === 'register') {
      if (!username || !email || !password) {
        throw new Error('请填写 Username / Email / Password')
      }
      await apiRegister({ username, email, password })
    }

    await apiLogin(username, password)
    loginVisible.value = false
    await boot()
  } catch (e) {
    if (rid === loginReqId) {
      loginError.value = e?.message || (mode === 'register' ? '注册失败' : '登录失败')
    }
  } finally {
    if (rid === loginReqId) {
      loginLoading.value = false
    }
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
      :recent="thisWeek"
      :last7-days="weekBefore"
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
      @mode-change="onAuthModeChange"
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
