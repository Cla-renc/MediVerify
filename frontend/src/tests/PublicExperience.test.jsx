import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import RegisterPage from '../pages/RegisterPage'
import PublicStatsPage from '../pages/PublicStatsPage'
import { getPublicStatistics, register } from '../services/api'

vi.mock('../services/api', () => ({
  getPublicStatistics: vi.fn(),
  register: vi.fn(),
}))

describe('public registration and statistics', () => {
  beforeEach(() => vi.clearAllMocks())

  it('submits professional signup details and explains that activation is pending', async () => {
    register.mockResolvedValue({ data: { pending_approval: true } })
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Account type'), { target: { value: 'PHARMACIST' } })
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'new_pharmacist' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'pharmacist@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'a-private-password' } })
    fireEvent.change(screen.getByLabelText('Pharmacy name'), { target: { value: 'Town Pharmacy' } })
    fireEvent.change(screen.getByLabelText('Professional license number'), { target: { value: 'PH-001' } })
    fireEvent.change(screen.getByLabelText('Pharmacy address'), { target: { value: 'Nairobi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => expect(register).toHaveBeenCalledOnce())
    expect(register.mock.calls[0][0]).toMatchObject({
      role: 'PHARMACIST',
      license_number: 'PH-001',
      address: 'Nairobi',
    })
    expect(await screen.findByText(/regulator must review and activate/i)).toBeTruthy()
  })

  it('renders aggregate public stats and refreshes on request', async () => {
    getPublicStatistics.mockResolvedValue({
      data: {
        scans_today: 17,
        genuine_percent_today: 88.2,
        clone_alerts_pending: 2,
        registered_products: 12,
        registered_batches: 30,
        registered_pharmacies: 5,
      },
    })
    render(<MemoryRouter><PublicStatsPage /></MemoryRouter>)

    expect(await screen.findByText('17')).toBeTruthy()
    expect(screen.getByText('88.2%')).toBeTruthy()
    expect(getPublicStatistics).toHaveBeenCalled()
  })
})
