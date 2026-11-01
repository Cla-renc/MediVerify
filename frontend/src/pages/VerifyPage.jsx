import { useState } from 'react'
import { ShieldCheck, Search, AlertCircle } from 'lucide-react'
import QRScanner from '../components/QRScanner'
import VerificationResult from '../components/VerificationResult'
import { verifyCode } from '../services/api'
import { useLang } from '../context/LangContext'

export default function VerifyPage() {
  const [code, setCode] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { t, lang, toggleLang } = useLang()

  const handleVerify = async (inputCode) => {
    const c = (inputCode || code).trim()
    if (!c) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const geo = await getGeo()
      const res = await verifyCode({
        code: c,
        channel: inputCode ? 'WEB_QR' : 'WEB_MANUAL',
        latitude: geo?.lat,
        longitude: geo?.lon,
      })
      setResult(res.data)
    } catch (err) {
      setError('Verification service unavailable. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const getGeo = () => new Promise(resolve => {
    if (!navigator.geolocation) return resolve(null)
    navigator.geolocation.getCurrentPosition(
      p => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => resolve(null),
      { timeout: 3000 }
    )
  })

  const reset = () => { setResult(null); setCode(''); setError(null) }

  return (
    <div className="min-h-[calc(100dvh-64px)] bg-gradient-dark">
      {/* Hero */}
      <div className="relative overflow-hidden">
        {/* Ambient glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-3xl" />
          <div className="absolute top-20 right-0 w-80 h-80 bg-violet-600/8 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-xl mx-auto px-4 pt-12 pb-6 text-center">
          {/* Shield icon */}
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-violet-600 mb-6 shadow-2xl glow-blue mx-auto">
            <ShieldCheck size={40} className="text-white" />
          </div>

          <h1 className="text-3xl md:text-4xl font-black text-white mb-3 leading-tight">
            {lang === 'sw' ? (
              <><span className="gradient-text">Hakiki</span> Dawa Yako</>
            ) : (
              <>Verify Your <span className="gradient-text">Medicine</span> is Safe</>
            )}
          </h1>
          <p className="text-gray-400 text-sm md:text-base mb-2 leading-relaxed">
            {lang === 'sw'
              ? 'Scan msimbo wa QR au weka nambari ili ujue kama dawa yako ni halisi, haijapitwa na wakati, na ni salama.'
              : 'Scan a QR code or enter the serial number to instantly check if your medicine is genuine, in-date, and safe to use.'}
          </p>

          {/* Language toggle pill */}
          <button
            onClick={toggleLang}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold border border-white/10 text-gray-400 hover:text-white hover:border-brand-500/40 transition-all mb-8"
          >
            🌐 {lang === 'en' ? 'Badilisha hadi Kiswahili' : 'Switch to English'}
          </button>
        </div>
      </div>

      {/* Main verification panel */}
      <div className="max-w-xl mx-auto px-4 pb-16">
        {result ? (
          <VerificationResult data={result} onReset={reset} />
        ) : (
          <div className="glass rounded-2xl p-6 space-y-5">
            {/* QR Scanner */}
            <QRScanner onScan={(c) => handleVerify(c)} />

            {/* Divider */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-xs text-gray-600 font-medium">{t('type_code')}</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            {/* Manual code entry */}
            <div className="space-y-3">
              <input
                id="medicine-code-input"
                type="text"
                className="input font-mono text-sm tracking-wider"
                placeholder={t('enter_code')}
                value={code}
                onChange={e => setCode(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === 'Enter' && handleVerify()}
              />
              {error && (
                <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                  <AlertCircle size={14} /> {error}
                </div>
              )}
              <button
                id="verify-submit-btn"
                onClick={() => handleVerify()}
                disabled={loading || !code.trim()}
                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <><div className="spinner w-4 h-4" />{t('loading')}</>
                ) : (
                  <><Search size={16} />{t('verify_btn')}</>
                )}
              </button>
            </div>

            {/* Trust indicators */}
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/5">
              {[
                ['🔐', lang === 'sw' ? 'Usalama wa Hali ya Juu' : 'HMAC Secured'],
                ['⚡', lang === 'sw' ? 'Matokeo ya Papo Hapo' : 'Instant Results'],
                ['🇰🇪', lang === 'sw' ? 'Imesajiliwa PPB' : 'PPB Registered'],
              ].map(([icon, label]) => (
                <div key={label} className="text-center py-2 px-1 rounded-xl bg-white/3 border border-white/5">
                  <span className="text-lg">{icon}</span>
                  <p className="text-xs text-gray-600 mt-1 leading-tight">{label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Report link */}
        {!result && (
          <p className="text-center text-xs text-gray-600 mt-4">
            {lang === 'sw' ? 'Una shaka kuhusu dawa?' : 'Suspicious about a medicine?'}{' '}
            <a href="/report" className="text-brand-400 hover:underline font-medium">
              {t('report_suspicious')}
            </a>
          </p>
        )}
      </div>
    </div>
  )
}
