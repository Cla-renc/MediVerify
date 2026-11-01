import { createContext, useContext, useState } from 'react'

const LangContext = createContext(null)

export const translations = {
  en: {
    verify: 'Verify Medicine',
    scan: 'Scan QR Code',
    type_code: 'Or type a code',
    enter_code: 'Enter medicine verification code…',
    verify_btn: 'Verify Now',
    result_genuine: 'Genuine Medicine',
    result_expired: 'Expired Medicine',
    result_recalled: 'Recalled Batch',
    result_clone: 'Suspected Clone',
    result_invalid: 'Invalid Code',
    report_suspicious: 'Report Suspicious Medicine',
    language: 'Language',
    product: 'Product',
    batch: 'Batch',
    expiry: 'Expiry Date',
    manufacturer: 'Manufacturer',
    usage: 'How to Use',
    side_effects: 'Side Effects',
    warnings: 'Warnings',
    scan_count: 'Times Scanned',
    risk_score: 'Risk Score',
    do_not_use: 'DO NOT USE THIS MEDICINE',
    safe_to_use: 'THIS MEDICINE IS SAFE TO USE',
    scanning: 'Scanning…',
    camera_denied: 'Camera access denied. Please type the code below.',
    back: 'Back',
    loading: 'Verifying…',
  },
  sw: {
    verify: 'Hakiki Dawa',
    scan: 'Scan Msimbo wa QR',
    type_code: 'Au andika msimbo',
    enter_code: 'Weka nambari ya uthibitisho wa dawa…',
    verify_btn: 'Hakiki Sasa',
    result_genuine: 'Dawa Halisi',
    result_expired: 'Dawa Iliyopitwa na Wakati',
    result_recalled: 'Kundi Lililorejeshwa',
    result_clone: 'Inashukiwa Kuwa Bandia',
    result_invalid: 'Msimbo Batili',
    report_suspicious: 'Ripoti Dawa ya Shaka',
    language: 'Lugha',
    product: 'Bidhaa',
    batch: 'Kundi',
    expiry: 'Tarehe ya Mwisho',
    manufacturer: 'Mtengenezaji',
    usage: 'Jinsi ya Kutumia',
    side_effects: 'Madhara ya Kawaida',
    warnings: 'Tahadhari',
    scan_count: 'Idadi ya Skani',
    risk_score: 'Kiwango cha Hatari',
    do_not_use: 'USITUMIE DAWA HII',
    safe_to_use: 'DAWA HII NI SALAMA KUTUMIA',
    scanning: 'Inasoma…',
    camera_denied: 'Ruhusa ya kamera imekataliwa. Tafadhali andika msimbo hapa chini.',
    back: 'Rudi',
    loading: 'Inathibitisha…',
  },
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('mv_lang') || 'en')

  const toggleLang = () => {
    const next = lang === 'en' ? 'sw' : 'en'
    setLang(next)
    localStorage.setItem('mv_lang', next)
  }

  const t = (key) => translations[lang]?.[key] ?? translations.en[key] ?? key

  return (
    <LangContext.Provider value={{ lang, toggleLang, t }}>
      {children}
    </LangContext.Provider>
  )
}

export const useLang = () => useContext(LangContext)
