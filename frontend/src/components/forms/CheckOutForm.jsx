import { useState, useEffect } from 'react'
import { checkoutAsset } from '../../api/assets'

export default function CheckOutForm({ selectedAsset, onSuccess, onClose }) {
  const [form, setForm] = useState({ assigned_to: '', email: '', phone: '', duration_needed: '' })
  const [error, setError] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    if (selectedAsset) {
      const currentAssignedTo = selectedAsset.assigned_to || ''
      setForm(f => ({
        ...f,
        assigned_to: currentAssignedTo.toLowerCase() === 'ready to assign' ? '' : currentAssignedTo,
        email: selectedAsset.email || '',
        phone: selectedAsset.phone || '',
      }))
    }
  }, [selectedAsset])

  const validate = () => {
    const e = {}
    if (!form.assigned_to.trim()) e.assigned_to = 'Required'
    if (!form.email.trim()) e.email = 'Required'
    if (!form.phone.trim()) e.phone = 'Required'
    return e
  }

  const submit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setError(errs); return }
    if (!selectedAsset) { setApiError('Select an asset row first'); return }

    setSubmitting(true)
    setApiError('')
    try {
      await checkoutAsset(selectedAsset.id, { assigned_to: form.assigned_to, email: form.email, phone: form.phone })
      onSuccess()
    } catch (err) {
      setApiError(err.response?.data?.error || 'Request failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3">
      <div className="flex justify-between items-center">
        <h2 className="font-semibold text-gray-800">Check Out Asset</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      {selectedAsset ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          {selectedAsset.label || selectedAsset.serial_number} · {selectedAsset.type}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Click a row in the table to select an asset</p>
      )}
      {apiError && <p className="text-sm text-red-600">{apiError}</p>}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Assigned To" error={error.assigned_to}>
          <input value={form.assigned_to} onChange={e => setForm(f => ({...f, assigned_to: e.target.value}))} className={input(error.assigned_to)} placeholder="Full name" />
        </Field>
        <Field label="Email" error={error.email}>
          <input type="email" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} className={input(error.email)} placeholder="email@example.com" />
        </Field>
        <Field label="Phone" error={error.phone}>
          <input value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))} className={input(error.phone)} placeholder="555-555-5555" />
        </Field>
        <Field label="Duration Needed (optional)">
          <input value={form.duration_needed} onChange={e => setForm(f => ({...f, duration_needed: e.target.value}))} className={input()} placeholder="e.g. 2 weeks" />
        </Field>
      </div>
      <button type="submit" disabled={submitting} className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors">
        {submitting ? 'Checking out…' : 'Submit Check Out'}
      </button>
    </form>
  )
}

function Field({ label, error, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  )
}

const input = (err) => `rounded-md border ${err ? 'border-red-400' : 'border-gray-300'} px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`
