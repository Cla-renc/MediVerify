import { useState, useEffect } from 'react'
import { Package, AlertTriangle, Clock, TrendingDown, RefreshCw, Plus, ShieldAlert } from 'lucide-react'
import { getInventory, getPharmacyAlerts, addStockByCode, getBatches, scanPack } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function PharmacistPage() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState(null)
  const [inventory, setInventory] = useState([])
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(false)
  const [addCode, setAddCode] = useState('')
  const [addQty, setAddQty] = useState(10)
  const [ocrResult, setOcrResult] = useState(null)
  const [ocrConfirmed, setOcrConfirmed] = useState(false)
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrError, setOcrError] = useState(null)
  const [registeredBatches, setRegisteredBatches] = useState([])
  const [adding, setAdding] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type='success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3500) }

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [a, inv] = await Promise.all([getPharmacyAlerts(), getInventory()])
      setAlerts(a.data)
      setInventory(inv.data.results || inv.data)
    } catch { showToast('Failed to load data.', 'error') }
    finally { setLoading(false) }
  }

  const handleAddStock = async () => {
    if (!addCode.trim()) return
    if (ocrResult && !ocrConfirmed) {
      showToast('Confirm or correct the scanned fields before saving.', 'error')
      return
    }
    setAdding(true)
    try {
      const res = await addStockByCode({ secure_code_or_batch: addCode.trim(), quantity: addQty })
      showToast(res.data.message)
      setAddCode('')
      fetchData()
    } catch (e) {
      showToast(e.response?.data?.error || 'Failed to add stock.', 'error')
    } finally { setAdding(false) }
  }

  const handlePackScan = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > 5 * 1024 * 1024) {
      setOcrError('Image must be no larger than 5 MB.')
      return
    }
    const formData = new FormData()
    formData.append('image', file)
    setOcrLoading(true)
    setOcrError(null)
    setOcrConfirmed(false)
    try {
      const [result, batchResponse] = await Promise.all([scanPack(formData), getBatches()])
      setOcrResult(result.data)
      setRegisteredBatches(batchResponse.data.results || batchResponse.data)
    } catch (error) {
      setOcrError(error.response?.data?.error || 'Could not read the pack image.')
    } finally {
      setOcrLoading(false)
    }
  }

  const confirmOcrFields = () => {
    const batchNumber = ocrResult?.batch_number?.value?.trim()
    if (!batchNumber) {
      setOcrError('Enter or correct a batch number before confirming.')
      return
    }
    setAddCode(batchNumber.toUpperCase())
    setOcrConfirmed(true)
    setOcrError(null)
  }

  const matchedBatch = ocrResult?.batch_number?.value
    ? registeredBatches.find(batch => batch.batch_number?.toLowerCase() === ocrResult.batch_number.value.toLowerCase())
    : null

  const summary = alerts?.summary || {}
  const TABS = ['overview', 'inventory', 'add_stock']

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
            <h1 className="text-2xl font-black text-white">Pharmacy Dashboard</h1>
            <p className="text-gray-500 text-sm mt-1">{user?.organization_name || 'Your Pharmacy'}</p>
          </div>
          <button onClick={fetchData} className="btn-secondary text-xs gap-1.5">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {/* Alert banners for critical issues */}
        {summary.recalled_count > 0 && (
          <div className="mb-4 p-4 rounded-xl bg-red-500/15 border border-red-500/40 flex items-center gap-3">
            <ShieldAlert size={20} className="text-red-400 flex-shrink-0" />
            <div>
              <p className="font-bold text-red-300 text-sm">⚠️ Recalled Batches in Stock</p>
              <p className="text-red-400/70 text-xs mt-0.5">{summary.recalled_count} batch(es) in your inventory have been officially recalled. Quarantine and report immediately.</p>
            </div>
          </div>
        )}

        {summary.expired_count > 0 && (
          <div className="mb-4 p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 flex items-center gap-3">
            <AlertTriangle size={20} className="text-amber-400 flex-shrink-0" />
            <p className="text-amber-300 text-sm font-medium">{summary.expired_count} expired batch(es) detected in your inventory. Remove from dispensing immediately.</p>
          </div>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total SKUs', value: summary.total_items || 0, sub: `${summary.total_units || 0} units`, color: 'blue', icon: Package },
            { label: 'Expiring ≤30d', value: summary.expiring_30_days_count || 0, sub: `+${summary.expiring_60_days_count || 0} in 60d`, color: 'amber', icon: Clock },
            { label: 'Recalled', value: summary.recalled_count || 0, sub: 'Quarantine now', color: 'red', icon: ShieldAlert },
            { label: 'Low Stock', value: summary.low_stock_count || 0, sub: '< 10 units', color: 'violet', icon: TrendingDown },
          ].map(({ label, value, sub, color, icon: Icon }) => (
            <div key={label} className={`glass rounded-xl p-4 glass-hover border ${
              value > 0 && (color === 'red' || color === 'amber') ? `border-${color === 'red' ? 'red' : 'amber'}-500/30` : 'border-white/5'
            }`}>
              <div className={`text-xs font-semibold mb-1 ${color === 'blue' ? 'text-brand-400' : color === 'amber' ? 'text-amber-400' : color === 'red' ? 'text-red-400' : 'text-violet-400'}`}>{label}</div>
              <div className="text-3xl font-black text-white">{value}</div>
              <div className="text-xs text-gray-600 mt-0.5">{sub}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 glass rounded-xl p-1 w-fit mb-6">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all ${tab === t ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30' : 'text-gray-500 hover:text-gray-300'}`}>
              {t.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Overview tab */}
        {tab === 'overview' && alerts && (
          <div className="space-y-4">
            {[
              { title: '🚨 Recalled Batches', items: alerts.recalled_alerts, color: 'red', badge: 'badge-recalled' },
              { title: '⏰ Expiring in ≤30 Days', items: alerts.expiring_30_days, color: 'red', badge: 'badge-expired' },
              { title: '⚠️ Expiring in ≤60 Days', items: alerts.expiring_60_days, color: 'amber', badge: 'badge-expired' },
              { title: '⌛ Expiring in ≤90 Days', items: alerts.expiring_90_days, color: 'amber', badge: 'badge-expired' },
              { title: '📦 Low Stock (< 10 units)', items: alerts.low_stock, color: 'violet', badge: 'badge-clone' },
            ].map(({ title, items, badge }) => items?.length > 0 && (
              <div key={title} className="glass rounded-2xl overflow-hidden">
                <div className="px-5 py-4 border-b border-white/5">
                  <h3 className="font-bold text-white text-sm">{title} <span className="text-gray-600">({items.length})</span></h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead><tr><th>Product</th><th>Batch</th><th>Expiry</th><th>Qty</th><th>Status</th></tr></thead>
                    <tbody>
                      {items.map(item => (
                        <tr key={item.id}>
                          <td className="font-medium text-white">{item.batch_details?.product_brand_name}</td>
                          <td className="font-mono text-xs text-brand-400">{item.batch_details?.batch_number}</td>
                          <td className="text-gray-400">{item.batch_details?.expiry_date}</td>
                          <td className="font-bold text-white">{item.quantity}</td>
                          <td><span className={`px-2 py-0.5 rounded-full text-xs ${badge}`}>{item.is_recalled ? 'RECALLED' : item.is_expired ? 'EXPIRED' : 'EXPIRING'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            {!alerts.recalled_alerts?.length && !alerts.expiring_30_days?.length && !alerts.low_stock?.length && (
              <div className="glass rounded-2xl p-10 text-center">
                <div className="text-4xl mb-3">✅</div>
                <p className="text-emerald-400 font-bold">All Clear!</p>
                <p className="text-gray-600 text-sm mt-1">No critical alerts for your pharmacy inventory.</p>
              </div>
            )}
          </div>
        )}

        {/* Inventory tab */}
        {tab === 'inventory' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5">
              <h2 className="font-bold text-white">Full Inventory</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead><tr><th>Product</th><th>Batch</th><th>Expiry</th><th>Qty</th><th>Sell Price (KES)</th><th>Supplier</th></tr></thead>
                <tbody>
                  {inventory.map(item => (
                    <tr key={item.id}>
                      <td className="font-medium text-white">{item.batch_details?.product_brand_name} {item.batch_details?.product_strength}</td>
                      <td className="font-mono text-xs text-brand-400">{item.batch_details?.batch_number}</td>
                      <td className={item.is_expired ? 'text-red-400 font-bold' : 'text-gray-400'}>{item.batch_details?.expiry_date}</td>
                      <td className={`font-bold ${item.quantity < 10 ? 'text-amber-400' : 'text-white'}`}>{item.quantity}</td>
                      <td className="text-gray-400">{parseFloat(item.selling_price).toFixed(2)}</td>
                      <td className="text-gray-600 text-xs">{item.supplier_name || '—'}</td>
                    </tr>
                  ))}
                  {inventory.length === 0 && <tr><td colSpan={6} className="text-center text-gray-600 py-10">No inventory items yet.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Add Stock tab */}
        {tab === 'add_stock' && (
          <div className="max-w-lg glass rounded-2xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center gap-2"><Plus size={18} className="text-brand-400" /> Add Stock by Code</h2>
            <p className="text-xs text-gray-500 mb-5">Scan a unit QR code or enter a batch number to add stock to your pharmacy inventory.</p>
            <div className="space-y-4">
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <label className="btn-secondary relative inline-flex cursor-pointer items-center gap-2">
                  <span>{ocrLoading ? 'Reading pack…' : 'Scan pack with camera'}</span>
                  <input
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    onChange={handlePackScan}
                    disabled={ocrLoading}
                    aria-label="Scan pack with camera or upload image"
                  />
                </label>
                <p className="text-xs text-gray-600 mt-2">Take or upload a clear photo. Maximum image size: 5 MB.</p>
                {ocrError && <p role="alert" className="text-xs text-red-300 mt-2">{ocrError}</p>}
                {ocrResult && (
                  <div className="mt-4 space-y-3">
                    <p className="text-xs text-gray-400">Review and correct every field, then confirm before adding stock.</p>
                    <OCRField
                      label="Batch number"
                      value={ocrResult.batch_number.value || ''}
                      confidence={ocrResult.batch_number.confidence}
                      onChange={value => {
                        setOcrConfirmed(false)
                        setOcrResult(result => ({ ...result, batch_number: { ...result.batch_number, value } }))
                      }}
                    />
                    <OCRField
                      label="Expiry date"
                      type="date"
                      value={ocrResult.expiry_date.value || ''}
                      confidence={ocrResult.expiry_date.confidence}
                      onChange={value => {
                        setOcrConfirmed(false)
                        setOcrResult(result => ({ ...result, expiry_date: { ...result.expiry_date, value } }))
                      }}
                    />
                    <OCRField
                      label="Manufacturing date"
                      type="date"
                      value={ocrResult.manufacturing_date.value || ''}
                      confidence={ocrResult.manufacturing_date.confidence}
                      onChange={value => {
                        setOcrConfirmed(false)
                        setOcrResult(result => ({ ...result, manufacturing_date: { ...result.manufacturing_date, value } }))
                      }}
                    />
                    {matchedBatch ? (
                      <p className="text-xs text-emerald-300">Registry match: {matchedBatch.product_brand_name || matchedBatch.product?.brand_name} · {matchedBatch.batch_number}</p>
                    ) : (
                      <p className="text-xs text-amber-300">Batch not found in registry. Correct the number or enter a registered batch before saving.</p>
                    )}
                    <button type="button" onClick={confirmOcrFields} className="btn-secondary w-full">
                      Confirm scanned values
                    </button>
                    {ocrConfirmed && <p className="text-xs text-emerald-300">Values confirmed. You can now submit the stock entry.</p>}
                  </div>
                )}
              </div>
              <div>
                <label className="label">Batch Number or Unit Code</label>
                <input className="input font-mono" placeholder="BN-2026-001 or MV-SER-0001-XXXX" value={addCode} onChange={e => {
                  setAddCode(e.target.value.toUpperCase())
                  if (ocrResult) setOcrConfirmed(false)
                }} />
              </div>
              <div>
                <label className="label">Quantity</label>
                <input className="input" type="number" min={1} value={addQty} onChange={e => setAddQty(+e.target.value)} />
              </div>
              <button onClick={handleAddStock} disabled={adding || !addCode.trim() || Boolean(ocrResult && !ocrConfirmed)} className="btn-primary w-full disabled:opacity-50">
                {adding ? <><div className="spinner w-4 h-4" /> Adding…</> : <><Plus size={16} /> Add to Inventory</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function OCRField({ label, value, confidence, type = 'text', onChange }) {
  const confidenceColor = confidence >= 0.8 ? 'text-emerald-300' : confidence >= 0.6 ? 'text-amber-300' : 'text-red-300'
  return (
    <label className="block">
      <span className="flex items-center justify-between text-xs text-gray-400 mb-1">
        {label}
        <span className={confidenceColor}>OCR confidence {Math.round(confidence * 100)}%</span>
      </span>
      <input className="input" type={type} value={value} onChange={event => onChange(event.target.value)} />
    </label>
  )
}
