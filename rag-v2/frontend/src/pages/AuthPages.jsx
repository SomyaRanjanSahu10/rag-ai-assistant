/**
 * Auth Pages — Login + Register
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Zap, Mail, Lock, User, ArrowRight, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import clsx from 'clsx'

function AuthCard({ children, title, subtitle }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-blue-950
                    flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl
                          bg-gradient-to-br from-blue-500 to-indigo-600 text-white mb-4 shadow-lg">
            <Zap size={22} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{title}</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{subtitle}</p>
        </div>

        <div className="card p-8 shadow-glass dark:shadow-none">{children}</div>
      </motion.div>
    </div>
  )
}

function Field({ label, type = 'text', icon: Icon, value, onChange, placeholder, error }) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{label}</label>
      <div className="relative">
        {Icon && <Icon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />}
        <input
          type={isPassword && show ? 'text' : type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className={clsx('input', Icon && 'pl-9', isPassword && 'pr-10', error && 'border-red-400 focus:ring-red-300')}
        />
        {isPassword && (
          <button type="button" onClick={() => setShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

// ── Login Page ─────────────────────────────────────────────────────────────────
export function LoginPage() {
  const { login } = useAuth()
  const navigate  = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) return toast.error('Please fill all fields')
    setLoading(true)
    try {
      await login(email, password)
      toast.success('Welcome back!')
      navigate('/')
    } catch (err) {
      toast.error(err.displayMessage || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard title="Welcome back" subtitle="Sign in to DocMind">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email" type="email" icon={Mail} value={email} onChange={setEmail} placeholder="you@example.com" />
        <Field label="Password" type="password" icon={Lock} value={password} onChange={setPassword} placeholder="••••••••" />

        <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <><span>Sign in</span><ArrowRight size={16} /></>}
        </button>
      </form>

      <p className="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
        No account?{' '}
        <Link to="/register" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
          Create one
        </Link>
      </p>
    </AuthCard>
  )
}

// ── Register Page ─────────────────────────────────────────────────────────────
export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', full_name: '' })
  const [loading, setLoading] = useState(false)

  const set = (key) => (val) => setForm(f => ({ ...f, [key]: val }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.email || !form.username || !form.password) return toast.error('Fill all required fields')
    if (form.password.length < 8) return toast.error('Password must be at least 8 characters')
    setLoading(true)
    try {
      await register(form.email, form.username, form.password, form.full_name)
      toast.success('Account created! Welcome to DocMind 🎉')
      navigate('/')
    } catch (err) {
      toast.error(err.displayMessage || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard title="Create account" subtitle="Start your DocMind journey">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Full name (optional)" icon={User} value={form.full_name} onChange={set('full_name')} placeholder="Jane Doe" />
        <Field label="Email *" type="email" icon={Mail} value={form.email} onChange={set('email')} placeholder="you@example.com" />
        <Field label="Username *" icon={User} value={form.username} onChange={set('username')} placeholder="janedoe" />
        <Field label="Password *" type="password" icon={Lock} value={form.password} onChange={set('password')} placeholder="min. 8 characters" />

        <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <><span>Create account</span><ArrowRight size={16} /></>}
        </button>
      </form>

      <p className="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
        Already have an account?{' '}
        <Link to="/login" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </AuthCard>
  )
}
