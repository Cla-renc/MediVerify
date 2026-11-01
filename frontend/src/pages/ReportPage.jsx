import { useState } from 'react'
import { Flag, Camera, MapPin, AlertCircle, CheckCircle } from 'lucide-react'
import { submitReport } from '../services/api'
import { useLang } from '../context/LangContext'

export default function ReportPage() {
  const { lang } = useLang()
  const [form, setForm] = useState({ reporter_name: '', reporter_phone: '', product_name: '', county: 'Nairobi', description: '' })
  const [image, setImage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (image) fd.append('image', image)
      await submitReport(fd)
      setSuccess(true)
    } catch (e) {
      setError('Submission failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const COUNTIES = ['Nairobi','Mombasa','Kisumu','Nakuru','Uasin Gishu','Nyeri','Kiambu','Machakos','Kisii','Meru','Kakamega','Kilifi','Kwale','Migori','Siaya']

  if (success) return (
    <div className="min-h-screen bg-gradient-dark flex items-center justify-center px-4">
      <div className="glass rounded-2xl p-10 text-center max-w-sm animate-slide-up">
        <CheckCircle size={52} className="text-emerald-400 mx-auto mb-4" />
        <h2 className="text-xl font-black text-white mb-2">{lang === 'sw' ? 'Asante!' : 'Report Submitted!'}</h2>
        <p className="text-gray-500 text-sm leading-relaxed mb-6">
          {lang === 'sw'
            ? 'Ripoti yako imepokelewa na Bodi ya Madawa ya PPB Kenya. Utachunguzwa hivi karibuni.'
            : 'Your report has been received by the Pharmacy & Poisons Board Kenya. It will be investigated promptly.'}
        </p>
        <button onClick={() => { setSuccess(false); setForm({ reporter_name:'', reporter_phone:'', product_name:'', county:'Nairobi', description:'' }); setImage(null) }} className="btn-primary w-full">
          {lang === 'sw' ? 'Ripoti Nyingine' : 'Submit Another Report'}
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-dark py-10">
      <div className="max-w-lg mx-auto px-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/20 border border-amber-500/30 mb-4">
            <Flag size={28} className="text-amber-400" />
          </div>
          <h1 className="text-2xl font-black text-white mb-2">
            {lang === 'sw' ? 'Ripoti Dawa ya Shaka' : 'Report Suspicious Medicine'}
          </h1>
          <p className="text-gray-500 text-sm">
            {lang === 'sw'
              ? 'Toa taarifa kwa siri au kwa jina lako. Taarifa zote zinapelekwa moja kwa moja kwa PPB Kenya.'
              : 'Report anonymously or with your details. All reports go directly to the PPB Kenya.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">{lang === 'sw' ? 'Jina lako (si lazima)' : 'Your Name (optional)'}</label>
              <input className="input" placeholder="Anonymous" value={form.reporter_name} onChange={set('reporter_name')} />
            </div>
            <div>
              <label className="label">{lang === 'sw' ? 'Nambari ya Simu' : 'Phone (optional)'}</label>
              <input className="input" placeholder="+254…" value={form.reporter_phone} onChange={set('reporter_phone')} />
            </div>
          </div>

          <div>
            <label className="label">{lang === 'sw' ? 'Jina la Dawa *' : 'Medicine Name *'}</label>
            <input className="input" placeholder="e.g. Paracetamol 500mg" value={form.product_name} onChange={set('product_name')} required />
          </div>

          <div>
            <label className="label">{lang === 'sw' ? 'Kaunti' : 'County'}</label>
            <select className="input" value={form.county} onChange={set('county')}>
              {COUNTIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>

          <div>
            <label className="label">{lang === 'sw' ? 'Eleza Tatizo *' : 'Describe the Issue *'}</label>
            <textarea
              className="input h-28 resize-none"
              placeholder={lang === 'sw'
                ? 'Eleza tatizo, mfano: rangi ya dawa, hali ya ufungaji, dalili baada ya kutumia…'
                : 'Describe what seems wrong, e.g. unusual packaging color, spelling errors, strange taste or side effects…'}
              value={form.description}
              onChange={set('description')}
              required
            />
          </div>

          <div>
            <label className="label">{lang === 'sw' ? 'Picha (si lazima, max 5MB)' : 'Photo (optional, max 5MB)'}</label>
            <div className="relative">
              <input
                type="file"
                accept="image/*"
                className="hidden"
                id="photo-upload"
                onChange={e => setImage(e.target.files[0])}
              />
              <label htmlFor="photo-upload" className="flex items-center gap-2 cursor-pointer input hover:border-brand-500/50 transition-colors">
                <Camera size={16} className="text-gray-500" />
                <span className="text-gray-500">{image ? image.name : (lang === 'sw' ? 'Chagua picha…' : 'Choose photo…')}</span>
              </label>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button type="submit" disabled={loading || !form.product_name || !form.description} className="btn-primary w-full disabled:opacity-50">
            {loading
              ? <><div className="spinner w-4 h-4" /> {lang === 'sw' ? 'Inatuma…' : 'Submitting…'}</>
              : <><Flag size={16} /> {lang === 'sw' ? 'Tuma Ripoti' : 'Submit Report'}</>}
          </button>
        </form>
      </div>
    </div>
  )
}
