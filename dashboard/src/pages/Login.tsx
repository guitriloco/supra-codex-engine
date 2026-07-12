import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/Button'
import { Hexagon, Eye, EyeOff } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { login, isLoading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Invalid credentials')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600/10 mb-4">
            <Hexagon className="w-8 h-8 text-primary-400" />
          </div>
          <h1 className="text-xl font-bold text-white">
            Supra<span className="text-primary-400">Codex</span>
          </h1>
          <p className="text-sm text-surface-500 mt-1">Orchestration Dashboard</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-surface-400 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-surface-900 border border-surface-800 rounded-lg px-4 py-2.5 text-sm text-surface-200 
                placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30 transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-surface-400 mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-surface-900 border border-surface-800 rounded-lg px-4 py-2.5 pr-10 text-sm text-surface-200 
                  placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && <p className="text-xs text-danger-400 bg-danger-500/10 rounded-lg px-3 py-2">{error}</p>}

          <Button type="submit" isLoading={isLoading} className="w-full">
            Sign in
          </Button>
        </form>

        <p className="text-xs text-surface-600 text-center mt-6">
          Demo: use any email and password to sign in
        </p>
      </div>
    </div>
  )
}