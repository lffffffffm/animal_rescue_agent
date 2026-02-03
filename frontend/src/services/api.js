const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const TOKEN_KEY = 'chatagent_token'

export const tokenStore = {
  get() {
    return localStorage.getItem(TOKEN_KEY) || ''
  },
  set(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
  }
}

async function request(path, { method = 'GET', headers = {}, body, auth = true } = {}) {
  const url = `${API_BASE_URL}${path}`

  const finalHeaders = {
    ...headers
  }

  if (auth) {
    const token = tokenStore.get()
    if (token) finalHeaders.Authorization = `Bearer ${token}`
  }

  const res = await fetch(url, {
    method,
    headers: finalHeaders,
    body
  })

  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await res.json().catch(() => null) : await res.text().catch(() => '')

  if (!res.ok) {
    const msg = typeof data === 'object' && data?.detail ? data.detail : `请求失败: ${res.status}`
    const err = new Error(msg)
    err.status = res.status
    err.data = data
    throw err
  }

  return data
}

export async function login(username, password) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)

  const data = await request('/auth/login', {
    method: 'POST',
    auth: false,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body
  })

  if (data?.access_token) tokenStore.set(data.access_token)
  return data
}

export async function me() {
  return request('/auth/me')
}

export async function register({ username, email, password }) {
  return request('/auth/register', {
    method: 'POST',
    auth: false,
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      username,
      email,
      password
    })
  })
}

export async function listSessions() {
  return request('/session')
}

export async function getSessionHistory(sessionId) {
  return request(`/session/${encodeURIComponent(sessionId)}/history`)
}

export async function createSession(title) {
  const qs = title ? `?title=${encodeURIComponent(title)}` : ''
  return request(`/session/create${qs}`, { method: 'POST' })
}

export async function updateSessionTitle(sessionId, title) {
  const qs = `?title=${encodeURIComponent(title)}`
  return request(`/session/${encodeURIComponent(sessionId)}/title${qs}`, {
    method: 'PUT'
  })
}

export async function deleteSession(sessionId) {
  return request(`/session/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

export async function rescueQuery({ query, chat_history = [], enable_web_search = false, enable_map = false, location = null, radius_km = 5, image_ids = [] }) {
  return request('/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query,
      chat_history,
      enable_web_search,
      enable_map,
      location,
      radius_km,
      image_ids
    })
  })
}

// SSE 流式请求方法
// 后端事件格式：
// event: delta
// data: {"text":"..."}
//
// event: done
// data: { session_id, used_web_search, used_map, evidences, rescue_resources, ... }
export async function rescueQueryStream({
  query,
  session_id = null,
  chat_history = [],
  enable_web_search = false,
  enable_map = false,
  location = null,
  radius_km = 5,
  image_ids = [],
  onDelta,
  onDone
} = {}) {
  const url = `${API_BASE_URL}/query/stream`

  const token = tokenStore.get()
  const body = {
    query,
    chat_history,
    enable_web_search,
    enable_map,
    location,
    radius_km,
    image_ids,
    ...(session_id ? { session_id } : {})
  }

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })

  if (!res.ok) {
    const isJson = (res.headers.get('content-type') || '').includes('application/json')
    const data = isJson ? await res.json().catch(() => null) : await res.text().catch(() => '')
    const msg = typeof data === 'object' && data?.detail ? data.detail : `请求失败: ${res.status}`
    const err = new Error(msg)
    err.status = res.status
    err.data = data
    throw err
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式响应')

  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const flush = () => {
    let idx
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const raw = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)

      const lines = raw.split('\n')
      let event = ''
      let dataLine = ''

      for (const l of lines) {
        if (l.startsWith('event:')) event = l.slice('event:'.length).trim()
        if (l.startsWith('data:')) dataLine += l.slice('data:'.length).trim()
      }

      if (!event || !dataLine) continue

      let payload
      try {
        payload = JSON.parse(dataLine)
      } catch {
        continue
      }

      if (event === 'delta') onDelta?.(payload)
      if (event === 'done') onDone?.(payload)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    flush()
  }

  flush()
}

export async function uploadImage(file, session_id = null) {
  const token = tokenStore.get()
  const form = new FormData()
  form.append('file', file)
  if (session_id) form.append('session_id', session_id)

  const res = await fetch(`${API_BASE_URL}/upload/image`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: form
  })

  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await res.json().catch(() => null) : await res.text().catch(() => '')

  if (!res.ok) {
    const msg = typeof data === 'object' && data?.detail ? data.detail : `请求失败: ${res.status}`
    const err = new Error(msg)
    err.status = res.status
    err.data = data
    throw err
  }

  return data
}
