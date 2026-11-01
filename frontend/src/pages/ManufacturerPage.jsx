import { useState, useEffect } from 'react'
import { Package, Plus, QrCode, Download, FileText, AlertTriangle, RefreshCw } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  getProducts, createProduct, getBatches, createBatch,
  generateCodes, exportPDF, exportCSV, recallBatch, getManufacturers
} from '../services/api'

export default function ManufacturerPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState('batches')
  const [products, setProducts] = useState([])
  const [batches, setBatches] = useState([])
  const [manufacturers, setManufacturers] = useState([])
  const [loading, setLoading] = useState(false)
  const [showAddProduct, setShowAddProduct] = useState(false)
  const [showAddBatch, setShowAddBatch] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [p, b, m] = await Promise.all([getProducts(), getBatches(), getManufacturers()])
      setProducts(p.data.results || p.data)
      setBatches(b.data.results || b.data)
      setManufacturers(m.data.results || m.data)
    } catch (e) {
      showToast('Failed to load data.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleExportPDF = async (batch) => {
    try {
      const res = await exportPDF(batch.id)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url; a.download = `QR_${batch.batch_number}.pdf`; a.click()
      showToast(`PDF downloaded for batch ${batch.batch_number}`)
    } catch { showToast('PDF export failed.', 'error') }
  }

  const handleExportCSV = async (batch) => {
    try {
      const res = await exportCSV(batch.id)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
      const a = document.createElement('a')
      a.href = url; a.download = `Codes_${batch.batch_number}.csv`; a.click()
      showToast(`CSV downloaded for batch ${batch.batch_number}`)
    } catch { showToast('CSV export failed.', 'error') }
  }

  const handleGenerateCodes = async (batch) => {
    try {
      await generateCodes(batch.id, batch.total_quantity)
      showToast(`Generated ${batch.total_quantity} HMAC codes for ${batch.batch_number}`)
    } catch { showToast('Code generation failed.', 'error') }
  }

  const handleRecall = async (batch) => {
    const reason = prompt(`Enter recall reason for batch ${batch.batch_number}:`)
    if (!reason) return
    try {
      await recallBatch(batch.id, reason)
      showToast(`Batch ${batch.batch_number} recalled.`, 'warning')
      fetchData()
    } catch { showToast('Recall failed.', 'error') }
  }

  const getBatchStatusBadge = (batch) => {
    if (batch.is_recalled) return <span className="badge-recalled px-2 py-0.5 rounded-full text-xs">Recalled</span>
    if (batch.is_expired) return <span className="badge-expired px-2 py-0.5 rounded-full text-xs">Expired</span>
    const days = Math.ceil((new Date(batch.expiry_date) - new Date()) / 86400000)
    if (days <= 30) return <span className="badge-expired px-2 py-0.5 rounded-full text-xs">Exp in {days}d</span>
    return <span className="badge-genuine px-2 py-0.5 rounded-full text-xs">Valid</span>
  }

  const TABS = ['batches', 'products']

  return (
    <div className="min-h-screen bg-gradient-dark">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl text-sm font-medium shadow-xl animate-slide-up ${
          toast.type === 'error' ? 'bg-red-500/20 border border-red-500/40 text-red-300' :
          toast.type === 'warning' ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300' :
          'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300'
        }`}>
          {toast.msg}
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-white">Manufacturer Portal</h1>
            <p className="text-gray-500 text-sm mt-1">Welcome, <span className="text-brand-400">{user?.username}</span> · {user?.organization_name}</p>
          </div>
          <button onClick={fetchData} className="btn-secondary text-xs gap-1.5">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Products', value: products.length, icon: Package, color: 'blue' },
            { label: 'Total Batches', value: batches.length, icon: Package, color: 'violet' },
            { label: 'Recalled', value: batches.filter(b => b.is_recalled).length, icon: AlertTriangle, color: 'red' },
            { label: 'Expiring ≤30d', value: batches.filter(b => !b.is_recalled && !b.is_expired && Math.ceil((new Date(b.expiry_date) - new Date()) / 86400000) <= 30).length, icon: AlertTriangle, color: 'amber' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="glass rounded-xl p-4 glass-hover">
              <div className={`text-xs font-semibold mb-1 ${color === 'blue' ? 'text-brand-400' : color === 'violet' ? 'text-violet-400' : color === 'red' ? 'text-red-400' : 'text-amber-400'}`}>{label}</div>
              <div className="text-3xl font-black text-white">{value}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 glass rounded-xl p-1 w-fit mb-6">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all ${tab === t ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30' : 'text-gray-500 hover:text-gray-300'}`}>
              {t}
            </button>
          ))}
        </div>

        {/* Batches Tab */}
        {tab === 'batches' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
              <h2 className="font-bold text-white">Registered Batches</h2>
              <button onClick={() => setShowAddBatch(true)} className="btn-primary text-xs py-2">
                <Plus size={14} /> New Batch
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Batch #</th>
                    <th>Product</th>
                    <th>Manufacturer</th>
                    <th>Expiry</th>
                    <th>Qty</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map(batch => (
                    <tr key={batch.id}>
                      <td className="font-mono text-xs text-brand-400">{batch.batch_number}</td>
                      <td className="font-medium text-white">{batch.product_brand_name || '—'} {batch.product_strength}</td>
                      <td className="text-gray-500 text-xs">{batch.manufacturer_name || '—'}</td>
                      <td className={batch.is_expired ? 'text-red-400' : 'text-gray-400'}>{batch.expiry_date}</td>
                      <td className="text-gray-400">{batch.total_quantity}</td>
                      <td>{getBatchStatusBadge(batch)}</td>
                      <td>
                        <div className="flex gap-1">
                          <button title="Generate HMAC Codes" onClick={() => handleGenerateCodes(batch)} className="p-1.5 rounded-lg hover:bg-brand-500/20 text-brand-400 transition-colors">
                            <QrCode size={14} />
                          </button>
                          <button title="Download QR PDF" onClick={() => handleExportPDF(batch)} className="p-1.5 rounded-lg hover:bg-emerald-500/20 text-emerald-400 transition-colors">
                            <Download size={14} />
                          </button>
                          <button title="Download CSV" onClick={() => handleExportCSV(batch)} className="p-1.5 rounded-lg hover:bg-violet-500/20 text-violet-400 transition-colors">
                            <FileText size={14} />
                          </button>
                          {!batch.is_recalled && (
                            <button title="Issue Recall" onClick={() => handleRecall(batch)} className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-colors">
                              <AlertTriangle size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {batches.length === 0 && (
                    <tr><td colSpan={7} className="text-center text-gray-600 py-10">No batches registered yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Products Tab */}
        {tab === 'products' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
              <h2 className="font-bold text-white">Registered Products</h2>
              <button onClick={() => setShowAddProduct(true)} className="btn-primary text-xs py-2">
                <Plus size={14} /> New Product
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr><th>Brand Name</th><th>Generic Name</th><th>Form</th><th>Strength</th><th>Category</th></tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id}>
                      <td className="font-semibold text-white">{p.brand_name}</td>
                      <td className="text-gray-400">{p.generic_name}</td>
                      <td><span className="px-2 py-0.5 rounded-full text-xs bg-white/5 text-gray-400">{p.dosage_form}</span></td>
                      <td className="font-mono text-xs text-brand-400">{p.strength}</td>
                      <td className="text-gray-500 text-xs">{p.category}</td>
                    </tr>
                  ))}
                  {products.length === 0 && (
                    <tr><td colSpan={5} className="text-center text-gray-600 py-10">No products registered yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Add Batch Modal */}
        {showAddBatch && <AddBatchModal products={products} manufacturers={manufacturers} onClose={() => setShowAddBatch(false)} onSave={async (data) => { await createBatch(data); setShowAddBatch(false); fetchData(); showToast('Batch created!') }} />}
        {showAddProduct && <AddProductModal manufacturers={manufacturers} onClose={() => setShowAddProduct(false)} onSave={async (data) => { await createProduct(data); setShowAddProduct(false); fetchData(); showToast('Product registered!') }} />}
      </div>
    </div>
  )
}

function AddBatchModal({ products, onClose, onSave }) {
  const [form, setForm] = useState({ product: '', batch_number: '', manufacture_date: '', expiry_date: '', total_quantity: 100 })
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))
  return (
    <Modal title="Register New Batch" onClose={onClose}>
      <div className="space-y-3">
        <div><label className="label">Product</label>
          <select className="input" value={form.product} onChange={set('product')}>
            <option value="">Select product…</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.brand_name} {p.strength}</option>)}
          </select>
        </div>
        <div><label className="label">Batch Number</label><input className="input font-mono" placeholder="BN-2026-001" value={form.batch_number} onChange={set('batch_number')} /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Manufacture Date</label><input className="input" type="date" value={form.manufacture_date} onChange={set('manufacture_date')} /></div>
          <div><label className="label">Expiry Date</label><input className="input" type="date" value={form.expiry_date} onChange={set('expiry_date')} /></div>
        </div>
        <div><label className="label">Total Quantity</label><input className="input" type="number" value={form.total_quantity} onChange={set('total_quantity')} /></div>
        <button className="btn-primary w-full" onClick={() => onSave(form)}>Create Batch & Generate Codes</button>
      </div>
    </Modal>
  )
}

function AddProductModal({ manufacturers, onClose, onSave }) {
  const [form, setForm] = useState({ manufacturer: '', brand_name: '', generic_name: '', dosage_form: 'Tablet', strength: '', category: 'Analgesic', usage_instructions_en: '', usage_instructions_sw: '', side_effects_en: '', side_effects_sw: '', key_warnings_en: '', key_warnings_sw: '' })
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))
  return (
    <Modal title="Register New Product" onClose={onClose}>
      <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
        <div><label className="label">Manufacturer</label>
          <select className="input" value={form.manufacturer} onChange={set('manufacturer')}>
            <option value="">Select manufacturer…</option>
            {manufacturers.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Brand Name</label><input className="input" placeholder="Paracetamol Cosmos" value={form.brand_name} onChange={set('brand_name')} /></div>
          <div><label className="label">Generic Name</label><input className="input" placeholder="Paracetamol" value={form.generic_name} onChange={set('generic_name')} /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Dosage Form</label>
            <select className="input" value={form.dosage_form} onChange={set('dosage_form')}>
              {['Tablet','Capsule','Syrup','Injection','Ointment','Inhaler','Eye Drops'].map(f => <option key={f}>{f}</option>)}
            </select>
          </div>
          <div><label className="label">Strength</label><input className="input" placeholder="500mg" value={form.strength} onChange={set('strength')} /></div>
        </div>
        {[['usage_instructions_en','Usage Instructions (English)'],['usage_instructions_sw','Maelezo ya Matumizi (Kiswahili)'],['side_effects_en','Side Effects (English)'],['side_effects_sw','Madhara (Kiswahili)'],['key_warnings_en','Key Warnings (English)'],['key_warnings_sw','Tahadhari (Kiswahili)']].map(([k,label]) => (
          <div key={k}><label className="label">{label}</label><textarea className="input h-16 resize-none" value={form[k]} onChange={set(k)} /></div>
        ))}
        <button className="btn-primary w-full" onClick={() => onSave(form)}>Register Product</button>
      </div>
    </Modal>
  )
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="glass rounded-2xl w-full max-w-lg animate-slide-up">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <h3 className="font-bold text-white">{title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
