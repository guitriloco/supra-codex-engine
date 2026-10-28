import type { ReactNode } from 'react'
import { Bell, BellOff, GitBranch, Server, PackageCheck, RotateCcw, Send } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/Card'
import { Button } from '@/components/Button'
import {
  useNotifications,
  type NotificationKind,
  type NotificationPreferences as Prefs,
} from '@/context/NotificationsContext'

interface ToggleRowProps {
  label: string
  description: string
  icon: ReactNode
  checked: boolean
  disabled?: boolean
  onChange: (next: boolean) => void
}

function ToggleRow({ label, description, icon, checked, disabled, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-surface-800 last:border-0">
      <div className="flex items-start gap-3 min-w-0">
        <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-surface-200">{label}</p>
          <p className="text-xs text-surface-500">{description}</p>
        </div>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed ${
          checked ? 'bg-primary-600' : 'bg-surface-700'
        }`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${
            checked ? 'left-5' : 'left-0.5'
          }`}
        />
      </button>
    </div>
  )
}

/**
 * Notification preferences panel — rendered on the Settings page.
 * Preferences are persisted in `NotificationsContext` (localStorage) and
 * immediately gate the live WebSocket → bell bridge.
 */
export function NotificationPreferences() {
  const { preferences, updatePreferences, resetPreferences, unreadCount, notify, clearAll } =
    useNotifications()

  const set = (patch: Partial<Prefs>) => updatePreferences(patch)

  const kindRows: Array<{ kind: NotificationKind; label: string; description: string; icon: ReactNode }> = [
    {
      kind: 'pipeline',
      label: 'Pipeline events',
      description: 'Failures, completions and step results',
      icon: <GitBranch className="w-4 h-4 text-primary-400" />,
    },
    {
      kind: 'node',
      label: 'Node events',
      description: 'Nodes joining, re-registering or dropping offline',
      icon: <Server className="w-4 h-4 text-success-400" />,
    },
    {
      kind: 'install',
      label: 'Marketplace installs',
      description: 'Modules installed or removed from Nectar',
      icon: <PackageCheck className="w-4 h-4 text-accent-400" />,
    },
  ]

  return (
    <Card className="scroll-mt-20" >
      <div id="notifications" />
      <CardHeader>
        <div className="flex items-center gap-2">
          {preferences.enabled ? (
            <Bell className="w-4 h-4 text-surface-400" />
          ) : (
            <BellOff className="w-4 h-4 text-warning-400" />
          )}
          <CardTitle>Notifications</CardTitle>
        </div>
        <span className="text-xs text-surface-500">{unreadCount} unread</span>
      </CardHeader>

      <ToggleRow
        label="Enable notifications"
        description="Master switch for the notification bell and live alerts"
        icon={<Bell className="w-4 h-4 text-surface-400" />}
        checked={preferences.enabled}
        onChange={(next) => set({ enabled: next })}
      />

      {kindRows.map((row) => (
        <ToggleRow
          key={row.kind}
          label={row.label}
          description={row.description}
          icon={row.icon}
          checked={preferences[row.kind]}
          disabled={!preferences.enabled}
          onChange={(next) => set({ [row.kind]: next } as Partial<Prefs>)}
        />
      ))}

      <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-surface-800">
        <Button
          variant="secondary"
          size="sm"
          onClick={() =>
            notify('pipeline', 'Test notification', 'This is what a pipeline alert looks like.')
          }
          disabled={!preferences.enabled || !preferences.pipeline}
        >
          <Send className="w-3.5 h-3.5" />
          Send test alert
        </Button>
        <Button variant="ghost" size="sm" onClick={resetPreferences}>
          <RotateCcw className="w-3.5 h-3.5" />
          Reset preferences
        </Button>
        <Button variant="ghost" size="sm" onClick={clearAll} disabled={unreadCount === 0}>
          Clear inbox
        </Button>
      </div>
    </Card>
  )
}
