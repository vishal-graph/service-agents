import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Flower2, Eye, EyeOff } from 'lucide-react'
import { api, setToken } from '../api/client'
import toast from 'react-hot-toast'

export default function Login() {
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await api.login(password)
      if (res.token) {
        setToken(res.token)
        navigate('/krsna/dashboard')
      } else {
        toast.error(res.detail || 'Invalid password')
      }
    } catch {
      toast.error('Login failed. Check your password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-indigo-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4 
                          ring-1 ring-indigo-500/30">
            <Flower2 className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-200">Krsna Panel</h1>
          <p className="text-slate-500 text-sm mt-1">Aadhya AI Operations · TatvaOps</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="text-xs text-slate-400 font-medium mb-1.5 block">
              Admin Password
            </label>
            <div className="relative">
              <input
                type={show ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter admin password"
                className="input pr-10"
                required
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShow(s => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full justify-center flex"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-600 mt-6">
          Internal use only · TatvaOps
        </p>
      </div>
    </div>
  )
}
