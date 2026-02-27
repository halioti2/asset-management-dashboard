import { useState } from 'react'
import { returnAsset } from '../../api/assets'

export default function ReturnForm({ selectedAsset, onSuccess, onClose }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!selectedAsset) { setError('Select a checked-out asset first'); return }
    setSubmitting(true)
    setError('')
    try {
      await returnAsset(selectedAsset.id, { notes })
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
        <h2 className="font-semibold text-gray-800">Return Asset</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      {selectedAsset ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          {selectedAsset.label || selectedAsset.serial_number} · assigned to {selectedAsset.assigned_to}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Click a checked-out row to select</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Condition / Return Notes</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
          placeholder="Describe condition, any damage, etc."
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
        />
      </div>
      <button type="submit" disabled={submitting} className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors">
        {submitting ? 'Processing…' : 'Confirm Return'}
      </button>
    </form>
  )
}
