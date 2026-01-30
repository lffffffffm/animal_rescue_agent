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
  const body = new URLSearchParams()
  body.set('title', title)
  return request(`/session/${encodeURIComponent(sessionId)}/title`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body
  })
}

export async function deleteSession(sessionId) {
  return request(`/session/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

export async function rescueQuery({ query, chat_history = [], enable_web_search = false, enable_map = false, location = null, radius_km = null }) {
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
      radius_km
    })
  })
}

