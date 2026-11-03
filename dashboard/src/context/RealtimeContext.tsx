import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useWebSocket, type ConnectionStatus, type PipelineEvent } from '@/hooks/useWebSocket'

/**
 * Single shared WebSocket connection to the Supra-Codex API.
 *
 * The dashboard had several places that wanted live pipeline events
 * (activity feed, notification bell, live view). Opening one socket per
 * consumer wastes connections and desynchronises the streams, so the
 * provider owns the connection and every consumer subscribes to the
 * same ordered event buffer through `useRealtime()`.
 */

const MAX_BUFFERED_EVENTS = 50

interface RealtimeState {
  /** Raw socket lifecycle state. */
  status: ConnectionStatus
  isConnected: boolean
  /** Most recent first. Capped so the buffer can never grow unbounded. */
  events: PipelineEvent[]
  /** Manual reconnect — used by the "Retry" affordances in the UI. */
  reconnect: () => void
}

const RealtimeContext = createContext<RealtimeState | undefined>(undefined)

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<PipelineEvent[]>([])

  // Must be referentially stable: `useWebSocket` rebuilds its connect
  // callback (and therefore reconnects) whenever this identity changes.
  const handleMessage = useCallback((event: PipelineEvent) => {
    setEvents((prev) => [event, ...prev].slice(0, MAX_BUFFERED_EVENTS))
  }, [])

  const { status, isConnected, connect } = useWebSocket({ onMessage: handleMessage })

  const value = useMemo<RealtimeState>(
    () => ({ status, isConnected, events, reconnect: connect }),
    [status, isConnected, events, connect],
  )

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>
}

export function useRealtime(): RealtimeState {
  const ctx = useContext(RealtimeContext)
  if (!ctx) throw new Error('useRealtime must be used within RealtimeProvider')
  return ctx
}
