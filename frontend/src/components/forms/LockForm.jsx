import { useState } from 'react'
import { lockAsset } from '../../api/assets'

export default function LockForm({ selectedAsset, onSuccess, onClose }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!selectedAsset) { setError('Select an asset first'); return }
    setSubmitting(true)
    setError('')
    try {
      await lockAsset(selectedAsset.id, { notes })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.error || 'Request failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3">
      <div className="flex justify-between items-center">
        <h2 className="font-semibold text-gray-800">Lock Asset</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      {selectedAsset ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          {selectedAsset.label || selectedAsset.serial_number} · {selectedAsset.type}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Click a row to select an asset</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Lock Reason (optional)</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          placeholder="e.g. Awaiting repair, lost, stolen…"
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
        />
      </div>
      <button type="submit" disabled={submitting} className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors">
        {submitting ? 'Locking…' : 'Lock Asset'}
      </button>
    </form>
  )
}
