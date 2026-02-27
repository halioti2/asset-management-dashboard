import { useState, useEffect } from 'react'
import { bulkUpdateNotes } from '../../api/assets'

export default function UpdateNotesForm({ selectedIds, onSuccess, onClose }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const ids = [...selectedIds]

  const submit = async (e) => {
    e.preventDefault()
    if (ids.length === 0) { setError('Select at least one asset'); return }
    setSubmitting(true)
    setError('')
    try {
      await bulkUpdateNotes(ids, notes)
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
        <h2 className="font-semibold text-gray-800">Update Notes</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      {ids.length > 0 ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          Updating {ids.length} asset{ids.length > 1 ? 's' : ''}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Select assets using checkboxes</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Notes (replaces existing)</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
          placeholder="Enter new notes…"
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none"
        />
      </div>
      <button type="submit" disabled={submitting} className="w-full bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors">
        {submitting ? 'Updating…' : `Update Notes${ids.length > 1 ? ` (${ids.length})` : ''}`}
      </button>
    </form>
  )
}
