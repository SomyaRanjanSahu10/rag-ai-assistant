import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Moon, Sun, PanelLeft, User, LogOut, Settings, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'

function UserMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initial = user?.username?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 hover:bg-slate-100 dark:hover:bg-slate-700 px-2 py-1.5 rounded-lg transition-colors"
      >
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600
                        flex items-center justify-center text-white text-xs font-bold">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
          ) : initial}
        </div>
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300 max-w-[100px] truncate hidden sm:block">
          {user?.full_name || user?.username}
        </span>
        <ChevronDown size={14} className="text-slate-400 hidden sm:block" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            className="absolute right-0 top-full mt-2 w-52 card shadow-lg py-1 z-50"
          >
            <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-700">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{user?.full_name || user?.username}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user?.email}</p>
            </div>
            <button onClick={onLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 dark:text-red-400
                               hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors">
              <LogOut size={14} />
              <span>Sign out</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function Navbar({ sidebarOpen, onToggleSidebar, sessionTitle }) {
  const { user, logout } = useAuth()
  const { dark, toggle } = useTheme()

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700
                    bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm flex-shrink-0">
      <div className="flex items-center gap-3">
        {!sidebarOpen && (
          <button onClick={onToggleSidebar} className="btn-ghost p-2 rounded-lg">
            <PanelLeft size={18} />
          </button>
        )}
        <div>
          <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate max-w-xs">
            {sessionTitle || 'DocMind'}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        {/* Theme toggle */}
        <button onClick={toggle} className="btn-ghost p-2 rounded-lg" title="Toggle theme">
          {dark ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {/* User menu */}
        {user && <UserMenu user={user} onLogout={logout} />}
      </div>
    </div>
  )
}
