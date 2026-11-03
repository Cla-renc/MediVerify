import { CheckCircle, XCircle, AlertTriangle, Skull, HelpCircle, ChevronDown, ChevronUp, MessageCircle, Send, Globe, Download } from 'lucide-react'
import { useState } from 'react'
import { useLang } from '../context/LangContext'
import { askMedicineQuestion, getVerificationReceipt } from '../services/api'

const STATUS_CONFIG = {
  GENUINE:        { icon: CheckCircle,    color: 'green',  cls: 'badge-genuine',  border: 'border-emerald-500/40',  glow: 'glow-green',  bg: 'from-emerald-950/60 to-emerald-900/20' },
  EXPIRED:        { icon: AlertTriangle,  color: 'amber',  cls: 'badge-expired',  border: 'border-amber-500/40',   glow: 'glow-amber',  bg: 'from-amber-950/60 to-amber-900/20' },
  RECALLED:       { icon: XCircle,        color: 'red',    cls: 'badge-recalled', border: 'border-red-500/40',     glow: 'glow-red',    bg: 'from-red-950/60 to-red-900/20' },
  SUSPECTED_CLONE:{ icon: Skull,          color: 'purple', cls: 'badge-clone',    border: 'border-violet-500/40',  glow: 'glow-purple', bg: 'from-violet-950/60 to-violet-900/20' },
  INVALID:        { icon: HelpCircle,     color: 'gray',   cls: 'badge-invalid',  border: 'border-gray-500/40',    glow: '',            bg: 'from-gray-950/60 to-gray-900/20' },
}

const ICON_COLORS = {
  green: 'text-emerald-400', amber: 'text-amber-400',
  red: 'text-red-400', purple: 'text-violet-400', gray: 'text-gray-400',
}

export default function VerificationResult({ data, onReset }) {
  const { lang, t } = useLang()
  const [expanded, setExpanded] = useState(false)
  const [chatLang, setChatLang] = useState(lang)
  const [chatQuestion, setChatQuestion] = useState('')
  const [medicineSearch, setMedicineSearch] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [receiptLoading, setReceiptLoading] = useState(false)
  const [receiptError, setReceiptError] = useState('')
  if (!data) return null

  const status = data.result_status
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.INVALID
  const Icon = cfg.icon
  const product = data.product
  const batch = data.batch
  const details = data.verification_details

  const message = lang === 'sw' ? data.message_sw : data.message_en
  const suggestions = chatLang === 'sw'
    ? ['Dawa hii hutumika kwa nini?', 'Madhara ya kawaida ni yapi?', 'Nihifadhi dawa hii vipi?']
    : ['What is it used for?', 'What are common side effects?', 'How should I store it?']

  const sendQuestion = async (question = chatQuestion) => {
    const text = question.trim()
    if (!text || chatLoading) return
    setChatMessages(messages => [...messages, { role: 'user', text }])
    setChatQuestion('')
    setChatLoading(true)
    try {
      const response = await askMedicineQuestion({
        code: details?.secure_code,
        question: text,
        language: chatLang,
        ...(medicineSearch.trim() ? { medicine: medicineSearch.trim() } : {}),
      })
      setChatMessages(messages => [...messages, { role: 'assistant', text: response.data.answer }])
    } catch (error) {
      const message = error.response?.data?.error || (chatLang === 'sw'
        ? 'Huduma haipatikani kwa sasa. Tafadhali jaribu tena.'
        : 'The information service is unavailable. Please try again.')
      setChatMessages(messages => [...messages, { role: 'assistant', text: message }])
    } finally {
      setChatLoading(false)
    }
  }

  const downloadReceipt = async () => {
    const scanId = data.verification_details?.scan_id
    if (!scanId || receiptLoading) return
    setReceiptLoading(true)
    setReceiptError('')
    try {
      const response = await getVerificationReceipt(scanId)
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `mediverify-receipt-${scanId}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setReceiptError(lang === 'sw' ? 'Risiti haikuweza kupakuliwa.' : 'Could not download the verification receipt.')
    } finally {
      setReceiptLoading(false)
    }
  }

  return (
    <div className={`glass border ${cfg.border} ${cfg.glow} bg-gradient-to-b ${cfg.bg} rounded-2xl overflow-hidden animate-slide-up`}>
      {/* Header */}
      <div className="p-6 flex items-start gap-4">
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 ${
          status === 'GENUINE' ? 'bg-emerald-500/20' :
          status === 'EXPIRED' ? 'bg-amber-500/20' :
          status === 'RECALLED' ? 'bg-red-500/20' :
          status === 'SUSPECTED_CLONE' ? 'bg-violet-500/20' : 'bg-gray-500/20'
        }`}>
          <Icon size={28} className={ICON_COLORS[cfg.color]} />
        </div>
        <div className="flex-1 min-w-0">
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold tracking-wider mb-2 ${cfg.cls}`}>
            {status.replace('_', ' ')}
          </span>
          <p className="text-sm text-gray-300 leading-relaxed">{message}</p>
        </div>
      </div>

      {/* Product info (if found) */}
      {product && (
        <div className="px-6 pb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <InfoTile label={t('product')} value={`${product.brand_name} ${product.strength}`} />
            <InfoTile label={t('manufacturer')} value={product.manufacturer} />
            <InfoTile label={t('batch')} value={batch.batch_number} />
            <InfoTile label={t('expiry')} value={batch.expiry_date} highlight={batch.is_expired ? 'red' : null} />
          </div>

          {/* Medicine info expandable */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between py-2.5 px-3 rounded-xl bg-white/5 hover:bg-white/8 transition-colors text-sm text-gray-400"
          >
            <span className="font-medium">{lang === 'sw' ? 'Maelezo ya Dawa' : 'Medicine Information'}</span>
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {expanded && (
            <div className="space-y-3 animate-fade-in">
              <MedInfoSection
                title={t('usage')}
                text={lang === 'sw' ? product.usage_instructions_sw : product.usage_instructions_en}
                color="blue"
              />
              <MedInfoSection
                title={t('side_effects')}
                text={lang === 'sw' ? product.side_effects_sw : product.side_effects_en}
                color="amber"
              />
              <MedInfoSection
                title={t('warnings')}
                text={lang === 'sw' ? product.key_warnings_sw : product.key_warnings_en}
                color="red"
              />
            </div>
          )}

          {/* Risk / Clone info */}
          {details?.risk_score > 0 && (
            <div className="rounded-xl bg-violet-500/10 border border-violet-500/20 p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-violet-400 font-semibold">{t('risk_score')}</span>
                <span className="text-lg font-black text-violet-300">{details.risk_score}%</span>
              </div>
              {details.risk_reasons?.map((r, i) => (
                <p key={i} className="text-xs text-violet-300/70">• {r}</p>
              ))}
            </div>
          )}

          {data.is_genuine && (
            <section className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                  <MessageCircle size={16} className="text-brand-300" />
                  {chatLang === 'sw' ? 'Uliza kuhusu dawa hii' : 'Ask about this medicine'}
                </h3>
                <button
                  type="button"
                  onClick={() => setChatLang(value => value === 'en' ? 'sw' : 'en')}
                  className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-white"
                  aria-label="Toggle chat language"
                >
                  <Globe size={13} /> {chatLang === 'en' ? 'Kiswahili' : 'English'}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {suggestions.map(question => (
                  <button key={question} type="button" onClick={() => sendQuestion(question)}
                    className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-gray-300 hover:border-brand-500/40">
                    {question}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500">
                {chatLang === 'sw'
                  ? 'Majibu hutegemea rekodi za dawa zilizosajiliwa; ufunguo wa AI ya nje si lazima.'
                  : 'Answers use registered medicine records; an external AI key is optional.'}
              </p>
              <label className="block text-xs text-gray-500">
                {chatLang === 'sw' ? 'Dawa nyingine (hiari)' : 'Ask about another medicine (optional)'}
                <input className="input mt-1" value={medicineSearch} maxLength={100}
                  placeholder={chatLang === 'sw' ? 'Jina la dawa' : 'Medicine name'}
                  onChange={event => setMedicineSearch(event.target.value)} />
              </label>
              {chatMessages.length > 0 && (
                <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg bg-black/10 p-2" aria-live="polite">
                  {chatMessages.map((entry, index) => (
                    <p key={`${entry.role}-${index}`} className={`rounded-lg p-2 text-xs leading-relaxed ${
                      entry.role === 'user' ? 'ml-6 bg-brand-500/10 text-brand-100' : 'mr-3 bg-white/5 text-gray-300'
                    }`}>{entry.text}</p>
                  ))}
                </div>
              )}
              <form className="flex gap-2" onSubmit={event => { event.preventDefault(); sendQuestion() }}>
                <input className="input min-w-0 flex-1" value={chatQuestion} maxLength={1000}
                  placeholder={chatLang === 'sw' ? 'Andika swali lako…' : 'Ask a question…'}
                  onChange={event => setChatQuestion(event.target.value)} />
                <button type="submit" className="btn-primary px-3" disabled={chatLoading || !chatQuestion.trim()}
                  aria-label={chatLang === 'sw' ? 'Tuma swali' : 'Send question'}>
                  <Send size={15} />
                </button>
              </form>
              {chatLoading && <p className="text-xs text-gray-500">{chatLang === 'sw' ? 'Inatafuta taarifa…' : 'Checking medicine information…'}</p>}
            </section>
          )}

          {/* Scan meta */}
          <div className="flex items-center justify-between text-xs text-gray-600 border-t border-white/5 pt-3">
            <span>Scan #{details?.scan_id?.slice(0,8)}</span>
            <span>{t('scan_count')}: {details?.scan_count}</span>
            <span>{details?.scanned_at ? new Date(details.scanned_at).toLocaleString() : ''}</span>
          </div>
        </div>
      )}

      {/* Reset button */}
      <div className="px-6 pb-5">
        {data.verification_details?.scan_id && (
          <div className="mb-3">
            <button type="button" onClick={downloadReceipt} disabled={receiptLoading} className="btn-secondary w-full">
              <Download size={15} />
              {receiptLoading
                ? (lang === 'sw' ? 'Inapakua…' : 'Downloading…')
                : (lang === 'sw' ? 'Pakua risiti ya uthibitisho' : 'Download verification receipt')}
            </button>
            {receiptError && <p role="alert" className="mt-2 text-center text-xs text-red-300">{receiptError}</p>}
          </div>
        )}
        <button onClick={onReset} className="btn-secondary w-full">
          {lang === 'sw' ? 'Hakiki Dawa Nyingine' : 'Verify Another Medicine'}
        </button>
      </div>
    </div>
  )
}

function InfoTile({ label, value, highlight }) {
  return (
    <div className="bg-white/5 rounded-xl px-3 py-2.5">
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={`text-sm font-semibold ${highlight === 'red' ? 'text-red-400' : 'text-white'}`}>{value}</p>
    </div>
  )
}

function MedInfoSection({ title, text, color }) {
  const colorMap = {
    blue: 'border-brand-500/30 bg-brand-500/5 text-brand-300',
    amber: 'border-amber-500/30 bg-amber-500/5 text-amber-300',
    red: 'border-red-500/30 bg-red-500/5 text-red-300',
  }
  return (
    <div className={`rounded-xl border p-3 ${colorMap[color]}`}>
      <p className="text-xs font-bold mb-1 uppercase tracking-wider opacity-70">{title}</p>
      <p className="text-xs leading-relaxed opacity-90">{text}</p>
    </div>
  )
}
