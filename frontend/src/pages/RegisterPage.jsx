import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, UserPlus } from 'lucide-react'
import { register } from '../services/api'

const INITIAL_FORM = {
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'PUBLIC',
  phone_number: '',
  organization_name: '',
  license_number: '',
  address: '',
  county: 'Nairobi',
}

function errorText(data) {
  if (!data) return 'Could not create the account. Please check your details and try again.'
  if (typeof data === 'string') return data
  return Object.values(data).flat().join(' ')
}

export default function RegisterPage() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const update = event => {
    const { name, value } = event.target
    setForm(current => ({ ...current, [name]: value }))
    setError('')
  }

  const submit = async event => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      const { data } = await register(form)
      setSuccess(data.pending_approval
        ? 'Registration received. A regulator must review and activate this professional account before sign-in.'
        : 'Your account is ready. You can now sign in.')
      setForm(INITIAL_FORM)
    } catch (requestError) {
      setError(errorText(requestError.response?.data))
    } finally {
      setSubmitting(false)
    }
  }

  const professionalRole = form.role === 'MANUFACTURER' || form.role === 'PHARMACIST'

  return (
    <main className="min-h-[calc(100dvh-64px)] bg-gradient-dark px-4 py-10">
      <div className="mx-auto max-w-xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-violet-600">
            <ShieldCheck size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-black text-white">Create a MediVerify account</h1>
          <p className="mt-2 text-sm text-gray-400">Professional access is reviewed before the account is activated.</p>
        </div>

        <form onSubmit={submit} className="glass space-y-4 rounded-2xl p-6">
          <div>
            <label className="label" htmlFor="register-role">Account type</label>
            <select id="register-role" name="role" className="input" value={form.role} onChange={update}>
              <option value="PUBLIC">Public customer</option>
              <option value="MANUFACTURER">Manufacturer (approval required)</option>
              <option value="PHARMACIST">Pharmacist (approval required)</option>
            </select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="register-username">Username</label>
              <input id="register-username" className="input" name="username" value={form.username} onChange={update} autoComplete="username" required maxLength={150} />
            </div>
            <div>
              <label className="label" htmlFor="register-email">Email</label>
              <input id="register-email" className="input" name="email" type="email" value={form.email} onChange={update} autoComplete="email" required />
            </div>
            <div>
              <label className="label" htmlFor="register-password">Password</label>
              <input id="register-password" className="input" name="password" type="password" value={form.password} onChange={update} autoComplete="new-password" minLength={6} required />
            </div>
            <div>
              <label className="label" htmlFor="register-phone">Phone (optional)</label>
              <input id="register-phone" className="input" name="phone_number" value={form.phone_number} onChange={update} autoComplete="tel" />
            </div>
          </div>

          {professionalRole && (
            <div className="space-y-4 border-t border-white/10 pt-4">
              <div>
                <label className="label" htmlFor="register-organization">
                  {form.role === 'PHARMACIST' ? 'Pharmacy name' : 'Manufacturer / organization name'}
                </label>
                <input id="register-organization" className="input" name="organization_name" value={form.organization_name} onChange={update} required />
              </div>
              <div>
                <label className="label" htmlFor="register-license">Professional license number</label>
                <input id="register-license" className="input" name="license_number" value={form.license_number} onChange={update} required />
              </div>
              {form.role === 'PHARMACIST' && (
                <>
                  <div>
                    <label className="label" htmlFor="register-address">Pharmacy address</label>
                    <input id="register-address" className="input" name="address" value={form.address} onChange={update} required />
                  </div>
                  <div>
                    <label className="label" htmlFor="register-county">County</label>
                    <input id="register-county" className="input" name="county" value={form.county} onChange={update} required />
                  </div>
                </>
              )}
              <p className="text-xs leading-relaxed text-amber-200/80">
                Professional accounts remain inactive until a regulator verifies the submitted details and activates them in the admin panel.
              </p>
            </div>
          )}

          {error && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>}
          {success && <p role="status" className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{success}</p>}
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-50">
            <UserPlus size={16} /> {submitting ? 'Submitting…' : 'Create account'}
          </button>
          <p className="text-center text-sm text-gray-500">
            Already registered? <Link to="/login" className="text-brand-300 hover:underline">Sign in</Link>
          </p>
        </form>
      </div>
    </main>
  )
}
