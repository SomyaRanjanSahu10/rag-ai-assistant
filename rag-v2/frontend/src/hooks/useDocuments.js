import { useState, useEffect, useCallback } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'

export function useDocuments() {
  const [documents, setDocuments]   = useState([])
  const [uploadQueue, setQueue]     = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading]   = useState(false)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const { data } = await api.get('/api/documents')
      setDocuments(data.documents || [])
    } catch (err) {
      toast.error('Failed to load documents')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const upload = useCallback(async (files) => {
    const arr = Array.isArray(files) ? files : [files]
    for (const file of arr) {
      const qid = `${file.name}-${Date.now()}`
      setQueue(prev => [...prev, { id: qid, name: file.name, progress: 0, status: 'uploading' }])
      const form = new FormData()
      form.append('file', file)
      try {
        await api.post('/api/upload', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: ({ loaded, total }) => {
            setQueue(prev => prev.map(q => q.id === qid ? { ...q, progress: Math.round(loaded * 100 / total) } : q))
          },
        })
        setQueue(prev => prev.map(q => q.id === qid ? { ...q, progress: 100, status: 'done' } : q))
        toast.success(`'${file.name}' uploaded — indexing in background`)
        setTimeout(() => { setQueue(prev => prev.filter(q => q.id !== qid)); load() }, 2500)
      } catch (err) {
        toast.error(err.displayMessage || 'Upload failed')
        setQueue(prev => prev.map(q => q.id === qid ? { ...q, status: 'error', error: err.displayMessage } : q))
      }
    }
  }, [load])

  const remove = useCallback(async (docId, name) => {
    try {
      await api.delete(`/api/documents/${docId}`)
      setDocuments(prev => prev.filter(d => d.id !== docId))
      toast.success(`'${name}' deleted`)
    } catch (err) {
      toast.error(err.displayMessage || 'Delete failed')
    }
  }, [])

  const filtered = documents.filter(d =>
    !searchQuery || d.original_name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return { documents: filtered, allDocuments: documents, uploadQueue, isLoading, searchQuery, setSearchQuery, upload, remove, refresh: load }
}
