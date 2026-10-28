import { Search, User, LogOut } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { NotificationBell } from '@/components/NotificationBell'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

export function TopBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [showMenu, setShowMenu] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 border-b border-surface-800 bg-surface-950 flex items-center justify-between px-6 sticky top-0 z-20">
      {/* Search */}
      <div className="relative w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
        <input
          type="text"
          placeholder="Search pipelines, nodes, modules..."
          className="w-full bg-surface-900 border border-surface-800 rounded-lg pl-10 pr-4 py-2 text-sm text-surface-200 
            placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30 transition-all"
        />
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <NotificationBell />

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-800 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-primary-600/20 flex items-center justify-center">
              <User className="w-3.5 h-3.5 text-primary-400" />
            </div>
            <div className="text-left">
              <p className="text-xs font-medium text-surface-200 leading-tight">{user?.name || 'User'}</p>
              <p className="text-[10px] text-surface-500 capitalize">{user?.tier || 'free'} tier</p>
            </div>
          </button>

          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border border-surface-800 bg-surface-900 shadow-xl z-20 py-1">
                <button className="w-full flex items-center gap-2 px-4 py-2 text-sm text-surface-300 hover:bg-surface-800 transition-colors">
                  <User className="w-4 h-4" />
                  Profile
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-danger-400 hover:bg-surface-800 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}