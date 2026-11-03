import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useRealtime } from '@/context/RealtimeContext'
import type { PipelineEvent } from '@/hooks/useWebSocket'

export type NotificationKind = 'pipeline' | 'node' | 'install'

export interface AppNotification {
  id: string
  kind: NotificationKind
  title: string
  description: string
  createdAt: number
  read: boolean
}

/** User-tunable delivery preferences, persisted per browser. */
export interface NotificationPreferences {
  /** Master switch — off silences every category at once. */
  enabled: boolean
  pipeline: boolean
  node: boolean
  install: boolean
}

interface NotificationsState {
  notifications: AppNotification[]
  unreadCount: number
  preferences: NotificationPreferences
  markAllRead: () => void
  markRead: (id: string) => void
  remove: (id: string) => void
  /** Raw insert — always stores, ignoring preferences. */
  addNotification: (notification: Omit<AppNotification, 'read'>) => void
  /** Preference-aware insert — used by live events and user actions. */
  notify: (kind: NotificationKind, title: string, description: string) => void
  clearAll: () => void
  updatePreferences: (patch: Partial<NotificationPreferences>) => void
  resetPreferences: () => void
}

const STORAGE_KEY = 'supra-codex:notifications'
const PREFS_KEY = 'supra-codex:notification-preferences'
const MAX_NOTIFICATIONS = 40

export const defaultPreferences: NotificationPreferences = {
  enabled: true,
  pipeline: true,
  node: true,
  install: true,
}

const seedNotifications: Omit<AppNotification, 'read'>[] = [
  {
    id: 'seed-pipeline-complete',
    kind: 'pipeline',
    title: 'Price Monitor pipeline completed',
    description: 'E-commerce Price Monitor finished 1,240 tasks without errors.',
    createdAt: Date.now() - 2 * 60 * 1000,
  },
  {
    id: 'seed-node-online',
    kind: 'node',
    title: 'Node us-west-2 came online',
    description: 'Oregon, USA · 32 vCPU · 48 GB RAM',
    createdAt: Date.now() - 15 * 60 * 1000,
  },
  {
    id: 'seed-install',
    kind: 'install',
    title: 'Module installed',
    description: 'Lead Gen Scraper v1.4 installed from the Nectar Marketplace.',
    createdAt: Date.now() - 60 * 60 * 1000,
  },
  {
    id: 'seed-pipeline-failed',
    kind: 'pipeline',
    title: 'Pipeline "Competitor Intel" failed',
    description: 'Parsing error on step 3 — enrichment skipped.',
    createdAt: Date.now() - 3 * 60 * 60 * 1000,
  },
]

function loadInitial(): AppNotification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as AppNotification[]
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    // Ignore corrupted storage and fall back to seeds.
  }
  return seedNotifications.map((n) => ({ ...n, read: false }))
}

function loadPreferences(): NotificationPreferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<NotificationPreferences>
      return { ...defaultPreferences, ...parsed }
    }
  } catch {
    // Ignore corrupted storage and fall back to defaults.
  }
  return { ...defaultPreferences }
}

/** Stable identity for a live WS event, so replays are only processed once. */
function eventKey(event: PipelineEvent): string {
  return `${event.timestamp}:${event.type}:${event.pipelineId}`
}

/** Map a live pipeline event onto a bell entry (or `null` if not noteworthy). */
function eventToNotification(
  event: PipelineEvent,
): { kind: NotificationKind; title: string; description: string } | null {
  const payload = event.payload ?? {}
  const pipelineRef = event.pipelineId ? `Pipeline ${event.pipelineId.slice(0, 8)}` : 'The engine'

  switch (event.type) {
    case 'error':
      return {
        kind: 'pipeline',
        title: 'Pipeline failed',
        description: `${pipelineRef} · ${String(payload.step ?? 'unknown step')}: ${String(
          payload.error ?? 'unknown error',
        )}`.slice(0, 160),
      }
    case 'result':
      return {
        kind: 'pipeline',
        title: 'Pipeline step completed',
        description: `${pipelineRef} · ${String(payload.step ?? 'result')} finished successfully`,
      }
    case 'status': {
      const nodeEvent = payload.event
      if (nodeEvent === 'node_registered' || nodeEvent === 'node_re-registered') {
        const hostname = String(payload.hostname ?? payload.node_id ?? 'unknown')
        return {
          kind: 'node',
          title: `Node ${hostname} came online`,
          description: `Registered with the cluster as ${String(payload.node_id ?? hostname)}`,
        }
      }
      return null
    }
    default:
      return null
  }
}

const NotificationsContext = createContext<NotificationsState | undefined>(undefined)

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>(loadInitial)
  const [preferences, setPreferences] = useState<NotificationPreferences>(loadPreferences)
  const { events } = useRealtime()

  // Preferences are read inside async-ish callbacks; keep a live mirror.
  const preferencesRef = useRef(preferences)
  preferencesRef.current = preferences

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications))
    } catch {
      // Ignore write failures (private mode / quota).
    }
  }, [notifications])

  useEffect(() => {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(preferences))
    } catch {
      // Ignore write failures (private mode / quota).
    }
  }, [preferences])

  const addNotification = useCallback((notification: Omit<AppNotification, 'read'>) => {
    setNotifications((prev) => {
      if (prev.some((n) => n.id === notification.id)) return prev
      return [{ ...notification, read: false }, ...prev].slice(0, MAX_NOTIFICATIONS)
    })
  }, [])

  const notify = useCallback(
    (kind: NotificationKind, title: string, description: string) => {
      const prefs = preferencesRef.current
      if (!prefs.enabled || !prefs[kind]) return
      addNotification({
        id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        kind,
        title,
        description,
        createdAt: Date.now(),
      })
    },
    [addNotification],
  )

  // ── Live bridge: turn noteworthy WebSocket events into bell entries ──
  const processedEvents = useRef<Set<string>>(new Set())
  useEffect(() => {
    if (events.length === 0) return
    const fresh = events.filter((e) => !processedEvents.current.has(eventKey(e)))
    if (fresh.length === 0) return

    // `events` is newest-first; apply oldest-first so ordering stays natural.
    const ordered = [...fresh].reverse()
    const prefs = preferencesRef.current
    const additions: AppNotification[] = []

    for (const event of ordered) {
      processedEvents.current.add(eventKey(event))
      if (!prefs.enabled) continue
      const mapped = eventToNotification(event)
      if (!mapped || !prefs[mapped.kind]) continue
      additions.push({
        id: `ws-${event.timestamp}-${event.type}-${event.pipelineId}`,
        kind: mapped.kind,
        title: mapped.title,
        description: mapped.description,
        createdAt: Date.parse(event.timestamp) || Date.now(),
        read: false,
      })
    }

    if (additions.length === 0) return
    setNotifications((prev) => {
      const seen = new Set(prev.map((n) => n.id))
      const unique = additions.filter((n) => !seen.has(n.id))
      if (unique.length === 0) return prev
      return [...unique.reverse(), ...prev].slice(0, MAX_NOTIFICATIONS)
    })
  }, [events])

  const markAllRead = useCallback(() => {
    setNotifications((prev) => (prev.some((n) => !n.read) ? prev.map((n) => ({ ...n, read: true })) : prev))
  }, [])

  const markRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id && !n.read ? { ...n, read: true } : n)),
    )
  }, [])

  const remove = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setNotifications([])
  }, [])

  const updatePreferences = useCallback((patch: Partial<NotificationPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...patch }))
  }, [])

  const resetPreferences = useCallback(() => {
    setPreferences({ ...defaultPreferences })
  }, [])

  const unreadCount = useMemo(() => notifications.filter((n) => !n.read).length, [notifications])

  const value = useMemo<NotificationsState>(
    () => ({
      notifications,
      unreadCount,
      preferences,
      markAllRead,
      markRead,
      remove,
      addNotification,
      notify,
      clearAll,
      updatePreferences,
      resetPreferences,
    }),
    [
      notifications,
      unreadCount,
      preferences,
      markAllRead,
      markRead,
      remove,
      addNotification,
      notify,
      clearAll,
      updatePreferences,
      resetPreferences,
    ],
  )

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext)
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider')
  return ctx
}
