import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, BellOff, CheckCheck, Settings, Trash2, GitBranch, Server, PackageCheck, Inbox, X } from 'lucide-react'
import { useNotifications, type AppNotification } from '@/context/NotificationsContext'
import { timeAgo } from '@/lib/time'

const kindConfig: Record<AppNotification['kind'], { icon: typeof Bell; color: string }> = {
  pipeline: { icon: GitBranch, color: 'text-primary-400' },
  node: { icon: Server, color: 'text-success-400' },
  install: { icon: PackageCheck, color: 'text-accent-400' },
}

export function NotificationBell() {
  const { notifications, unreadCount, preferences, markAllRead, markRead, remove, clearAll } =
    useNotifications()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-colors"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        {preferences.enabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
        {unreadCount > 0 && preferences.enabled && (
          <span className="absolute top-1 right-1 min-w-4 h-4 px-1 rounded-full bg-danger-500 text-white text-[10px] font-semibold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-surface-800 bg-surface-900 shadow-2xl z-40 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-surface-200">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-primary-600/15 text-primary-400 border border-primary-600/20">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={markAllRead}
                className="p-1.5 rounded-md text-surface-500 hover:text-surface-200 hover:bg-surface-800 transition-colors"
                title="Mark all as read"
              >
                <CheckCheck className="w-4 h-4" />
              </button>
              <button
                onClick={clearAll}
                className="p-1.5 rounded-md text-surface-500 hover:text-danger-400 hover:bg-surface-800 transition-colors"
                title="Clear all"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {!preferences.enabled && (
            <div className="px-4 py-2 text-[11px] text-warning-400 bg-warning-500/10 border-b border-warning-500/20">
              Notifications are paused. Live events won't create new alerts.
            </div>
          )}

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-10 px-4 text-center">
                <Inbox className="w-8 h-8 text-surface-700 mx-auto mb-2" />
                <p className="text-sm text-surface-500">You're all caught up</p>
              </div>
            ) : (
              notifications.map((n) => {
                const cfg = kindConfig[n.kind]
                const Icon = cfg.icon
                return (
                  <div
                    key={n.id}
                    className={`group relative border-b border-surface-800 last:border-0 hover:bg-surface-800/40 transition-colors ${
                      n.read ? 'opacity-60' : ''
                    }`}
                  >
                    <button
                      onClick={() => markRead(n.id)}
                      className="w-full flex items-start gap-3 px-4 py-3 text-left"
                    >
                      <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Icon className={`w-4 h-4 ${cfg.color}`} />
                      </div>
                      <div className="flex-1 min-w-0 pr-4">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm text-surface-200 font-medium leading-snug">{n.title}</p>
                          {!n.read && (
                            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 flex-shrink-0 mt-1" />
                          )}
                        </div>
                        <p className="text-xs text-surface-500 mt-0.5 leading-snug">{n.description}</p>
                        <p className="text-[10px] text-surface-600 mt-1">{timeAgo(n.createdAt)}</p>
                      </div>
                    </button>
                    <button
                      onClick={() => remove(n.id)}
                      className="absolute right-2 top-2 p-1 rounded-md text-surface-600 opacity-0 group-hover:opacity-100 hover:text-danger-400 hover:bg-surface-800 transition-all"
                      title="Dismiss"
                      aria-label={`Dismiss ${n.title}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                )
              })
            )}
          </div>

          <Link
            to="/settings#notifications"
            onClick={() => setOpen(false)}
            className="flex items-center justify-center gap-2 px-4 py-2.5 text-xs text-surface-400 hover:text-surface-200 bg-surface-950/50 border-t border-surface-800 transition-colors"
          >
            <Settings className="w-3.5 h-3.5" />
            Notification preferences
          </Link>
        </div>
      )}
    </div>
  )
}
