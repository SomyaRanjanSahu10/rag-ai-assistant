/**
 * AuthContext
 * ===========
 * Provides user state + login/logout/register to the whole app.
 * Tokens stored in localStorage with auto-refresh logic.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)  // true until initial auth check done

  // ── Bootstrap: verify stored token on mount ──────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      api.get('/api/auth/me')
        .then(({ data }) => setUser(data.user))
        .catch(() => _clearTokens())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  // ── Helpers ───────────────────────────────────────────────────────────────
  const _storeTokens = (access, refresh) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`
  }

  const _clearTokens = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/api/auth/login', { email, password })
    _storeTokens(data.access_token, data.refresh_token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (email, username, password, full_name) => {
    const { data } = await api.post('/api/auth/register', { email, username, password, full_name })
    _storeTokens(data.access_token, data.refresh_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    _clearTokens()
    toast.success('Logged out')
  }, [])

  const updateProfile = useCallback(async (updates) => {
    const { data } = await api.put('/api/auth/me', updates)
    setUser(data.user)
    return data.user
  }, [])

  const refreshAccessToken = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) throw new Error('No refresh token')
    const { data } = await api.post('/api/auth/refresh', { refresh_token: refresh })
    localStorage.setItem('access_token', data.access_token)
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    return data.access_token
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateProfile, refreshAccessToken }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
