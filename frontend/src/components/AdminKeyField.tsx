import { useState } from 'react'
import { getApiKey, setApiKey } from '../services/api'

/** Lets the user supply the API key on a hosted deployment. The value stays in
 *  this browser's localStorage — it is never part of the built bundle. */
export default function AdminKeyField() {
  const [value, setValue] = useState(getApiKey())
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState(false)

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm text-slate-600 underline-offset-2 hover:underline"
      >
        {value ? 'Admin key ✓' : 'Admin key'}
      </button>
    )
  }

  return (
    <span className="flex items-center gap-2">
      <input
        type="password"
        value={value}
        onChange={(event) => {
          setValue(event.target.value)
          setSaved(false)
        }}
        placeholder="API key"
        aria-label="Admin API key"
        className="w-40 border border-slate-300 px-2 py-1 text-sm"
      />
      <button
        type="button"
        onClick={() => {
          setApiKey(value)
          setSaved(true)
          setOpen(false)
        }}
        className="border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50"
      >
        Save
      </button>
      {saved && <span className="text-xs text-emerald-700">Saved</span>}
    </span>
  )
}
