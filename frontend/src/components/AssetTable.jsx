const STATUS_STYLES = {
  'Checked Out': 'bg-blue-100 text-blue-800',
  'Not Assigned': 'bg-green-100 text-green-800',
  'Historical': 'bg-gray-100 text-gray-600',
  'Locked': 'bg-red-100 text-red-800',
  'Returned': 'bg-orange-100 text-orange-800',
}

const COLUMNS = [
  { key: 'label', label: 'Label' },
  { key: 'type', label: 'Type' },
  { key: 'ownership', label: 'Ownership' },
  { key: 'serial_number', label: 'Serial #' },
  { key: 'status', label: 'Status' },
  { key: 'assigned_to', label: 'Assigned To' },
  { key: 'lease_end_date', label: 'Lease End Date' },
  { key: 'notes', label: 'Notes' },
  { key: 'returned', label: 'Returned' },
]

const EMPTY_FILTERS = { status: '', type: '', ownership: '', assigned_to: '', serial_number: '', label: '', lease_end_after: '', lease_end_before: '' }

const inputCls = "w-full rounded border border-gray-300 px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"

function FilterCell({ col, filters, set }) {
  if (col.key === 'label') {
    return <input type="text" placeholder="Search…" value={filters.label || ''} onChange={e => set('label', e.target.value)} className={inputCls} />
  }
  if (col.key === 'type') {
    return (
      <select value={filters.type || ''} onChange={e => set('type', e.target.value)} className={inputCls}>
        <option value="">All</option>
        <option>Laptop</option>
        <option>Tablet</option>
        <option>Chromebook</option>
        <option>Hotspot</option>
      </select>
    )
  }
  if (col.key === 'ownership') {
    return (
      <select value={filters.ownership || ''} onChange={e => set('ownership', e.target.value)} className={inputCls}>
        <option value="">All</option>
        <option>Purchased</option>
        <option>Lease-Temp</option>
        <option>Lease-Own</option>
        <option>Donated</option>
        <option>Returned</option>
      </select>
    )
  }
  if (col.key === 'serial_number') {
    return <input type="text" placeholder="Search…" value={filters.serial_number || ''} onChange={e => set('serial_number', e.target.value)} className={inputCls} />
  }
  if (col.key === 'status') {
    return (
      <select value={filters.status || ''} onChange={e => set('status', e.target.value)} className={inputCls}>
        <option value="">All</option>
        <option value="not_historical">All Laptops</option>
        <option>Checked Out</option>
        <option>Not Assigned</option>
        <option>Historical</option>
        <option>Returned</option>
        <option>Locked</option>
        <option>Uncategorized</option>
      </select>
    )
  }
  if (col.key === 'assigned_to') {
    return <input type="text" placeholder="Search…" value={filters.assigned_to || ''} onChange={e => set('assigned_to', e.target.value)} className={inputCls} />
  }
  if (col.key === 'lease_end_date') {
    return (
      <div className="flex flex-col gap-0.5">
        <input type="date" title="After" value={filters.lease_end_after || ''} onChange={e => set('lease_end_after', e.target.value)} className={inputCls} />
        <input type="date" title="Before" value={filters.lease_end_before || ''} onChange={e => set('lease_end_before', e.target.value)} className={inputCls} />
      </div>
    )
  }
  return null
}

export default function AssetTable({ assets, selectedIds, onSelectionChange, onRowClick, filters = {}, onFilterChange }) {
  const allSelected = assets.length > 0 && assets.every(a => selectedIds.has(a.id))
  const set = (key, value) => onFilterChange({ ...filters, [key]: value })

  const toggleAll = () => {
    if (allSelected) {
      onSelectionChange(new Set())
    } else {
      onSelectionChange(new Set(assets.map(a => a.id)))
    }
  }

  const toggleOne = (id) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelectionChange(next)
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 text-xs uppercase text-gray-500 tracking-wide">
          <tr>
            <th className="px-3 py-3 w-10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                className="rounded border-gray-300"
              />
            </th>
            {COLUMNS.map(col => (
              <th key={col.key} className="px-4 py-3 text-left whitespace-nowrap">
                {col.label}
              </th>
            ))}
          </tr>
          <tr className="border-t border-gray-200 bg-white">
            <th className="px-3 py-2" />
            {COLUMNS.map(col => (
              <th key={col.key} className="px-2 py-1.5 font-normal">
                <FilterCell col={col} filters={filters} set={set} />
              </th>
            ))}
            <th className="px-2 py-1.5 font-normal">
              <button
                onClick={() => onFilterChange(EMPTY_FILTERS)}
                className="text-xs text-gray-400 hover:text-gray-600 underline whitespace-nowrap"
              >
                Clear
              </button>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {assets.length === 0 && (
            <tr>
              <td colSpan={COLUMNS.length + 2} className="px-4 py-8 text-center text-gray-400">
                No assets found
              </td>
            </tr>
          )}
          {assets.map(asset => (
            <tr
              key={asset.id}
              onClick={() => onRowClick && onRowClick(asset)}
              className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                selectedIds.has(asset.id) ? 'bg-blue-50' : ''
              }`}
            >
              <td className="px-3 py-2" onClick={e => { e.stopPropagation(); toggleOne(asset.id) }}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(asset.id)}
                  onChange={() => toggleOne(asset.id)}
                  className="rounded border-gray-300"
                />
              </td>
              {COLUMNS.map(col => (
                <td key={col.key} className="px-4 py-2 max-w-[200px] truncate">
                  {col.key === 'status' ? (
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[asset.status] || 'bg-gray-100 text-gray-600'}`}>
                      {asset.status}
                    </span>
                  ) : (
                    <span title={asset[col.key]}>{asset[col.key] || '—'}</span>
                  )}
                </td>
              ))}
              <td />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
