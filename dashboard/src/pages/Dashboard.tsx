import { Card, CardHeader, CardTitle, CardValue, CardLabel } from '@/components/Card'
import { Activity, GitBranch, Server, Zap, TrendingUp, Globe } from 'lucide-react'

export default function Dashboard() {
  const stats = [
    { icon: Server, value: '12', label: 'Active Nodes', color: 'text-primary-400' },
    { icon: GitBranch, value: '47', label: 'Active Pipelines', color: 'text-accent-400' },
    { icon: Activity, value: '99.2%', label: 'Uptime', color: 'text-success-400' },
    { icon: Zap, value: '2,847', label: 'Tasks Today', color: 'text-warning-400' },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-surface-500 mt-1">Overview of your Supra-Codex infrastructure</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} hover>
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <span className={`text-xs font-semibold ${stat.color}`}>Live</span>
            </CardHeader>
            <CardValue>{stat.value}</CardValue>
            <CardLabel>{stat.label}</CardLabel>
          </Card>
        ))}
      </div>

      {/* Activity & Recent pipelines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <span className="text-xs text-surface-500">Last 24h</span>
          </CardHeader>
          <div className="space-y-3">
            {[
              { action: 'Price monitoring pipeline completed', time: '2 min ago', icon: TrendingUp, color: 'text-success-400' },
              { action: 'Node us-west-2 came online', time: '15 min ago', icon: Server, color: 'text-primary-400' },
              { action: 'Lead gen scraper processed 1,240 records', time: '1h ago', icon: Globe, color: 'text-accent-400' },
              { action: 'Pipeline "Competitor Intel" failed', time: '3h ago', icon: Activity, color: 'text-danger-400' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-surface-800 last:border-0">
                <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center">
                  <item.icon className={`w-4 h-4 ${item.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-surface-200 truncate">{item.action}</p>
                </div>
                <span className="text-xs text-surface-500 whitespace-nowrap">{item.time}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Pipeline performance */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Performance</CardTitle>
            <span className="text-xs text-surface-500">This week</span>
          </CardHeader>
          <div className="space-y-4">
            {[
              { name: 'Price Monitor', success: 98, tasks: 1240 },
              { name: 'Lead Generator', success: 87, tasks: 892 },
              { name: 'Competitor Intel', success: 76, tasks: 445 },
              { name: 'Data Enrichment', success: 94, tasks: 2103 },
            ].map((pipeline) => (
              <div key={pipeline.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-surface-300">{pipeline.name}</span>
                  <span className="text-surface-500">{pipeline.success}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      pipeline.success >= 95 ? 'bg-success-500' : pipeline.success >= 85 ? 'bg-warning-500' : 'bg-danger-500'
                    }`}
                    style={{ width: `${pipeline.success}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}