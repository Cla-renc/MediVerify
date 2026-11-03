import { useState, useEffect, useCallback } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { ShieldAlert, CheckCircle, XCircle, AlertTriangle, RefreshCw, Settings, Users, Map as MapIcon } from 'lucide-react'
import {
  getCloneAlerts, resolveCloneAlert,
  getCloneModel, retrainCloneModel,
  getReports, getHeatmapData,
  getSystemSettings, updateSystemSettings,
  getPharmacyTrustRatings, getBatches, getCloneAlertSocketURL
} from '../services/api'
import { useAuth } from '../context/AuthContext'
import 'leaflet/dist/leaflet.css'

const MARKER_COLORS = {
  SUSPICIOUS_REPORT: '#f59e0b',
  CLONE_ALERT: '#8b5cf6',
}

export default function AdminPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState('overview')
  const [cloneAlerts, setCloneAlerts] = useState([])
  const [reports, setReports] = useState([])
  const [heatmap, setHeatmap] = useState({ markers: [] })
  const [pharmacies, setPharmacies] = useState([])
  const [batches, setBatches] = useState([])
  const [settings, setSettings] = useState(null)
  const [model, setModel] = useState(null)
  const [retraining, setRetraining] = useState(false)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [alertConnection, setAlertConnection] = useState('connecting')

  const showToast = useCallback((msg, type='success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  useEffect(() => { fetchAll() }, [])

  useEffect(() => {
    if (user?.role !== 'REGULATOR') return undefined
    let active = true
    let socket
    let reconnectTimer
    let reconnectDelay = 1000

    const connect = () => {
      if (!active) return
      const token = localStorage.getItem('mv_access_token')
      if (!token) {
        setAlertConnection('disconnected')
        return
      }
      setAlertConnection('connecting')
      socket = new WebSocket(getCloneAlertSocketURL(), ['mediverify', token])
      socket.onopen = () => {
        reconnectDelay = 1000
        if (active) setAlertConnection('connected')
      }
      socket.onmessage = async event => {
        let notification
        try {
          notification = JSON.parse(event.data)
        } catch {
          return
        }
        if (notification.type !== 'clone_alert' || !active) return
        try {
          const response = await getCloneAlerts()
          setCloneAlerts(response.data.results || response.data)
        } catch {
          showToast('A live clone alert arrived, but the alert list could not refresh.', 'error')
        }
        showToast(
          `${notification.is_new ? 'New' : 'Updated'} clone alert: ${notification.product_brand_name} · risk ${Math.round(notification.risk_score)}%.`,
          'error',
        )
      }
      socket.onclose = () => {
        if (!active) return
        setAlertConnection('reconnecting')
        reconnectTimer = window.setTimeout(connect, reconnectDelay)
        reconnectDelay = Math.min(reconnectDelay * 2, 30000)
      }
      socket.onerror = () => socket.close()
    }

    connect()
    return () => {
      active = false
      window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [user?.role, showToast])

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [a, r, h, p, b, s, m] = await Promise.all([
        getCloneAlerts(), getReports(), getHeatmapData(),
        getPharmacyTrustRatings(), getBatches(), getSystemSettings(), getCloneModel()
      ])
      setCloneAlerts(a.data.results || a.data)
      setReports(r.data.results || r.data)
      setHeatmap(h.data)
      setPharmacies(p.data.results || p.data)
      setBatches(b.data.results || b.data)
      setSettings(s.data)
      setModel(m.data)
    } catch { showToast('Failed to load dashboard data.', 'error') }
    finally { setLoading(false) }
  }

  const handleResolveAlert = async (id, status) => {
    try {
      await resolveCloneAlert(id, status)
      showToast(`Alert ${status === 'CONFIRMED' ? 'confirmed as clone' : 'dismissed'}.`, status === 'CONFIRMED' ? 'error' : 'success')
      fetchAll()
    } catch { showToast('Failed to resolve alert.', 'error') }
  }

  const handleSaveSettings = async () => {
    try {
      await updateSystemSettings(settings)
      showToast('Detection engine settings saved.')
    } catch { showToast('Failed to save settings.', 'error') }
  }

  const handleRetrainModel = async () => {
    setRetraining(true)
    try {
      const response = await retrainCloneModel()
      setModel(response.data)
      showToast(`Clone model ${response.data.version} trained on ${response.data.training_samples} samples.`)
    } catch (error) {
      showToast(error.response?.data?.error || 'Failed to retrain clone model.', 'error')
    } finally {
      setRetraining(false)
    }
  }

  const pending = cloneAlerts.filter(a => a.status === 'PENDING').length
  const recalledBatches = batches.filter(b => b.is_recalled).length
  const pendingReports = reports.filter(r => r.status === 'PENDING').length

  const trustData = [
    { name: 'Trusted', count: pharmacies.filter(p => p.trust_rating === 'TRUSTED').length, color: '#10b981' },
    { name: 'Watch', count: pharmacies.filter(p => p.trust_rating === 'WATCH').length, color: '#f59e0b' },
    { name: 'Flagged', count: pharmacies.filter(p => p.trust_rating === 'FLAGGED').length, color: '#ef4444' },
  ]

  const TABS = ['overview', 'clone_alerts', 'heatmap', 'pharmacies', 'model', 'settings']

  return (
    <div className="min-h-screen bg-gradient-dark">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl text-sm font-medium shadow-xl animate-slide-up ${
          toast.type === 'error' ? 'bg-red-500/20 border border-red-500/40 text-red-300' : 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300'
        }`}>{toast.msg}</div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-white">Regulator Dashboard</h1>
            <p className="text-gray-500 text-sm mt-1">Pharmacy &amp; Poisons Board Kenya · <span className="text-brand-400">{user?.username}</span></p>
            <p className={`mt-1 text-xs ${alertConnection === 'connected' ? 'text-emerald-300' : 'text-amber-300'}`}>
              {alertConnection === 'connected' ? '● Live clone alerts connected' : '○ Live clone alerts reconnecting'}
            </p>
          </div>
          <button onClick={fetchAll} className="btn-secondary text-xs gap-1.5">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Pending Clone Alerts', value: pending, color: 'purple', urgent: pending > 0 },
            { label: 'Recalled Batches', value: recalledBatches, color: 'red', urgent: recalledBatches > 0 },
            { label: 'Pending Reports', value: pendingReports, color: 'amber', urgent: pendingReports > 0 },
            { label: 'Pharmacies Monitored', value: pharmacies.length, color: 'blue', urgent: false },
          ].map(({ label, value, color, urgent }) => (
            <div key={label} className={`glass rounded-xl p-4 glass-hover border ${urgent ? `border-${color === 'red' ? 'red' : color === 'purple' ? 'violet' : color === 'amber' ? 'amber' : 'brand'}-500/40` : 'border-white/5'}`}>
              <div className={`text-xs font-semibold mb-1 ${color === 'blue' ? 'text-brand-400' : color === 'amber' ? 'text-amber-400' : color === 'red' ? 'text-red-400' : 'text-violet-400'}`}>{label}</div>
              <div className="text-3xl font-black text-white">{value}</div>
              {urgent && <div className="text-xs text-red-400 mt-1 font-medium animate-pulse">● Action Required</div>}
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-1 glass rounded-xl p-1 w-fit mb-6">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all ${tab === t ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30' : 'text-gray-500 hover:text-gray-300'}`}>
              {t.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* ── Overview Tab ── */}
        {tab === 'overview' && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Trust rating chart */}
            <div className="glass rounded-2xl p-5">
              <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Users size={16} className="text-brand-400" /> Pharmacy Trust Distribution</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={trustData}>
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#0d1a35', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {trustData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Recent clone alerts */}
            <div className="glass rounded-2xl p-5">
              <h3 className="font-bold text-white mb-4 flex items-center gap-2"><ShieldAlert size={16} className="text-violet-400" /> Recent Clone Alerts</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {cloneAlerts.slice(0, 5).map(a => (
                  <div key={a.id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-white/5">
                    <div>
                      <p className="text-xs font-mono text-violet-400">{a.secure_code?.slice(0,20)}…</p>
                      <p className="text-xs text-gray-600">{a.product_brand_name} · Risk: <span className={a.risk_score >= 80 ? 'text-red-400 font-bold' : 'text-amber-400 font-bold'}>{a.risk_score}%</span></p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${a.status === 'PENDING' ? 'badge-clone' : a.status === 'CONFIRMED' ? 'badge-recalled' : 'badge-invalid'}`}>{a.status}</span>
                  </div>
                ))}
                {!cloneAlerts.length && <p className="text-gray-600 text-xs text-center py-6">No clone alerts detected.</p>}
              </div>
            </div>
          </div>
        )}

        {/* ── Clone Alerts Tab ── */}
        {tab === 'clone_alerts' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5">
              <h2 className="font-bold text-white">Clone Detection Alerts <span className="text-gray-600 font-normal ml-2 text-sm">({cloneAlerts.length} total)</span></h2>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead><tr><th>Code</th><th>Product</th><th>Risk Score</th><th>Trigger Reasons</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>
                  {cloneAlerts.map(a => (
                    <tr key={a.id}>
                      <td className="font-mono text-xs text-violet-400">{a.secure_code?.slice(0,25)}…</td>
                      <td>
                        <p className="font-medium text-white text-xs">{a.product_brand_name}</p>
                        <p className="text-gray-600 text-xs">{a.batch_number}</p>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                            <div className={`h-full rounded-full ${a.risk_score >= 80 ? 'bg-red-500' : a.risk_score >= 60 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${a.risk_score}%` }} />
                          </div>
                          <span className={`text-xs font-bold ${a.risk_score >= 80 ? 'text-red-400' : 'text-amber-400'}`}>{a.risk_score}%</span>
                        </div>
                      </td>
                      <td className="max-w-xs">
                        {(a.trigger_reasons || []).map((r, i) => (
                          <p key={i} className="text-xs text-gray-500 truncate">• {r}</p>
                        ))}
                      </td>
                      <td><span className={`px-2 py-0.5 rounded-full text-xs ${a.status === 'PENDING' ? 'badge-clone' : a.status === 'CONFIRMED' ? 'badge-recalled' : 'badge-invalid'}`}>{a.status}</span></td>
                      <td>
                        {a.status === 'PENDING' && (
                          <div className="flex gap-1.5">
                            <button onClick={() => handleResolveAlert(a.id, 'CONFIRMED')} title="Confirm as Clone" className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-colors">
                              <XCircle size={15} />
                            </button>
                            <button onClick={() => handleResolveAlert(a.id, 'DISMISSED')} title="Dismiss Alert" className="p-1.5 rounded-lg hover:bg-emerald-500/20 text-emerald-400 transition-colors">
                              <CheckCircle size={15} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!cloneAlerts.length && <tr><td colSpan={6} className="text-center text-gray-600 py-10">No clone alerts detected.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Heatmap Tab ── */}
        {tab === 'heatmap' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5 flex items-center gap-2">
              <MapIcon size={16} className="text-brand-400" />
              <h2 className="font-bold text-white">Suspicious Reports & Clone Alert Map</h2>
              <div className="ml-auto flex gap-4 text-xs text-gray-500">
                <span><span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1.5" />Reports</span>
                <span><span className="inline-block w-2 h-2 rounded-full bg-violet-400 mr-1.5" />Clone Alerts</span>
              </div>
            </div>
            <div className="p-4">
              <MapContainer center={[-1.286389, 36.817223]} zoom={6} style={{ height: 450, borderRadius: 12 }}>
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                {heatmap.markers?.map(m => (
                  <CircleMarker
                    key={m.id}
                    center={[m.latitude, m.longitude]}
                    radius={m.risk_level === 'CRITICAL' ? 16 : m.risk_level === 'HIGH' ? 12 : 8}
                    color={MARKER_COLORS[m.type] || '#0d91e1'}
                    fillColor={MARKER_COLORS[m.type] || '#0d91e1'}
                    fillOpacity={0.6}
                    weight={2}
                  >
                    <Popup>
                      <div className="text-xs space-y-1">
                        <p className="font-bold">{m.title}</p>
                        <p className="text-gray-500">{m.description?.slice(0, 100)}…</p>
                        <p><strong>Status:</strong> {m.status}</p>
                        <p><strong>Risk:</strong> {m.risk_level}</p>
                        <p className="text-gray-400">{new Date(m.created_at).toLocaleDateString()}</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div>
          </div>
        )}

        {/* ── Pharmacies Tab ── */}
        {tab === 'pharmacies' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5">
              <h2 className="font-bold text-white">Pharmacy Trust Ratings</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead><tr><th>Pharmacy</th><th>County</th><th>License</th><th>Trust Score</th><th>Rating</th></tr></thead>
                <tbody>
                  {pharmacies.map(p => (
                    <tr key={p.id}>
                      <td className="font-medium text-white">{p.name}</td>
                      <td className="text-gray-400 text-xs">{p.county}</td>
                      <td className="font-mono text-xs text-gray-600">{p.license_number}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                            <div className={`h-full rounded-full ${p.trust_score >= 80 ? 'bg-emerald-500' : p.trust_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${p.trust_score}%` }} />
                          </div>
                          <span className="text-xs text-white font-bold">{p.trust_score.toFixed(0)}%</span>
                        </div>
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          p.trust_rating === 'TRUSTED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                          p.trust_rating === 'WATCH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                          'bg-red-500/20 text-red-400 border border-red-500/30'
                        }`}>{p.trust_rating}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Settings Tab ── */}
        {tab === 'model' && (
          <div className="max-w-2xl glass rounded-2xl p-6">
            <h2 className="font-bold text-white mb-2 flex items-center gap-2"><ShieldAlert size={18} className="text-violet-400" /> Clone Detection Model</h2>
            <p className="text-xs text-gray-500 mb-5">The Isolation Forest model augments the existing rule-based detector. Rules continue to operate if no model is trained.</p>
            {model?.available ? (
              <dl className="grid sm:grid-cols-3 gap-4 mb-5">
                <ModelDatum label="Model version" value={model.version} />
                <ModelDatum label="Training date" value={new Date(model.trained_at).toLocaleString()} />
                <ModelDatum label="Training samples" value={model.training_samples} />
              </dl>
            ) : <p className="text-amber-300 text-sm mb-5">No trained model is available. Verification currently uses rules only.</p>}
            <button onClick={handleRetrainModel} disabled={retraining} className="btn-primary disabled:opacity-50">
              <RefreshCw size={14} className={retraining ? 'animate-spin' : ''} />
              {retraining ? 'Training model…' : 'Retrain model'}
            </button>
          </div>
        )}

        {tab === 'settings' && settings && (
          <div className="max-w-lg glass rounded-2xl p-6">
            <h2 className="font-bold text-white mb-1 flex items-center gap-2"><Settings size={18} className="text-brand-400" /> Clone Detection Engine Settings</h2>
            <p className="text-xs text-gray-500 mb-5">Configure thresholds that determine when a code is flagged as a suspected clone.</p>
            <div className="space-y-4">
              {[
                { key: 'max_scan_threshold', label: 'Max Scan Count Threshold', help: 'Scans before flagging high frequency (default: 3)' },
                { key: 'max_velocity_kmh', label: 'Max Velocity (km/h)', help: 'Speed threshold for impossible travel detection (default: 800)' },
                { key: 'distinct_ip_window_minutes', label: 'IP Entropy Window (minutes)', help: 'Time window for distinct IP counting (default: 15)' },
                { key: 'distinct_ip_threshold', label: 'Distinct IP Threshold', help: 'Number of IPs before flagging entropy anomaly (default: 3)' },
              ].map(({ key, label, help }) => (
                <div key={key}>
                  <label className="label">{label}</label>
                  <input className="input" type="number" value={settings[key] || ''} onChange={e => setSettings(s => ({ ...s, [key]: parseFloat(e.target.value) }))} />
                  <p className="text-xs text-gray-600 mt-1">{help}</p>
                </div>
              ))}

              <div className="pt-2 border-t border-white/5">
                <p className="text-xs text-gray-500 font-semibold mb-3 uppercase tracking-wider">Risk Score Weights (must sum to 1.0)</p>
                {[
                  { key: 'weight_frequency', label: 'Frequency Weight (default: 0.35)' },
                  { key: 'weight_velocity', label: 'Velocity Weight (default: 0.45)' },
                  { key: 'weight_entropy', label: 'Entropy Weight (default: 0.20)' },
                ].map(({ key, label }) => (
                  <div key={key} className="mb-3">
                    <label className="label">{label}</label>
                    <input className="input" type="number" step="0.05" min="0" max="1" value={settings[key] || ''} onChange={e => setSettings(s => ({ ...s, [key]: parseFloat(e.target.value) }))} />
                  </div>
                ))}
              </div>

              <div className="pt-2 border-t border-white/5">
                <p className="text-xs text-gray-500 font-semibold mb-3 uppercase tracking-wider">Hybrid model weights (must sum to 1.0)</p>
                {[
                  { key: 'rule_weight', label: 'Rules weight (default: 0.60)' },
                  { key: 'ml_weight', label: 'ML weight (default: 0.40)' },
                  { key: 'ml_threshold', label: 'ML anomaly threshold (0–100)' },
                  { key: 'hybrid_threshold', label: 'Hybrid alert threshold (0–100)' },
                ].map(({ key, label }) => (
                  <div key={key} className="mb-3">
                    <label className="label">{label}</label>
                    <input className="input" type="number" step="0.05" min="0" max={key.includes('threshold') ? 100 : 1}
                      value={settings[key] ?? ''} onChange={e => setSettings(s => ({ ...s, [key]: parseFloat(e.target.value) }))} />
                  </div>
                ))}
              </div>

              <div className="pt-2 border-t border-white/5 space-y-3">
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Feature switches</p>
                {[
                  { key: 'ml_enabled', label: 'Enable ML clone detection' },
                  { key: 'ocr_enabled', label: 'Enable pack OCR' },
                  { key: 'chatbot_enabled', label: 'Enable medicine information chat' },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center justify-between text-sm text-gray-300">
                    {label}
                    <input type="checkbox" checked={Boolean(settings[key])}
                      onChange={e => setSettings(s => ({ ...s, [key]: e.target.checked }))} />
                  </label>
                ))}
              </div>

              <button onClick={handleSaveSettings} className="btn-primary w-full">Save Settings</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ModelDatum({ label, value }) {
  return (
    <div className="rounded-xl bg-white/5 p-3">
      <dt className="text-xs text-gray-500">{label}</dt>
      <dd className="text-sm text-white font-semibold mt-1">{value}</dd>
    </div>
  )
}
