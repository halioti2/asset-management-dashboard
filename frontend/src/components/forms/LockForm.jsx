import { useState } from 'react'
import { lockAsset } from '../../api/assets'

export default function LockForm({ selectedAsset, onSuccess, onClose }) {
  const [pin, setPin] = useState('')
  const [message, setMessage] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      await lockAsset(selectedAsset.id, { pin, message, notes })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.error || 'Request failed')
      setShowConfirm(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3">
      <div className="flex justify-between items-center">
        <h2 className="font-semibold text-gray-800">Lock Device (SimpleMDM)</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>

      {selectedAsset ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          {selectedAsset.label || selectedAsset.serial_number} · {selectedAsset.type} · SN: {selectedAsset.serial_number}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Click a row to select an asset</p>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Lock PIN (6 digits)</label>
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={e => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="e.g. 123456"
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 font-mono"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Lock Screen Message (optional)</label>
        <input
          type="text"
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder="e.g. Contact IT to unlock this device"
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">Lock Reason / Notes (optional)</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          placeholder="e.g. Awaiting repair, lost, stolen…"
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 resize-none"
        />
      </div>

      {/* Confirmation overlay */}
      {showConfirm && (
        <div className="bg-orange-50 border border-orange-300 rounded-lg p-3 space-y-2">
          <p className="text-sm font-medium text-orange-800">
            Are you sure you want to lock <strong>{selectedAsset?.label || selectedAsset?.serial_number}</strong>?
          </p>
          <p className="text-xs text-orange-600">This will send a remote lock command via SimpleMDM.</p>
          <div className="flex gap-2">
            <button
              onClick={submit}
              disabled={submitting}
              className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
            >
              {submitting ? 'Locking…' : 'Confirm Lock'}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              disabled={submitting}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {!showConfirm && (
        <button
          onClick={() => {
            if (!selectedAsset) { setError('Select an asset first'); return }
            setShowConfirm(true)
          }}
          className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
        >
          Lock Device
        </button>
      )}
    </div>
  )
}
