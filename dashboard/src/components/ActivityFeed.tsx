import {
  Activity,
  AlertTriangle,
  GitBranch,
  Inbox,
  PackageCheck,
  RefreshCw,
  Server,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { Card, CardHeader, CardTitle } from '@/components/Card'
import { Button } from '@/components/Button'
import type { ActivityFeedData } from '@/hooks/useActivityFeed'
import { toneLabel, type ActivityItem } from '@/lib/activity'
import { timeAgo } from '@/lib/time'

const kindIcons = {
  pipeline: GitBranch,
  node: Server,
  install: PackageCheck,
  system: Activity,
} as const

const toneColors = {
  ok: 'text-success-400',
  warn: 'text-warning-400',
  error: 'text-danger-400',
  idle: 'text-surface-500',
} as const

function ActivityRow({ item }: { item: ActivityItem }) {
  const Icon = kindIcons[item.kind]
  return (
    <div className="flex items-center gap-3 py-3 border-b border-surface-800 last:border-0">
      <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
        <Icon className={`w-4 h-4 ${toneColors[item.tone]}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-surface-200 truncate">{item.title}</p>
        <p className="text-xs text-surface-500 truncate">{item.detail}</p>
      </div>
      {item.timestamp > 0 ? (
        <span className="text-[10px] text-surface-600 whitespace-nowrap">{timeAgo(item.timestamp)}</span>
      ) : item.live ? (
        <span className="flex items-center gap-1 text-[10px] text-success-400 whitespace-nowrap">
          <span className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
          {toneLabel(item)}
        </span>
      ) : (
        <span className="text-[10px] text-surface-600 whitespace-nowrap">{toneLabel(item)}</span>
      )}
    </div>
  )
}

function SkeletonRows() {
  return (
    <div className="space-y-1">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 py-3 border-b border-surface-800 last:border-0 animate-pulse"
        >
          <div className="w-8 h-8 rounded-lg bg-surface-800 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 rounded bg-surface-800 w-3/4" />
            <div className="h-2.5 rounded bg-surface-800 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function ActivityFeed({ feed }: { feed: ActivityFeedData }) {
  const { items, loading, error, isConnected, lastUpdated, refresh } = feed

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>Activity Feed</CardTitle>
          <span
            className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-md border ${
              isConnected
                ? 'text-success-400 border-success-500/30 bg-success-500/10'
                : 'text-surface-500 border-surface-700 bg-surface-800/50'
            }`}
            title={isConnected ? 'WebSocket connected' : 'WebSocket disconnected — showing REST snapshot'}
          >
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>
        <button
          onClick={() => void refresh()}
          className="flex items-center gap-1.5 text-xs text-surface-500 hover:text-surface-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </CardHeader>

      {loading && items.length === 0 ? (
        <SkeletonRows />
      ) : error && items.length === 0 ? (
        <div className="py-8 text-center">
          <AlertTriangle className="w-8 h-8 text-warning-400 mx-auto mb-2" />
          <p className="text-sm text-surface-300">Couldn't reach the API</p>
          <p className="text-xs text-surface-600 mt-1 mb-4 max-w-xs mx-auto truncate">{error}</p>
          <Button variant="secondary" size="sm" onClick={() => void refresh()}>
            <RefreshCw className="w-4 h-4" />
            Retry
          </Button>
        </div>
      ) : items.length === 0 ? (
        <div className="py-10 text-center">
          <Inbox className="w-8 h-8 text-surface-700 mx-auto mb-2" />
          <p className="text-sm text-surface-400">No activity yet</p>
          <p className="text-xs text-surface-600 mt-1">
            Start a pipeline or register a node to see it here.
          </p>
        </div>
      ) : (
        <>
          <div>
            {items.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </div>
          {error && (
            <p className="mt-3 text-[10px] text-warning-400">
              Live data unavailable — showing the last known state.
            </p>
          )}
          {!error && lastUpdated > 0 && (
            <p className="mt-3 text-[10px] text-surface-600">
              Snapshot updated {timeAgo(lastUpdated)}
            </p>
          )}
        </>
      )}
    </Card>
  )
}
