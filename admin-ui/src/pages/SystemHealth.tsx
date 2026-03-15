import { useEffect, useState } from 'react'
import { api, createSSEStream } from '../api/client'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

function StatusBadge({ status }: { status: string }) {
  const ok = status === 'ok' || status === 'configured'
  const warn = status === 'not_configured'
  return (
    <div className={clsx(
      'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium',
      ok ? 'bg-teal-600/20 text-teal-300' :
      warn ? 'bg-amber-600/20 text-amber-300' : 'bg-red-600/20 text-red-300'
    )}>
      {ok ? <CheckCircle className="w-3.5 h-3.5" /> :
       warn ? <AlertCircle className="w-3.5 h-3.5" /> :
       <XCircle className="w-3.5 h-3.5" />}
      {status}
    </div>
  )
}

export default function SystemHealth() {
  const [health, setHealth] = useState<any>(null)
  const [liveEvents, setLiveEvents] = useState<any[]>([])
  const [esStatus, setEsStatus] = useState('connecting')

  useEffect(() => {
    api.health().then(setHealth)
    const id = setInterval(() => api.health().then(setHealth), 30000)

    const es = createSSEStream((data: any) => {
      if (data.event !== 'connected') {
        setLiveEvents(prev => [data, ...prev].slice(0, 50))
      }
      setEsStatus('connected')
    })
    es.onerror = () => setEsStatus('error')

    return () => { clearInterval(id); es.close() }
  }, [])

  const services = health?.services || {}

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-200">System Health</h1>
        <p className="text-sm text-slate-500 mt-1">
          Overall: <span className={health?.overall === 'healthy' ? 'text-teal-400' : 'text-amber-400'}>
            {health?.overall || 'checking...'}
          </span>
        </p>
      </div>

      {/* Service grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(services).map(([name, info]: [string, any]) => (
          <div key={name} className="card flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-300 capitalize">{name}</p>
              {info.model && <p className="text-xs text-slate-500">{info.model}</p>}
              {info.error && <p className="text-xs text-red-400 mt-0.5 truncate max-w-[180px]">{info.error}</p>}
            </div>
            <StatusBadge status={info.status} />
          </div>
        ))}
      </div>

      {/* Live monitor */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-slate-400">Live Monitor</h3>
          <span className={clsx(
            'badge',
            esStatus === 'connected' ? 'bg-teal-600/20 text-teal-300' : 'bg-amber-600/20 text-amber-300'
          )}>
            ● {esStatus}
          </span>
        </div>
        <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
          {liveEvents.length === 0 ? (
            <p className="text-slate-600 py-4 text-center">Waiting for events...</p>
          ) : (
            liveEvents.map((ev, i) => (
              <div key={i} className="flex gap-3 text-xs">
                <span className="text-slate-600 flex-shrink-0">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-indigo-300 flex-shrink-0">{ev.event}</span>
                <span className="text-slate-500 truncate">{ev.session_id}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
