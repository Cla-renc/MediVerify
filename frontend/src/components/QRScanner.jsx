import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { Camera, CameraOff } from 'lucide-react'
import { useLang } from '../context/LangContext'

export default function QRScanner({ onScan }) {
  const [active, setActive] = useState(false)
  const [error, setError] = useState(null)
  const scannerRef = useRef(null)
  const { t } = useLang()

  useEffect(() => {
    return () => { stopScanner() }
  }, [])

  const startScanner = async () => {
    setError(null)
    try {
      const scanner = new Html5Qrcode('qr-reader')
      scannerRef.current = scanner
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          onScan(decodedText)
          stopScanner()
        },
        () => {}
      )
      setActive(true)
    } catch (err) {
      setError(t('camera_denied'))
      setActive(false)
    }
  }

  const stopScanner = async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop()
        await scannerRef.current.clear()
      } catch (_) {}
      scannerRef.current = null
    }
    setActive(false)
  }

  return (
    <div className="space-y-3">
      {/* Camera preview area */}
      <div className="scanner-container bg-black/40 min-h-[280px] flex items-center justify-center relative rounded-2xl overflow-hidden border border-white/10">
        <div id="qr-reader" className="w-full" />

        {active && (
          <>
            <div className="scanner-frame" />
            <div className="scanner-corner tl" />
            <div className="scanner-corner tr" />
            <div className="scanner-corner bl" />
            <div className="scanner-corner br" />
            <div className="scan-line" style={{ top: '50%' }} />
          </>
        )}

        {!active && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-500">
            <Camera size={40} className="opacity-30" />
            <p className="text-xs">{t('scan')}</p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <button
        onClick={active ? stopScanner : startScanner}
        className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
          active
            ? 'bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30'
            : 'btn-primary'
        }`}
      >
        {active ? (
          <><CameraOff size={17} /> Stop Camera</>
        ) : (
          <><Camera size={17} /> {t('scan')}</>
        )}
      </button>
    </div>
  )
}
