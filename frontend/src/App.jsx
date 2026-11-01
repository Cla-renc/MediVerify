import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { LangProvider } from './context/LangContext'
import Navbar from './components/Navbar'
import VerifyPage from './pages/VerifyPage'
import LoginPage from './pages/LoginPage'
import ManufacturerPage from './pages/ManufacturerPage'
import PharmacistPage from './pages/PharmacistPage'
import AdminPage from './pages/AdminPage'
import SimulatorPage from './pages/SimulatorPage'
import ReportPage from './pages/ReportPage'

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen bg-gradient-dark flex items-center justify-center">
      <div className="text-center">
        <div className="spinner w-10 h-10 mx-auto mb-4" style={{ borderWidth: 3 }} />
        <p className="text-gray-600 text-sm">Loading MediVerify…</p>
      </div>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

function AppRoutes() {
  return (
    <div className="min-h-screen bg-gradient-dark">
      <Navbar />
      <Routes>
        <Route path="/" element={<VerifyPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/simulator" element={<SimulatorPage />} />

        <Route path="/manufacturer" element={
          <ProtectedRoute roles={['MANUFACTURER', 'REGULATOR']}>
            <ManufacturerPage />
          </ProtectedRoute>
        } />

        <Route path="/pharmacist" element={
          <ProtectedRoute roles={['PHARMACIST', 'REGULATOR']}>
            <PharmacistPage />
          </ProtectedRoute>
        } />

        <Route path="/admin" element={
          <ProtectedRoute roles={['REGULATOR']}>
            <AdminPage />
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LangProvider>
          <AppRoutes />
        </LangProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
