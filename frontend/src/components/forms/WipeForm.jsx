import { useState, useEffect } from 'react'
import { wipeAsset, getMdmStatus } from '../../api/assets'

function SafetyBadge({ pass: ok, warn, label, reason }) {
  if (warn) return (
    <div className="flex flex-col">
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">&#9888; {label}</span>
      {reason && <span className="text-[10px] text-yellow-600 pl-2 mt-0.5">{reason}</span>}
    </div>
  )
  if (ok) return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">&#10003; {label}</span>
  return (
    <div className="flex flex-col">
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-red-100 text-red-700">&#10007; {label}</span>
      {reason && <span className="text-[10px] text-red-600 pl-2 mt-0.5">{reason}</span>}
    </div>
  )
}

export default function WipeForm({ selectedAsset, onSuccess, onClose }) {
  const [mdm, setMdm] = useState(null)
  const [mdmLoading, setMdmLoading] = useState(false)
  const [confirmSerial, setConfirmSerial] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    if (!selectedAsset) { setMdm(null); return }
    setMdmLoading(true)
    setError('')
    setConfirmSerial('')
    setShowConfirm(false)
    getMdmStatus(selectedAsset.id)
      .then(data => setMdm(data))
      .catch(err => setError(err.response?.data?.error || 'Failed to check MDM status'))
      .finally(() => setMdmLoading(false))
  }, [selectedAsset?.id])

  // Safety checks
  const foundInMdm = mdm?.found
  const enrolled = mdm?.enrolled
  const isDonated = mdm?.ownership?.toLowerCase() === 'donated'
  const isHistorical = mdm?.derived_status === 'Historical'
  const isUncategorized = mdm?.derived_status === 'Uncategorized'
  const statusOk = mdm && !isHistorical && !isUncategorized
  const ownershipOk = mdm && !isDonated

  const allSafe = foundInMdm && enrolled && statusOk && ownershipOk
  const serialMatch = confirmSerial.toUpperCase() === (selectedAsset?.serial_number || '').toUpperCase()

  // Build failure reasons for each check
  const getStatusReason = () => {
    if (!mdm) return ''
    if (isHistorical) return 'Historical record — select the current record for this device'
    if (isUncategorized) return 'Status unclear — update ownership/status first'
    return ''
  }

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      await wipeAsset(selectedAsset.id, { confirm_serial: confirmSerial })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.error || 'Request failed')
      setShowConfirm(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white border border-red-200 rounded-lg p-4 shadow-sm space-y-3">
      <div className="flex justify-between items-center">
        <h2 className="font-semibold text-red-800">Wipe Device (SimpleMDM)</h2>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>

      {selectedAsset ? (
        <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
          {selectedAsset.label || selectedAsset.serial_number} · {selectedAsset.type} · SN: {selectedAsset.serial_number}
        </p>
      ) : (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">Click a row to select an asset</p>
      )}

      {error && <p className="text-sm text-red-600 bg-red-50 rounded px-2 py-1.5">{error}</p>}

      {/* Safety badges */}
      {selectedAsset && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-gray-600">Safety Checks</p>
          {mdmLoading ? (
            <p className="text-xs text-gray-400">Checking SimpleMDM…</p>
          ) : mdm ? (
            <div className="flex flex-wrap gap-1.5">
              <SafetyBadge
                pass={foundInMdm}
                label="Found in SimpleMDM"
                reason={!foundInMdm ? 'Serial not found — verify it matches SimpleMDM' : ''}
              />
              <SafetyBadge
                pass={enrolled}
                warn={foundInMdm && !enrolled}
                label={enrolled ? 'Enrolled' : 'Not enrolled'}
                reason={foundInMdm && !enrolled ? 'Device must be enrolled to receive wipe command' : ''}
              />
              <SafetyBadge
                pass={statusOk}
                label={`Status: ${mdm.derived_status}`}
                reason={getStatusReason()}
              />
              <SafetyBadge
                pass={ownershipOk}
                label={ownershipOk ? `Ownership: ${mdm.ownership || '—'}` : 'Donated'}
                reason={isDonated ? 'Donated devices are no longer managed and cannot be wiped' : ''}
              />
            </div>
          ) : null}
        </div>
      )}

      {/* Serial confirmation */}
      {selectedAsset && allSafe && (
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">
            Type the serial number to confirm: <span className="font-mono text-red-600">{selectedAsset.serial_number}</span>
          </label>
          <input
            type="text"
            value={confirmSerial}
            onChange={e => setConfirmSerial(e.target.value)}
            placeholder="Enter serial number"
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500"
          />
        </div>
      )}

      {/* Blocked message when checks fail */}
      {selectedAsset && !mdmLoading && mdm && !allSafe && (
        <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1.5">
          Wipe is blocked — resolve the failed checks above before proceeding.
        </p>
      )}

      {/* Confirmation overlay */}
      {showConfirm && (
        <div className="bg-red-50 border border-red-300 rounded-lg p-3 space-y-2">
          <p className="text-sm font-medium text-red-800">
            Are you sure you want to <strong>WIPE</strong> {selectedAsset?.label || selectedAsset?.serial_number}?
          </p>
          <p className="text-xs text-red-600">This will erase all content and settings on the device. This cannot be undone.</p>
          <div className="flex gap-2">
            <button
              onClick={submit}
              disabled={submitting}
              className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
            >
              {submitting ? 'Wiping…' : 'Confirm Wipe'}
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
            if (!allSafe) { setError('Wipe is blocked — resolve the failed safety checks first.'); return }
            if (!serialMatch) { setError('Serial number does not match. Re-enter to confirm.'); return }
            setError('')
            setShowConfirm(true)
          }}
          disabled={!allSafe || !serialMatch}
          className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg py-2 text-sm font-medium transition-colors"
        >
          Wipe Device
        </button>
      )}
    </div>
  )
}
