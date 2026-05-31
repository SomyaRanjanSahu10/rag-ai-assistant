import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, MessageSquare, Trash2, Edit3, Check, X,
  ChevronLeft, Zap, FileText, Image as ImageIcon,
  File, Search, MoreHorizontal, FolderOpen, Clock
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'
import { UploadZone } from '../upload/UploadZone'

// ── Session Item ───────────────────────────────────────────────────────────────
function SessionItem({ session, isActive, onSelect, onRename, onDelete }) {
  const [editing, setEditing]   = useState(false)
  const [title, setTitle]       = useState(session.title)
  const [showMenu, setShowMenu] = useState(false)

  const commitRename = () => {
    if (title.trim() && title !== session.title) onRename(session.id, title.trim())
    setEditing(false)
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className={clsx(
        'group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer',
        'transition-all duration-150 text-sm',
        isActive
          ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-slate-900 dark:hover:text-slate-200',
      )}
      onClick={() => !editing && onSelect(session)}
    >
      <MessageSquare size={14} className="flex-shrink-0 opacity-60" />

      {editing ? (
        <input
          autoFocus
          value={title}
          onChange={e => setTitle(e.target.value)}
          onBlur={commitRename}
          onKeyDown={e => { if (e.key === 'Enter') commitRename(); if (e.key === 'Escape') setEditing(false) }}
          className="flex-1 bg-transparent outline-none text-sm min-w-0"
          onClick={e => e.stopPropagation()}
        />
      ) : (
        <span className="flex-1 truncate text-sm leading-tight">{session.title}</span>
      )}

      {/* Actions — visible on hover */}
      <div className={clsx('flex gap-0.5 flex-shrink-0', 'opacity-0 group-hover:opacity-100', isActive && 'opacity-100')}>
        <button className="btn-ghost p-1 rounded-md" onClick={e => { e.stopPropagation(); setEditing(true) }} title="Rename">
          <Edit3 size={12} />
        </button>
        <button className="btn-ghost p-1 rounded-md text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950" onClick={e => { e.stopPropagation(); onDelete(session.id) }} title="Delete">
          <Trash2 size={12} />
        </button>
      </div>
    </motion.div>
  )
}

// ── Document Card (compact) ────────────────────────────────────────────────────
const TYPE_ICONS = {
  pdf:   { Icon: FileText, cls: 'text-red-500' },
  docx:  { Icon: FileText, cls: 'text-blue-500' },
  txt:   { Icon: FileText, cls: 'text-green-500' },
  image: { Icon: ImageIcon, cls: 'text-purple-500' },
}

function DocCard({ doc, onDelete }) {
  const [confirm, setConfirm] = useState(false)
  const { Icon, cls } = TYPE_ICONS[doc.file_type] || { Icon: File, cls: 'text-slate-400' }
  const displayName = doc.original_name || doc.saved_name || 'Unknown'
  const size = doc.file_size ? `${(doc.file_size / 1024).toFixed(0)} KB` : '—'

  return (
    <div className="group flex items-start gap-2.5 px-2 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors">
      <Icon size={15} className={clsx('mt-0.5 flex-shrink-0', cls)} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">{displayName}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          {size} ·{' '}
          <span className={clsx('font-medium', doc.status === 'ready' ? 'text-green-500' : doc.status === 'error' ? 'text-red-500' : 'text-yellow-500')}>
            {doc.status}
          </span>
        </p>
      </div>
      <button
        onClick={() => confirm ? onDelete(doc.id, doc.original_name) : setConfirm(true)}
        onBlur={() => setTimeout(() => setConfirm(false), 200)}
        className={clsx(
          'opacity-0 group-hover:opacity-100 p-1 rounded transition-all',
          confirm ? 'text-red-500 bg-red-50 dark:bg-red-950 opacity-100' : 'text-slate-400 hover:text-red-500'
        )}
        title={confirm ? 'Click again to confirm' : 'Delete'}
      >
        <Trash2 size={12} />
      </button>
    </div>
  )
}

// ── Sidebar ────────────────────────────────────────────────────────────────────
export function Sidebar({
  sessions, activeSession, onNewChat, onSelectSession, onRenameSession, onDeleteSession,
  documents, uploadQueue, onUpload, onDeleteDoc,
  onClose,
}) {
  const [tab, setTab] = useState('chats') // 'chats' | 'docs'
  const [docSearch, setDocSearch] = useState('')

  const filteredDocs = documents.filter(d =>
    !docSearch || d.original_name?.toLowerCase().includes(docSearch.toLowerCase())
  )

  return (
    <div className="w-64 h-screen flex flex-col border-r border-slate-200 dark:border-slate-700
                    bg-white dark:bg-slate-900 flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600
                          flex items-center justify-center shadow-sm">
            <Zap size={14} className="text-white" />
          </div>
          <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">DocMind</span>
        </div>
        <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg">
          <ChevronLeft size={15} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-3">
        <button onClick={onNewChat} className="btn-primary w-full justify-center text-xs py-2">
          <Plus size={14} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 mx-3 mb-3 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
        {['chats', 'docs'].map(t => (
          <button key={t} onClick={() => setTab(t)}
                  className={clsx('flex-1 text-xs py-1.5 rounded-md font-medium capitalize transition-all',
                    tab === t ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm' : 'text-slate-500 dark:text-slate-400')}>
            {t === 'chats' ? `Chats (${sessions.length})` : `Docs (${documents.length})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {tab === 'chats' ? (
          <div className="px-2 space-y-0.5 pb-4">
            {sessions.length === 0 ? (
              <div className="text-center py-10">
                <MessageSquare size={24} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs text-slate-400 dark:text-slate-500">No conversations yet</p>
              </div>
            ) : (
              sessions.map(s => (
                <SessionItem
                  key={s.id}
                  session={s}
                  isActive={activeSession?.id === s.id}
                  onSelect={onSelectSession}
                  onRename={onRenameSession}
                  onDelete={onDeleteSession}
                />
              ))
            )}
          </div>
        ) : (
          <div className="px-3 pb-4 space-y-3">
            {/* Upload zone */}
            <UploadZone onUpload={onUpload} uploadQueue={uploadQueue} compact />

            {/* Search */}
            {documents.length > 3 && (
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={docSearch}
                  onChange={e => setDocSearch(e.target.value)}
                  placeholder="Search files…"
                  className="input pl-8 text-xs py-1.5"
                />
              </div>
            )}

            {/* Document list */}
            {filteredDocs.length === 0 ? (
              <div className="text-center py-6">
                <FolderOpen size={24} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs text-slate-400">No documents yet</p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredDocs.map((doc, i) => (
                  <DocCard key={doc.id || i} doc={doc} onDelete={onDeleteDoc} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
