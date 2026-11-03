import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import VerificationResult from '../components/VerificationResult'
import { LangProvider } from '../context/LangContext'

// Mock leaflet (not needed in unit tests)
vi.mock('leaflet', () => ({ default: {} }))

const mockGenuineData = {
  result_status: 'GENUINE',
  badge_color: 'green',
  is_genuine: true,
  message_en: 'GENUINE & SAFE: Authenticated product by Cosmos Ltd.',
  message_sw: 'DAWA HALISI NA SALAMA: Imethibitishwa kutoka Cosmos Ltd.',
  product: {
    brand_name: 'Paracetamol Cosmos',
    generic_name: 'Paracetamol',
    strength: '500mg',
    dosage_form: 'Tablet',
    category: 'Analgesic',
    manufacturer: 'Cosmos Limited Kenya',
    manufacturer_country: 'Kenya',
    usage_instructions_en: 'Take 1 to 2 tablets every 4 to 6 hours.',
    usage_instructions_sw: 'Kunywa vidonge 1 au 2 kila masaa 4 hadi 6.',
    side_effects_en: 'Mild nausea.',
    side_effects_sw: 'Kichefuchefu kidogo.',
    key_warnings_en: 'Do not exceed recommended dose.',
    key_warnings_sw: 'Usizidishe kipimo kilichopendekezwa.',
  },
  batch: {
    batch_number: 'BN-PAR-2026-001',
    manufacture_date: '2026-01-01',
    expiry_date: '2027-06-01',
    is_expired: false,
    is_recalled: false,
    recall_reason: null,
  },
  verification_details: {
    scan_id: 'aabbcc-1234',
    scan_count: 1,
    secure_code: 'MV-SER-0001-ABCDEF123456',
    scanned_at: '2026-10-15T10:00:00Z',
    risk_score: 0.0,
    risk_reasons: [],
  },
}

const mockExpiredData = {
  ...mockGenuineData,
  result_status: 'EXPIRED',
  badge_color: 'amber',
  is_genuine: false,
  message_en: 'EXPIRED MEDICINE: Do not use.',
  message_sw: 'DAWA IMEHARIBAKA: Usitumie.',
  batch: { ...mockGenuineData.batch, is_expired: true, expiry_date: '2025-01-01' },
}

const mockCloneData = {
  ...mockGenuineData,
  result_status: 'SUSPECTED_CLONE',
  badge_color: 'purple',
  is_genuine: false,
  message_en: 'SUSPECTED CLONE: This code shows signs of duplication.',
  message_sw: 'INASHUKIWA KUWA BANDIA.',
  verification_details: { ...mockGenuineData.verification_details, risk_score: 95.0, risk_reasons: ['High Frequency: 5 scans (threshold 3)', 'Velocity Anomaly: 5760 km/h'] },
}

const Wrapper = ({ children }) => <LangProvider>{children}</LangProvider>

describe('VerificationResult Component', () => {
  it('renders GENUINE badge and green glow for genuine medicine', () => {
    const onReset = vi.fn()
    render(<Wrapper><VerificationResult data={mockGenuineData} onReset={onReset} /></Wrapper>)
    expect(screen.getByText('GENUINE')).toBeTruthy()
    expect(screen.getByText(/GENUINE & SAFE/)).toBeTruthy()
  })

  it('shows product name and manufacturer', () => {
    render(<Wrapper><VerificationResult data={mockGenuineData} onReset={vi.fn()} /></Wrapper>)
    expect(screen.getByText(/Paracetamol Cosmos/)).toBeTruthy()
    expect(screen.getByText(/Cosmos Limited Kenya/)).toBeTruthy()
  })

  it('renders EXPIRED badge for expired medicine', () => {
    render(<Wrapper><VerificationResult data={mockExpiredData} onReset={vi.fn()} /></Wrapper>)
    expect(screen.getByText('EXPIRED')).toBeTruthy()
    expect(screen.getByText(/EXPIRED MEDICINE/)).toBeTruthy()
  })

  it('renders SUSPECTED_CLONE badge and risk score', () => {
    render(<Wrapper><VerificationResult data={mockCloneData} onReset={vi.fn()} /></Wrapper>)
    expect(screen.getByText('SUSPECTED CLONE')).toBeTruthy()
    expect(screen.getByText('95%')).toBeTruthy()
  })

  it('calls onReset when reset button is clicked', () => {
    const onReset = vi.fn()
    render(<Wrapper><VerificationResult data={mockGenuineData} onReset={onReset} /></Wrapper>)
    screen.getByText(/Verify Another Medicine/).click()
    expect(onReset).toHaveBeenCalledOnce()
  })

  it('displays batch number and expiry date', () => {
    render(<Wrapper><VerificationResult data={mockGenuineData} onReset={vi.fn()} /></Wrapper>)
    expect(screen.getByText('BN-PAR-2026-001')).toBeTruthy()
    expect(screen.getByText('2027-06-01')).toBeTruthy()
  })

  it('shows the medicine chat only for genuine verification and allows a language toggle', () => {
    render(<Wrapper><VerificationResult data={mockGenuineData} onReset={vi.fn()} /></Wrapper>)
    expect(screen.getByText('Ask about this medicine')).toBeTruthy()
    expect(screen.getByText('Download verification receipt')).toBeTruthy()
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Toggle chat language' }))
    })
    expect(screen.getByText('Uliza kuhusu dawa hii')).toBeTruthy()
  })
})
