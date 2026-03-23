const ACTIONS = [
  { id: 'checkout', label: 'Check Out', color: 'bg-blue-600 hover:bg-blue-700' },
  { id: 'return',   label: 'Return',    color: 'bg-green-600 hover:bg-green-700' },
  { id: 'add',      label: 'Add Laptop', color: 'bg-indigo-600 hover:bg-indigo-700' },
  { id: 'lock',     label: 'Lock',      color: 'bg-orange-600 hover:bg-orange-700' },
  { id: 'wipe',     label: 'Wipe',      color: 'bg-red-600 hover:bg-red-700' },
  { id: 'notes',    label: 'Update Notes', color: 'bg-amber-600 hover:bg-amber-700' },
]

export default function ActionBar({ activeForm, onFormToggle, selectedCount, totalCount }) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {ACTIONS.map(action => (
        <button
          key={action.id}
          onClick={() => onFormToggle(action.id)}
          className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors ${action.color} ${
            activeForm === action.id ? 'ring-2 ring-offset-2 ring-current opacity-90' : ''
          }`}
        >
          {action.label}
        </button>
      ))}
      <span className="ml-auto text-sm text-gray-500">
        {selectedCount > 0 ? `${selectedCount} selected · ` : ''}{totalCount} total
      </span>
    </div>
  )
}
