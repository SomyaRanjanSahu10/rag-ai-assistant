import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'

import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { Sidebar } from './components/layout/Sidebar'
import { Navbar } from './components/layout/Navbar'
import { ChatWindow } from './components/chat/ChatWindow'
import { useChat } from './hooks/useChat'
import { useDocuments } from './hooks/useDocuments'

function ChatApp() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const chat = useChat()
  const docs = useDocuments()

  // Load sessions on mount
  useEffect(() => { chat.loadSessions() }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.div
            key="sidebar"
            initial={{ x: -260, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -260, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="flex-shrink-0"
          >
            <Sidebar
              sessions={chat.sessions}
              activeSession={chat.activeSession}
              onNewChat={chat.createSession}
              onSelectSession={chat.openSession}
              onRenameSession={chat.renameSession}
              onDeleteSession={chat.deleteSession}
              documents={docs.documents}
              uploadQueue={docs.uploadQueue}
              onUpload={docs.upload}
              onDeleteDoc={docs.remove}
              onClose={() => setSidebarOpen(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <Navbar
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(o => !o)}
          sessionTitle={chat.activeSession?.title}
        />
        <ChatWindow
          messages={chat.messages}
          isLoading={chat.isLoading}
          isStreaming={chat.isStreaming}
          onSendMessage={chat.sendMessage}
          documentsCount={docs.allDocuments?.length || docs.documents.length}
        />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login"    element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/*" element={
              <ProtectedRoute>
                <ChatApp />
              </ProtectedRoute>
            } />
          </Routes>

          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3500,
              style: {
                fontSize: '13px',
                maxWidth: '380px',
                borderRadius: '10px',
              },
            }}
          />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
