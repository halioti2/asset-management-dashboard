import { useState, useEffect, useCallback } from 'react'
import { getAssets } from './api/assets'
import ActionBar from './components/ActionBar'
import AssetTable from './components/AssetTable'
import CheckOutForm from './components/forms/CheckOutForm'
import ReturnForm from './components/forms/ReturnForm'
import AddLaptopForm from './components/forms/AddLaptopForm'
import LockForm from './components/forms/LockForm'
import WipeForm from './components/forms/WipeForm'
import UpdateNotesForm from './components/forms/UpdateNotesForm'

const EMPTY_FILTERS = { status: '', type: '', ownership: '', assigned_to: '', serial_number: '', label: '', lease_end_after: '', lease_end_before: '' }

function parseLeaseDate(dateStr) {
  // Handle "MM/DD/YYYY" format and "YYYY-MM-DD" format
  if (!dateStr || dateStr === 'N/A' || dateStr === '-') return null

  // If already YYYY-MM-DD format, use as-is
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr

  // Parse MM/DD/YYYY → YYYY-MM-DD
  const match = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (match) {
    const [, m, d, y] = match
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  }
  return null
}

function applyFilters(assets, filters) {
  return assets.filter(a => {
    if (filters.status === 'not_historical' && a.status === 'Historical') return false
    if (filters.status && filters.status !== 'not_historical' && a.status !== filters.status) return false
    if (filters.type && (a.type || '').toLowerCase() !== filters.type.toLowerCase()) return false
    if (filters.ownership && (a.ownership || '').toLowerCase() !== filters.ownership.toLowerCase()) return false
    if (filters.assigned_to && !(a.assigned_to || '').toLowerCase().includes(filters.assigned_to.toLowerCase())) return false
    if (filters.serial_number && !(a.serial_number || '').toLowerCase().includes(filters.serial_number.toLowerCase())) return false
    if (filters.label && !(a.label || '').toLowerCase().includes(filters.label.toLowerCase())) return false

    if (filters.lease_end_after || filters.lease_end_before) {
      const assetDate = parseLeaseDate(a.lease_end_date)
      if (!assetDate) return false // Can't filter dates if asset has no valid date

      if (filters.lease_end_after && assetDate < filters.lease_end_after) return false
      if (filters.lease_end_before && assetDate > filters.lease_end_before) return false
    }
    return true
  })
}

export default function App() {
  const [assets, setAssets] = useState([])
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [activeForm, setActiveForm] = useState(null)
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const fetchAssets = useCallback(async () => {
    try {
      const data = await getAssets()
      setAssets(data)
      setLoadError('')
    } catch {
      setLoadError('Failed to load assets — is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAssets() }, [fetchAssets])

  const handleFormToggle = (formId) => {
    const isClosing = activeForm === formId
    setActiveForm(isClosing ? null : formId)
    if (isClosing) {
      setSelectedIds(new Set())
      setSelectedAsset(null)
    }
  }

  const handleSuccess = () => {
    setActiveForm(null)
    setSelectedIds(new Set())
    setSelectedAsset(null)
    fetchAssets()
  }

  const handleSelectionChange = (newSelectedIds) => {
    setSelectedIds(newSelectedIds)
    if (newSelectedIds.size === 1) {
      const id = [...newSelectedIds][0]
      setSelectedAsset(assets.find(a => a.id === id) || null)
    } else {
      setSelectedAsset(null)
    }
  }

  const handleRowClick = (asset) => {
    setSelectedAsset(asset)
    setSelectedIds(new Set([asset.id]))
  }

  const filtered = applyFilters(assets, filters)

  const formProps = { onSuccess: handleSuccess, onClose: () => setActiveForm(null) }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">Asset Management Dashboard</h1>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-5 space-y-4">
        {loadError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{loadError}</div>
        )}

        <ActionBar
          activeForm={activeForm}
          onFormToggle={handleFormToggle}
          selectedCount={selectedIds.size}
          totalCount={filtered.length}
        />

        {activeForm === 'checkout' && <CheckOutForm selectedAsset={selectedAsset} {...formProps} />}
        {activeForm === 'return'   && <ReturnForm   selectedAsset={selectedAsset} {...formProps} />}
        {activeForm === 'add'      && <AddLaptopForm {...formProps} />}
        {activeForm === 'lock'     && <LockForm      selectedAsset={selectedAsset} {...formProps} />}
        {activeForm === 'wipe'     && <WipeForm      selectedAsset={selectedAsset} {...formProps} />}
        {activeForm === 'notes'    && <UpdateNotesForm selectedIds={selectedIds} {...formProps} />}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading assets…</div>
        ) : (
          <AssetTable
            assets={filtered}
            selectedIds={selectedIds}
            onSelectionChange={handleSelectionChange}
            onRowClick={handleRowClick}
            filters={filters}
            onFilterChange={setFilters}
          />
        )}
      </main>
    </div>
  )
}
