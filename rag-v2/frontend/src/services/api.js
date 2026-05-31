/**
 * API Service
 * ===========
 * Axios instance with:
 *   - Base URL from env
 *   - Auto token refresh on 401
 *   - Consistent error extraction
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL, timeout: 30000 })

// ── Request interceptor: attach current access token ──────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: auto-refresh on 401 ────────────────────────────────
let _refreshing = false
let _queue = []

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const status   = error.response?.status

    if (status === 401 && !original._retry) {
      if (_refreshing) {
        return new Promise((resolve, reject) => {
          _queue.push({ resolve, reject })
        }).then(token => {
          original.headers.Authorization = `Bearer ${token}`
          return api(original)
        })
      }

      original._retry = true
      _refreshing = true

      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) throw new Error('No refresh token')
        const { data } = await axios.post(`${BASE_URL}/api/auth/refresh`, { refresh_token: refresh })
        const newToken = data.access_token
        localStorage.setItem('access_token', newToken)
        api.defaults.headers.common.Authorization = `Bearer ${newToken}`
        _queue.forEach(q => q.resolve(newToken))
        _queue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch (refreshErr) {
        _queue.forEach(q => q.reject(refreshErr))
        _queue = []
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshErr)
      } finally {
        _refreshing = false
      }
    }

    // Extract readable message
    const message = error.response?.data?.error?.message
      || error.response?.data?.detail
      || error.message
      || 'Request failed'
    error.displayMessage = message
    return Promise.reject(error)
  }
)

// ── Streaming helper (Fetch API, bypasses axios for SSE) ──────────────────────
export async function streamChat(sessionId, body, { onStart, onToken, onDone, onError }) {
  const token = localStorage.getItem('access_token')
  try {
    const res = await fetch(`${BASE_URL}/api/chat/sessions/${sessionId}/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error?.message || `HTTP ${res.status}`)
    }

    const reader  = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const events = buf.split('\n\n')
      buf = events.pop() || ''
      for (const ev of events) {
        if (!ev.startsWith('data: ')) continue
        try {
          const d = JSON.parse(ev.slice(6))
          if (d.type === 'start')  onStart?.(d)
          if (d.type === 'token')  onToken?.(d.content)
          if (d.type === 'done')   onDone?.(d)
          if (d.type === 'error')  onError?.(new Error(d.message))
        } catch { /* skip malformed */ }
      }
    }
  } catch (err) {
    onError?.(err)
  }
}

export default api
