import { useState } from 'react'
import { addAsset } from '../../api/assets'

const OWNERSHIP_TYPES = ['Purchased', 'Lease-Temp', 'Lease-Own', 'Donated']
const ASSET_STATUSES = ['Assigned', 'Historical', 'Returned', 'Unusable', 'Ready to Assign']
const TYPES = ['Laptop', 'Chromebook', 'Tablet', 'Hotspot', 'Other']

export default function AddLaptopForm({ onSuccess, onClose }) {
  const [form, setForm] = useState({ type: '', serial_number: '', ownership: '', asset_status: 'Ready to Assign', label: '', date_assigned: '', lease_end_date: '', notes: '' })
  const [error, setError] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const validate = () => {
    const e = {}
    if (!form.type.trim()) e.type = 'Required'
    if (!form.serial_number.trim()) e.serial_number = 'Required'
    if (!form.ownership.trim()) e.ownership = 'Required'
    if (!form.asset_status.trim()) e.asset_status = 'Required'
    return e
  }

  const submit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setError(errs); return }
    setSubmitting(true)
    setApiError('')
    try {
      await addAsset(form)
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
        <h2 className="font-semibold text-gray-800">Add New Asset</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      {apiError && <p className="text-sm text-red-600">{apiError}</p>}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Type *" error={error.type}>
          <select value={form.type} onChange={e => set('type', e.target.value)} className={sel(error.type)}>
            <option value="">Select type…</option>
            {TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Serial # *" error={error.serial_number}>
          <input value={form.serial_number} onChange={e => set('serial_number', e.target.value)} className={inp(error.serial_number)} placeholder="SN123456" />
        </Field>
        <Field label="Ownership *" error={error.ownership}>
          <select value={form.ownership} onChange={e => set('ownership', e.target.value)} className={sel(error.ownership)}>
            <option value="">Select ownership…</option>
            {OWNERSHIP_TYPES.map(o => <option key={o}>{o}</option>)}
          </select>
        </Field>
        <Field label="Asset Status *" error={error.asset_status}>
          <select value={form.asset_status} onChange={e => set('asset_status', e.target.value)} className={sel(error.asset_status)}>
            <option value="">Select status…</option>
            {ASSET_STATUSES.map(s => <option key={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Label">
          <input value={form.label} onChange={e => set('label', e.target.value)} className={inp()} placeholder="Asset label / tag" />
        </Field>
        <Field label="Date Assigned">
          <input type="date" value={form.date_assigned} onChange={e => set('date_assigned', e.target.value)} className={inp()} />
        </Field>
        <Field label="Lease End Date">
          <input type="date" value={form.lease_end_date} onChange={e => set('lease_end_date', e.target.value)} className={inp()} />
        </Field>
      </div>
      <Field label="Notes">
        <textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2} className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
      </Field>
      <button type="submit" disabled={submitting} className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors">
        {submitting ? 'Adding…' : 'Add Asset'}
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

const inp = (err) => `rounded-md border ${err ? 'border-red-400' : 'border-gray-300'} px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full`
const sel = (err) => `rounded-md border ${err ? 'border-red-400' : 'border-gray-300'} px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full bg-white`
