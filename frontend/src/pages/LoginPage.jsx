import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShieldCheck, Eye, EyeOff, LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const ROLE_ROUTES = {
  MANUFACTURER: '/manufacturer',
  PHARMACIST: '/pharmacist',
  REGULATOR: '/admin',
  PUBLIC: '/',
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const user = await login(form.username, form.password)
      navigate(ROLE_ROUTES[user.role] || '/')
    } catch {
      setError('Invalid username or password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-dark flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-600 mb-4 shadow-2xl glow-blue">
            <ShieldCheck size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-black text-white">Sign In to <span className="gradient-text">MediVerify</span></h1>
          <p className="text-gray-500 text-sm mt-1">Access your dashboard</p>
        </div>

        {/* Login form */}
        <form onSubmit={handleLogin} className="glass rounded-2xl p-6 space-y-4">
          <div>
            <label className="label">Username</label>
            <input id="login-username" className="input" placeholder="username" value={form.username} onChange={set('username')} autoComplete="username" required />
          </div>
          <div>
            <label className="label">Password</label>
            <div className="relative">
              <input id="login-password" className="input pr-10" type={showPwd ? 'text' : 'password'} placeholder="••••••" value={form.password} onChange={set('password')} autoComplete="current-password" required />
              <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          {error && <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>}
          <button type="submit" id="login-submit-btn" disabled={loading} className="btn-primary w-full disabled:opacity-50">
            {loading ? <><div className="spinner w-4 h-4" /> Signing in…</> : <><LogIn size={16} /> Sign In</>}
          </button>
        </form>

        <p className="text-center text-xs text-gray-700 mt-4">
          Public medicine verification doesn't require login.{' '}
          <a href="/" className="text-brand-400 hover:underline">Verify a medicine →</a>
        </p>
        <p className="mt-3 text-center text-sm text-gray-500">
          New to MediVerify? <Link to="/register" className="text-brand-300 hover:underline">Create an account</Link>
        </p>
      </div>
    </div>
  )
}
