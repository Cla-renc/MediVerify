import { useState } from 'react'
import { MessageSquare, Smartphone, Send, Terminal } from 'lucide-react'
import { simulateUSSD, simulateSMS } from '../services/api'

const USSD_MENU = {
  '': { title: 'MediVerify Kenya', options: [{ key: '1', label: 'Verify Medicine Code' }, { key: '2', label: 'Report Suspicious Product' }, { key: '3', label: 'Badilisha Lugha (Kiswahili)' }] },
  '1': { title: 'Enter medicine code:', type: 'input' },
  '2': { title: 'Enter product & pharmacy name:', type: 'input' },
  '3': { title: 'Select Language / Chagua Lugha', options: [{ key: '1', label: 'English' }, { key: '2', label: 'Swahili' }] },
}

export default function SimulatorPage() {
  const [mode, setMode] = useState('ussd') // 'ussd' | 'sms'
  const [ussdSession, setUssdSession] = useState([])
  const [ussdPath, setUssdPath] = useState([])
  const [ussdInput, setUssdInput] = useState('')
  const [smsInput, setSmsInput] = useState('')
  const [smsList, setSmsList] = useState([])
  const [loading, setLoading] = useState(false)

  const handleUSSDInput = async () => {
    const text = [...ussdPath, ussdInput].filter(Boolean).join('*')
    setUssdSession(prev => [...prev, { type: 'user', text: ussdInput || '(open)' }])
    setLoading(true)
    try {
      const res = await simulateUSSD(text)
      const response = res.data
      const isCON = response.startsWith ? response.startsWith('CON ') : false
      const isEND = response.startsWith ? response.startsWith('END ') : false
      const body = response.replace(/^(CON|END) /, '')
      setUssdSession(prev => [...prev, { type: 'system', text: body, final: isEND }])
      if (!isEND) {
        setUssdPath([...ussdPath, ussdInput].filter(Boolean))
      } else {
        setTimeout(() => { setUssdSession([]); setUssdPath([]) }, 5000)
      }
    } catch (e) {
      setUssdSession(prev => [...prev, { type: 'error', text: 'Service unavailable. Check backend is running.' }])
    } finally {
      setUssdInput('')
      setLoading(false)
    }
  }

  const resetUSSD = () => { setUssdSession([]); setUssdPath([]) }

  const handleSMS = async () => {
    if (!smsInput.trim()) return
    setSmsList(prev => [...prev, { type: 'sent', text: smsInput }])
    setLoading(true)
    try {
      const res = await simulateSMS(smsInput.trim())
      setSmsList(prev => [...prev, { type: 'received', text: res.data.reply_message }])
    } catch {
      setSmsList(prev => [...prev, { type: 'received', text: 'Service unavailable. Check backend is running.' }])
    } finally {
      setSmsInput('')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-dark py-10">
      <div className="max-w-2xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-black text-white mb-2">
            📱 <span className="gradient-text">SMS & USSD</span> Simulator
          </h1>
          <p className="text-gray-500 text-sm">Test Africa's Talking SMS/USSD verification flows locally without a real SIM card or paid account.</p>
        </div>

        {/* Mode switch */}
        <div className="flex gap-1 glass rounded-xl p-1 w-fit mx-auto mb-6">
          {[['ussd', Terminal, 'USSD (*384#)'], ['sms', MessageSquare, 'SMS Shortcode']].map(([m, Icon, label]) => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-5 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${mode === m ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30' : 'text-gray-500 hover:text-gray-300'}`}>
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>

        {/* ── USSD Simulator ── */}
        {mode === 'ussd' && (
          <div className="glass rounded-2xl overflow-hidden">
            {/* Phone UI frame */}
            <div className="bg-gradient-to-b from-gray-900 to-gray-950 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Smartphone size={16} className="text-gray-500" />
                <span className="text-xs text-gray-500 font-mono">*384# — MediVerify Kenya</span>
              </div>
              {/* USSD screen */}
              <div className="bg-black/60 rounded-xl p-4 min-h-[200px] font-mono text-xs space-y-2">
                {ussdSession.length === 0 && (
                  <div className="text-gray-600">
                    <p className="text-green-400 mb-2">{'>'} Dial *384# to start</p>
                    <p>MediVerify USSD Simulator</p>
                    <p>1. Verify Medicine Code</p>
                    <p>2. Report Suspicious Product</p>
                    <p>3. Badilisha Lugha (Kiswahili)</p>
                  </div>
                )}
                {ussdSession.map((s, i) => (
                  <div key={i} className={`${s.type === 'user' ? 'text-cyan-400' : s.type === 'error' ? 'text-red-400' : s.final ? 'text-amber-400' : 'text-green-400'}`}>
                    {s.type === 'user' ? `> ${s.text}` : s.text}
                    {s.final && <span className="text-gray-600 block mt-1 text-xs">(Session ended)</span>}
                  </div>
                ))}
                {loading && <div className="text-gray-600 animate-pulse">Processing…</div>}
              </div>
              {/* Input */}
              <div className="mt-3 flex gap-2">
                <input
                  className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-brand-500/50"
                  placeholder={ussdPath.length === 0 ? "Enter option (1, 2, 3)…" : "Enter code or response…"}
                  value={ussdInput}
                  onChange={e => setUssdInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !loading && handleUSSDInput()}
                />
                <button onClick={handleUSSDInput} disabled={loading} className="btn-primary px-4 py-2 text-xs">
                  {loading ? <div className="spinner w-4 h-4" /> : <Send size={14} />}
                </button>
              </div>
              <div className="flex gap-2 mt-2">
                <button onClick={resetUSSD} className="flex-1 btn-secondary text-xs py-2">Reset Session</button>
                <button onClick={() => { setUssdInput('1'); handleUSSDInput() }} className="flex-1 btn-secondary text-xs py-2">Try: Verify Code</button>
              </div>
            </div>
            {/* Guide */}
            <div className="p-4 bg-white/2 border-t border-white/5">
              <p className="text-xs text-gray-600 font-semibold mb-2 uppercase tracking-wider">How to test:</p>
              <ol className="text-xs text-gray-500 space-y-1 list-decimal list-inside">
                <li>Type <code className="text-brand-400">1</code> and press Send (selects "Verify Medicine Code")</li>
                <li>Enter any valid medicine code from the seed data (e.g. from the CSV export)</li>
                <li>See the live result from the backend engine</li>
              </ol>
            </div>
          </div>
        )}

        {/* ── SMS Simulator ── */}
        {mode === 'sms' && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="bg-gradient-to-b from-gray-900 to-gray-950 p-4">
              <div className="flex items-center gap-2 mb-3">
                <MessageSquare size={16} className="text-gray-500" />
                <span className="text-xs text-gray-500 font-mono">SMS · From: +254700000000</span>
              </div>
              {/* Chat bubbles */}
              <div className="min-h-[220px] space-y-2 mb-3">
                {smsList.length === 0 && (
                  <p className="text-gray-700 text-xs font-mono">Send a medicine code as an SMS (e.g. MV-SER-XXXX-ABCD123) to verify it.</p>
                )}
                {smsList.map((m, i) => (
                  <div key={i} className={`flex ${m.type === 'sent' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs px-3 py-2 rounded-xl text-xs font-mono ${m.type === 'sent' ? 'bg-brand-500/30 text-brand-300 rounded-br-sm' : 'bg-white/5 text-gray-300 rounded-bl-sm'}`}>
                      {m.text}
                    </div>
                  </div>
                ))}
                {loading && <div className="flex justify-start"><div className="bg-white/5 rounded-xl px-3 py-2 text-xs text-gray-600 animate-pulse">MediVerify is typing…</div></div>}
              </div>
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-brand-500/50"
                  placeholder="Type a medicine code…"
                  value={smsInput}
                  onChange={e => setSmsInput(e.target.value.toUpperCase())}
                  onKeyDown={e => e.key === 'Enter' && !loading && handleSMS()}
                />
                <button onClick={handleSMS} disabled={loading || !smsInput.trim()} className="btn-primary px-4 py-2 text-xs disabled:opacity-50">
                  {loading ? <div className="spinner w-4 h-4" /> : <Send size={14} />}
                </button>
              </div>
            </div>
            <div className="p-4 bg-white/2 border-t border-white/5">
              <p className="text-xs text-gray-600 font-semibold mb-2 uppercase tracking-wider">How to test:</p>
              <ol className="text-xs text-gray-500 space-y-1 list-decimal list-inside">
                <li>Copy a medicine code from the CSV export or database</li>
                <li>Paste it in the field above and press Send</li>
                <li>MediVerify replies with GENUINE / EXPIRED / RECALLED / SUSPECTED CLONE / INVALID</li>
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
