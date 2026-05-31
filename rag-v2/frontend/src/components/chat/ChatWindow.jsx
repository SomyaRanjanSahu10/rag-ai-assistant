import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Sparkles, User, ChevronDown, FileText, Clock, Zap } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'
import { useTheme } from '../../context/ThemeContext'

// ── Source citation pill ───────────────────────────────────────────────────────
function SourcePill({ source }) {
  const name = source.filename || source.saved_name?.replace(/^[a-f0-9]{8}_/, '') || 'Unknown'
  const pct  = Math.round((source.avg_relevance || 0) * 100)
  return (
    <span className="inline-flex items-center gap-1.5 text-xs bg-blue-50 dark:bg-blue-900/30
                     border border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300
                     rounded-lg px-2 py-1 max-w-[200px]">
      <FileText size={11} className="flex-shrink-0" />
      <span className="truncate">{name}</span>
      <span className="text-blue-400 dark:text-blue-500 font-mono flex-shrink-0">{pct}%</span>
    </span>
  )
}

// ── Typing dots ────────────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <span className="inline-flex items-end gap-1 h-5">
      {[0, 1, 2].map(i => (
        <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce-dot"
              style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </span>
  )
}

// ── Code block with syntax highlighting ───────────────────────────────────────
function CodeBlock({ language, value, dark }) {
  return (
    <SyntaxHighlighter
      language={language || 'text'}
      style={dark ? oneDark : oneLight}
      customStyle={{ margin: 0, borderRadius: '10px', fontSize: '12px', lineHeight: '1.5' }}
      showLineNumbers={value.split('\n').length > 5}
    >
      {value}
    </SyntaxHighlighter>
  )
}

// ── Single message ─────────────────────────────────────────────────────────────
function Message({ message }) {
  const { dark } = useTheme()
  const isUser   = message.role === 'user'
  const [sourcesOpen, setSourcesOpen] = useRef ? [false, () => {}] : [false, () => {}]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={clsx('flex gap-3', isUser && 'flex-row-reverse')}
    >
      {/* Avatar */}
      <div className={clsx(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm',
        isUser
          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
          : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600'
      )}>
        {isUser ? <User size={14} /> : <Sparkles size={14} />}
      </div>

      {/* Bubble */}
      <div className={clsx('max-w-[78%] space-y-2', isUser && 'items-end flex flex-col')}>
        <div className={clsx(
          'rounded-2xl px-4 py-3',
          isUser
            ? 'bg-brand-500 text-white rounded-tr-sm'
            : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-tl-sm',
          message.isError && 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800',
        )}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className={clsx('prose-chat', message.isStreaming && !message.content && 'py-1')}>
              {message.content ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match  = /language-(\w+)/.exec(className || '')
                      const value  = String(children).replace(/\n$/, '')
                      if (!inline && match) {
                        return <CodeBlock language={match[1]} value={value} dark={dark} />
                      }
                      return <code className={className} {...props}>{children}</code>
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              ) : (
                <TypingDots />
              )}
              {message.isStreaming && message.content && <span className="typing-cursor" />}
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources?.length > 0 && !message.isStreaming && (
          <div className="px-1">
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-1.5 flex items-center gap-1">
              <Zap size={10} />
              Sources ({message.sources.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((s, i) => <SourcePill key={i} source={s} />)}
            </div>
          </div>
        )}

        {/* Timestamp + latency */}
        <p className={clsx('text-xs text-slate-400 dark:text-slate-500 px-1', isUser && 'text-right')}>
          {message.timestamp && formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
          {message.latency_ms && ` · ${(message.latency_ms / 1000).toFixed(1)}s`}
        </p>
      </div>
    </motion.div>
  )
}

// ── Welcome state ──────────────────────────────────────────────────────────────
function Welcome({ documentsCount }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full text-center px-8 pb-20"
    >
      <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-blue-500 to-indigo-600
                      flex items-center justify-center text-white mb-5 shadow-glow">
        <Sparkles size={28} />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">DocMind v2</h2>
      <p className="text-slate-500 dark:text-slate-400 max-w-sm text-sm leading-relaxed mb-6">
        Your private AI knowledge assistant with hybrid search, reranking, and persistent chat history.
      </p>
      {documentsCount > 0 ? (
        <div className="badge badge-green text-sm px-3 py-1.5">
          <span>{documentsCount} document{documentsCount !== 1 ? 's' : ''} ready in knowledge base</span>
        </div>
      ) : (
        <div className="card p-5 max-w-xs text-left space-y-2.5">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Get started</p>
          {['Upload documents using the sidebar', 'Ask questions in natural language', 'Get cited, accurate answers'].map((s, i) => (
            <p key={i} className="text-sm text-slate-600 dark:text-slate-400 flex items-start gap-2">
              <span className="text-brand-500 font-bold mt-0.5">{i + 1}.</span>{s}
            </p>
          ))}
        </div>
      )}
    </motion.div>
  )
}

// ── Chat input ─────────────────────────────────────────────────────────────────
import { useState, useCallback } from 'react'
import { Send } from 'lucide-react'

function ChatInput({ onSend, isLoading, disabled }) {
  const [text, setText] = useState('')
  const ref = useRef(null)

  const submit = useCallback(() => {
    const t = text.trim()
    if (!t || isLoading || disabled) return
    onSend(t)
    setText('')
    if (ref.current) ref.current.style.height = 'auto'
  }, [text, isLoading, disabled, onSend])

  return (
    <div className="border border-slate-200 dark:border-slate-600 rounded-2xl
                    focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-400/20
                    bg-white dark:bg-slate-800 transition-all duration-200">
      <div className="flex items-end gap-2 p-3">
        <textarea
          ref={ref}
          value={text}
          onChange={e => { setText(e.target.value); e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px' }}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          placeholder={disabled ? 'Upload documents to start chatting…' : 'Ask anything about your documents…'}
          disabled={isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-slate-900 dark:text-slate-100
                     placeholder-slate-400 dark:placeholder-slate-500 outline-none leading-relaxed py-1
                     disabled:opacity-50"
          style={{ maxHeight: 140 }}
        />
        <button
          onClick={submit}
          disabled={!text.trim() || isLoading || disabled}
          className="btn-primary p-2.5 rounded-xl flex-shrink-0 h-9 w-9 flex items-center justify-center"
        >
          {isLoading
            ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <Send size={15} />
          }
        </button>
      </div>
    </div>
  )
}

// ── Main ChatWindow ────────────────────────────────────────────────────────────
export function ChatWindow({ messages, isLoading, isStreaming, onSendMessage, documentsCount }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <Welcome documentsCount={documentsCount} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
            <AnimatePresence initial={false}>
              {messages.map(msg => <Message key={msg.id} message={msg} />)}
            </AnimatePresence>
            <div ref={bottomRef} className="h-1" />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-100 dark:border-slate-800 px-4 sm:px-6 py-4 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={onSendMessage} isLoading={isLoading} disabled={documentsCount === 0} />
          <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-2">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
