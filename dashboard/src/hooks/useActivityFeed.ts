import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRealtime } from '@/context/RealtimeContext'
import {
  eventToActivity,
  snapshotActivity,
  type ActivityItem,
} from '@/lib/activity'
import { listNodes, listPipelines, type Node, type Pipeline } from '@/services/api'

const REFRESH_INTERVAL_MS = 30_000

export interface ActivityFeedData {
  items: ActivityItem[]
  loading: boolean
  error: string | null
  isConnected: boolean
  /** Epoch millis of the last successful REST snapshot. */
  lastUpdated: number
  pipelines: Pipeline[]
  nodes: Node[]
  refresh: () => Promise<void>
}

/**
 * Combines a REST snapshot (pipelines + nodes) with the live WebSocket
 * event stream into one ordered activity feed. Live events lead, the
 * snapshot fills in current state, and the snapshot is re-polled every
 * 30s so rows don't go stale when nothing is running.
 */
export function useActivityFeed(limit = 8): ActivityFeedData {
  const { events, isConnected } = useRealtime()
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [nodes, setNodes] = useState<Node[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState(0)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextPipelines, nextNodes] = await Promise.all([listPipelines(), listNodes()])
      setPipelines(nextPipelines)
      setNodes(nextNodes)
      setLastUpdated(Date.now())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load activity')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = setInterval(() => {
      void refresh()
    }, REFRESH_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [refresh])

  const items = useMemo<ActivityItem[]>(() => {
    const live: ActivityItem[] = []
    const seen = new Set<string>()
    for (const event of events) {
      const item = eventToActivity(event)
      if (!item || seen.has(item.id)) continue
      seen.add(item.id)
      live.push(item)
    }
    // Live events are already newest-first; snapshot rows follow in API order.
    return [...live, ...snapshotActivity(pipelines, nodes)].slice(0, limit)
  }, [events, pipelines, nodes, limit])

  return { items, loading, error, isConnected, lastUpdated, pipelines, nodes, refresh }
}
