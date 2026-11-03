import { Activity, CheckCircle2, GitBranch, Server, Wifi, WifiOff, Zap } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardValue, CardLabel } from '@/components/Card'
import { ActivityFeed } from '@/components/ActivityFeed'
import { useActivityFeed } from '@/hooks/useActivityFeed'

function utilizationColor(value: number): string {
  if (value >= 85) return 'bg-danger-500'
  if (value >= 60) return 'bg-warning-500'
  return 'bg-success-500'
}

function NodeRow({
  name,
  region,
  cpu,
  mem,
  status,
}: {
  name: string
  region: string
  cpu: number
  mem: number
  status: 'online' | 'offline'
}) {
  const online = status === 'online'
  return (
    <div className="py-3 border-b border-surface-800 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
              online ? 'bg-success-400' : 'bg-surface-600'
            }`}
          />
          <span className="text-sm text-surface-200 truncate">{name}</span>
          <span className="text-xs text-surface-600 truncate">{region}</span>
        </div>
        <span className="text-xs text-surface-500 whitespace-nowrap">{online ? 'online' : 'offline'}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="flex justify-between text-[10px] text-surface-600 mb-1">
            <span>CPU</span>
            <span>{online ? `${cpu}%` : '—'}</span>
          </div>
          <div className="h-1 rounded-full bg-surface-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${online ? utilizationColor(cpu) : 'bg-surface-700'}`}
              style={{ width: online ? `${Math.min(cpu, 100)}%` : '0%' }}
            />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-[10px] text-surface-600 mb-1">
            <span>MEM</span>
            <span>{online ? `${mem}%` : '—'}</span>
          </div>
          <div className="h-1 rounded-full bg-surface-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${online ? utilizationColor(mem) : 'bg-surface-700'}`}
              style={{ width: online ? `${Math.min(mem, 100)}%` : '0%' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const feed = useActivityFeed(8)
  const { pipelines, nodes, loading, error, isConnected, lastUpdated, refresh } = feed

  const onlineNodes = nodes.filter((n) => n.status === 'online').length
  const runningPipelines = pipelines.filter((p) => p.status === 'running').length
  const tasksInFlight = pipelines.reduce((sum, p) => sum + p.tasks, 0)
  const hasData = !loading && !error

  const stats = [
    {
      icon: Server,
      value: hasData ? String(onlineNodes) : '—',
      label: 'Active Nodes',
      meta: `${nodes.length} registered`,
      color: 'text-primary-400',
    },
    {
      icon: GitBranch,
      value: hasData ? String(runningPipelines) : '—',
      label: 'Running Pipelines',
      meta: `${pipelines.length} defined`,
      color: 'text-accent-400',
    },
    {
      icon: Zap,
      value: hasData ? tasksInFlight.toLocaleString() : '—',
      label: 'Tasks In Flight',
      meta: 'across all pipelines',
      color: 'text-warning-400',
    },
    {
      icon: isConnected ? Wifi : WifiOff,
      value: isConnected ? 'Live' : 'Offline',
      label: 'Event Stream',
      meta: isConnected ? 'WebSocket connected' : 'REST snapshot only',
      color: isConnected ? 'text-success-400' : 'text-danger-400',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-surface-500 mt-1">Overview of your Supra-Codex infrastructure</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-surface-500">
          {isConnected ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
              Streaming live events
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5" />
              Reconnecting to event stream…
            </>
          )}
        </div>
      </div>

      {/* Stats grid — driven by the API snapshot from useActivityFeed */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} hover>
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <span className={`text-xs font-semibold ${stat.color}`}>{stat.meta}</span>
            </CardHeader>
            <CardValue>{stat.value}</CardValue>
            <CardLabel>{stat.label}</CardLabel>
          </Card>
        ))}
      </div>

      {/* Activity & node health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityFeed feed={feed} />

        <Card>
          <CardHeader>
            <CardTitle>Node Health</CardTitle>
            <button
              onClick={() => void refresh()}
              className="flex items-center gap-1.5 text-xs text-surface-500 hover:text-surface-300 transition-colors"
            >
              <Activity className={`w-3.5 h-3.5 ${loading ? 'animate-pulse' : ''}`} />
              {lastUpdated > 0 ? `${onlineNodes}/${nodes.length} online` : 'Loading'}
            </button>
          </CardHeader>

          {nodes.length === 0 ? (
            <div className="py-10 text-center">
              <Server className="w-8 h-8 text-surface-700 mx-auto mb-2" />
              <p className="text-sm text-surface-400">No nodes registered</p>
              <p className="text-xs text-surface-600 mt-1">
                Register a node to start distributing workloads.
              </p>
            </div>
          ) : (
            <div>
              {nodes.slice(0, 6).map((node) => (
                <NodeRow
                  key={node.name}
                  name={node.name}
                  region={node.region}
                  cpu={node.cpu}
                  mem={node.mem}
                  status={node.status}
                />
              ))}
            </div>
          )}

          {pipelines.length > 0 && (
            <div className="mt-4 pt-4 border-t border-surface-800">
              <p className="text-xs font-semibold text-surface-300 mb-2">Pipeline status</p>
              <div className="grid grid-cols-2 gap-2">
                {(['running', 'paused', 'idle', 'error'] as const).map((status) => {
                  const count = pipelines.filter((p) => p.status === status).length
                  const tone =
                    status === 'running'
                      ? 'text-success-400'
                      : status === 'paused'
                        ? 'text-warning-400'
                        : status === 'error'
                          ? 'text-danger-400'
                          : 'text-surface-500'
                  return (
                    <div
                      key={status}
                      className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-surface-800/50"
                    >
                      <span className="text-xs text-surface-400 capitalize">{status}</span>
                      <span className={`text-xs font-semibold ${tone}`}>{count}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 text-[11px] text-warning-400">
              <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span className="truncate">API unreachable — showing last known state.</span>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
