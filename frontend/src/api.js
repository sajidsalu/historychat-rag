const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!res.ok) {
    const detail = data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
          : `Request failed (${res.status})`
    throw new ApiError(message, res.status)
  }

  return data
}

export const authApi = {
  signup: (email, password) =>
    api('/auth/signup', { method: 'POST', body: { email, password } }),
  login: (email, password) =>
    api('/auth/login', { method: 'POST', body: { email, password } }),
  me: (token) => api('/auth/me', { token }),
}

export const personalitiesApi = {
  list: (token) => api('/personalities', { token }),
  search: (token, name) =>
    api('/personalities/search', { method: 'POST', token, body: { name } }),
  status: (token, id) => api(`/personalities/${id}/status`, { token }),
  messages: (token, id) => api(`/personalities/${id}/messages`, { token }),
}

export const chatApi = {
  send: (token, personalityId, message) =>
    api('/chat', {
      method: 'POST',
      token,
      body: { personality_id: personalityId, message },
    }),
}
