import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Enquiries() {
  const [enquiries, setEnquiries] = useState<any[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => { api.enquiries().then(d => setEnquiries(d.enquiries || [])) }, [])

  const displayFields = ['client_name','city','property_type','configuration','area_sqft','budget_range','timeline']

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-200">Enquiries</h1>
        <p className="text-sm text-slate-500 mt-1">{enquiries.length} collected</p>
      </div>

      {enquiries.length === 0 ? (
        <div className="card text-center py-12 text-slate-500">No enquiries yet.</div>
      ) : (
        <div className="space-y-2">
          {enquiries.map((e, i) => {
            const key = e.id || e.session_id || String(i)
            const fields = e.extracted_fields || e
            return (
              <div key={key} className="card">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpanded(expanded === key ? null : key)}
                >
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1 flex-1">
                    {displayFields.slice(0,4).map(f => (
                      <div key={f}>
                        <p className="text-[10px] text-slate-600">{f}</p>
                        <p className="text-xs text-slate-300">{fields[f] || '—'}</p>
                      </div>
                    ))}
                  </div>
                  <span className="text-slate-500 text-xs ml-4">{expanded === key ? '▲' : '▼'}</span>
                </div>
                {expanded === key && (
                  <div className="mt-4 pt-4 border-t border-slate-700/50">
                    <pre className="text-xs text-slate-400 overflow-x-auto whitespace-pre-wrap bg-navy-900 rounded-lg p-3">
                      {JSON.stringify(fields, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
