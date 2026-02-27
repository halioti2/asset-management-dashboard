export default function FilterBar({ filters, onChange }) {
  const set = (key, value) => onChange({ ...filters, [key]: value })

  return (
    <div className="flex flex-wrap gap-3 items-end bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Status</label>
        <select
          value={filters.status || ''}
          onChange={e => set('status', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All</option>
          <option value="Checked Out">Checked Out</option>
          <option value="Not Assigned">Not Assigned</option>
          <option value="Historical">Historical</option>
          <option value="Locked">Locked</option>
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Type</label>
        <select
          value={filters.type || ''}
          onChange={e => set('type', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All</option>
          <option value="Laptop">Laptop</option>
          <option value="Tablet">Tablet</option>
          <option value="Chromebook">Chromebook</option>
          <option value="Hotspot">Hotspot</option>
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Assigned To</label>
        <input
          type="text"
          placeholder="Search name..."
          value={filters.assigned_to || ''}
          onChange={e => set('assigned_to', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Serial #</label>
        <input
          type="text"
          placeholder="Search serial..."
          value={filters.serial_number || ''}
          onChange={e => set('serial_number', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Lease End After</label>
        <input
          type="date"
          value={filters.lease_end_after || ''}
          onChange={e => set('lease_end_after', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">Lease End Before</label>
        <input
          type="date"
          value={filters.lease_end_before || ''}
          onChange={e => set('lease_end_before', e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <button
        onClick={() => onChange({ status: '', type: '', assigned_to: '', lease_end_after: '', lease_end_before: '' })}
        className="ml-auto text-xs text-gray-400 hover:text-gray-600 underline self-end pb-1"
      >
        Clear filters
      </button>
    </div>
  )
}
