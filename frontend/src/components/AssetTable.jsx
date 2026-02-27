const STATUS_STYLES = {
  'Checked Out': 'bg-blue-100 text-blue-800',
  'Not Assigned': 'bg-green-100 text-green-800',
  'Historical': 'bg-gray-100 text-gray-600',
  'Locked': 'bg-red-100 text-red-800',
}

const COLUMNS = [
  { key: 'label', label: 'Label' },
  { key: 'type', label: 'Type' },
  { key: 'serial_number', label: 'Serial #' },
  { key: 'status', label: 'Status' },
  { key: 'assigned_to', label: 'Assigned To' },
  { key: 'lease_end_date', label: 'Lease End Date' },
  { key: 'notes', label: 'Notes' },
  { key: 'returned', label: 'Returned' },
]

export default function AssetTable({ assets, selectedIds, onSelectionChange, onRowClick }) {
  const allSelected = assets.length > 0 && assets.every(a => selectedIds.has(a.id))

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
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {assets.length === 0 && (
            <tr>
              <td colSpan={COLUMNS.length + 1} className="px-4 py-8 text-center text-gray-400">
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
