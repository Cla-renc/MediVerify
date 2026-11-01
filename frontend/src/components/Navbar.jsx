import { Link, useNavigate, useLocation } from 'react-router-dom'
import { ShieldCheck, Menu, X, Globe, LogOut, User, LayoutDashboard } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LangContext'

const ROLE_DASHBOARDS = {
  MANUFACTURER: '/manufacturer',
  PHARMACIST: '/pharmacist',
  REGULATOR: '/admin',
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const { lang, toggleLang } = useLang()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const dashboardPath = user ? ROLE_DASHBOARDS[user.role] : null

  return (
    <nav className="sticky top-0 z-50 glass border-b border-white/10 border-x-0 border-t-0 rounded-none">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <span className="font-black text-lg tracking-tight text-white">
            Medi<span className="gradient-text">Verify</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-2">
          {dashboardPath && (
            <Link to={dashboardPath} className="btn-secondary text-xs py-2 px-4">
              <LayoutDashboard size={15} />
              Dashboard
            </Link>
          )}

          {/* Language toggle */}
          <button
            onClick={toggleLang}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-white/5 transition-all"
            title="Toggle English / Swahili"
          >
            <Globe size={15} />
            {lang === 'en' ? 'SW' : 'EN'}
          </button>

          {user ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg glass text-xs">
                <User size={13} className="text-brand-400" />
                <span className="text-gray-300 font-medium">{user.username}</span>
                <span className="text-xs text-gray-600 bg-white/5 px-2 py-0.5 rounded-full">{user.role}</span>
              </div>
              <button onClick={handleLogout} className="btn-secondary text-xs py-2 px-3">
                <LogOut size={14} /> Sign Out
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn-primary text-xs py-2 px-4">
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden glass border-t border-white/10 rounded-none px-4 py-3 space-y-2 animate-fade-in">
          {dashboardPath && (
            <Link to={dashboardPath} onClick={() => setOpen(false)} className="flex items-center gap-2 py-2 text-sm text-gray-300 hover:text-white">
              <LayoutDashboard size={16} /> Dashboard
            </Link>
          )}
          <button onClick={() => { toggleLang(); setOpen(false) }} className="flex items-center gap-2 py-2 text-sm text-gray-300 hover:text-white w-full">
            <Globe size={16} /> {lang === 'en' ? 'Kiswahili' : 'English'}
          </button>
          {user ? (
            <button onClick={() => { handleLogout(); setOpen(false) }} className="flex items-center gap-2 py-2 text-sm text-red-400 hover:text-red-300 w-full">
              <LogOut size={16} /> Sign Out ({user.username})
            </button>
          ) : (
            <Link to="/login" onClick={() => setOpen(false)} className="flex items-center gap-2 py-2 text-sm text-brand-400 hover:text-brand-300">
              Sign In
            </Link>
          )}
        </div>
      )}
    </nav>
  )
}
