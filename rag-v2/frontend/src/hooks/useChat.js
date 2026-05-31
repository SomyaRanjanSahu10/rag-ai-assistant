import { useState, useCallback, useRef } from 'react'
import { streamChat } from '../services/api'
import api from '../services/api'
import toast from 'react-hot-toast'

export function useChat() {
  const [sessions, setSessions]       = useState([])
  const [activeSession, setActive]    = useState(null)
  const [messages, setMessages]       = useState([])
  const [isLoading, setIsLoading]     = useState(false)
  const [isStreaming, setIsStreaming]  = useState(false)
  const abortRef = useRef(false)

  // ── Session management ────────────────────────────────────────────────────
  const loadSessions = useCallback(async () => {
    try {
      const { data } = await api.get('/api/chat/sessions')
      setSessions(data.sessions || [])
    } catch (err) {
      toast.error('Failed to load chat history')
    }
  }, [])

  const createSession = useCallback(async (model = 'llama-3.3-70b-versatile') => {
    const { data } = await api.post('/api/chat/sessions', { model })
    const session  = data.session
    setSessions(prev => [session, ...prev])
    setActive(session)
    setMessages([])
    return session
  }, [])

  const openSession = useCallback(async (session) => {
    setActive(session)
    const { data } = await api.get(`/api/chat/sessions/${session.id}`)
    setMessages(data.messages || [])
  }, [])

  const renameSession = useCallback(async (sessionId, title) => {
    await api.put(`/api/chat/sessions/${sessionId}`, { title })
    setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title } : s))
    if (activeSession?.id === sessionId) setActive(s => ({ ...s, title }))
  }, [activeSession])

  const deleteSession = useCallback(async (sessionId) => {
    await api.delete(`/api/chat/sessions/${sessionId}`)
    setSessions(prev => prev.filter(s => s.id !== sessionId))
    if (activeSession?.id === sessionId) {
      setActive(null)
      setMessages([])
    }
  }, [activeSession])

  // ── Messaging ─────────────────────────────────────────────────────────────
  const sendMessage = useCallback(async (text, options = {}) => {
    if (!text.trim() || isLoading) return

    // Ensure we have a session
    let session = activeSession
    if (!session) {
      session = await createSession(options.model)
    }

    abortRef.current = false
    setIsLoading(true)

    const userMsg = { id: Date.now(), role: 'user', content: text, timestamp: new Date().toISOString() }
    const asstMsg = { id: Date.now() + 1, role: 'assistant', content: '', sources: [], isStreaming: true, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg, asstMsg])
    setIsStreaming(true)

    await streamChat(
      session.id,
      { message: text, n_results: options.nResults || 6, model: options.model || 'llama-3.3-70b-versatile' },
      {
        onStart: ({ chunks_found, sources }) => {
          setMessages(prev => prev.map(m => m.id === asstMsg.id ? { ...m, chunksFound: chunks_found, sources } : m))
        },
        onToken: (token) => {
          if (abortRef.current) return
          setMessages(prev => prev.map(m => m.id === asstMsg.id ? { ...m, content: m.content + token } : m))
        },
        onDone: ({ sources, latency_ms }) => {
          setMessages(prev => prev.map(m => m.id === asstMsg.id ? { ...m, sources, latency_ms, isStreaming: false } : m))
          // Update session title in list (backend auto-generates it)
          setTimeout(() => loadSessions(), 1000)
          setIsStreaming(false)
          setIsLoading(false)
        },
        onError: (err) => {
          toast.error(err.message)
          setMessages(prev => prev.map(m => m.id === asstMsg.id ? { ...m, content: `❌ ${err.message}`, isStreaming: false, isError: true } : m))
          setIsStreaming(false)
          setIsLoading(false)
        },
      }
    )
  }, [activeSession, isLoading, createSession, loadSessions])

  const clearMessages = useCallback(() => {
    abortRef.current = true
    setMessages([])
  }, [])

  return {
    sessions, activeSession, messages, isLoading, isStreaming,
    loadSessions, createSession, openSession, renameSession, deleteSession,
    sendMessage, clearMessages,
  }
}
