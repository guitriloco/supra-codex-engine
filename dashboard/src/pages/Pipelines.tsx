import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { useNavigate } from 'react-router-dom'
import { GitBranch, Play, Pause, MoreHorizontal, Plus, Radio } from 'lucide-react'

const pipelines = [
  { name: 'E-commerce Price Monitor', status: 'running', nodes: 3, tasks: 1240, uptime: '99.8%' },
  { name: 'Lead Generation Scraper', status: 'running', nodes: 2, tasks: 892, uptime: '97.2%' },
  { name: 'Competitor Intelligence', status: 'paused', nodes: 4, tasks: 445, uptime: '—' },
  { name: 'Data Enrichment Pipeline', status: 'running', nodes: 5, tasks: 2103, uptime: '99.9%' },
  { name: 'Social Media Monitor', status: 'idle', nodes: 1, tasks: 0, uptime: '—' },
]

const statusBadge = (status: string) => {
  const colors: Record<string, string> = {
    running: 'bg-success-500/10 text-success-400 border-success-500/20',
    paused: 'bg-warning-500/10 text-warning-400 border-warning-500/20',
    idle: 'bg-surface-800 text-surface-500 border-surface-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${colors[status]}`}>
      {status}
    </span>
  )
}

export default function Pipelines() {
  const navigate = useNavigate()
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Pipelines</h1>
          <p className="text-sm text-surface-500 mt-1">Manage your automation workflows</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate('/pipelines/live')}>
            <Radio className="w-4 h-4" />
            Live View
          </Button>
          <Button>
            <Plus className="w-4 h-4" />
            New Pipeline
          </Button>
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-800 text-xs text-surface-500 uppercase tracking-wider">
              <th className="text-left px-5 py-3 font-medium">Pipeline</th>
              <th className="text-left px-5 py-3 font-medium">Status</th>
              <th className="text-left px-5 py-3 font-medium">Nodes</th>
              <th className="text-left px-5 py-3 font-medium">Tasks</th>
              <th className="text-left px-5 py-3 font-medium">Uptime</th>
              <th className="text-right px-5 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800">
            {pipelines.map((p) => (
              <tr key={p.name} className="hover:bg-surface-800/30 transition-colors">
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary-600/10 flex items-center justify-center">
                      <GitBranch className="w-4 h-4 text-primary-400" />
                    </div>
                    <span className="text-sm font-medium text-surface-200">{p.name}</span>
                  </div>
                </td>
                <td className="px-5 py-4">{statusBadge(p.status)}</td>
                <td className="px-5 py-4 text-sm text-surface-400">{p.nodes}</td>
                <td className="px-5 py-4 text-sm text-surface-400">{p.tasks.toLocaleString()}</td>
                <td className="px-5 py-4 text-sm text-surface-400">{p.uptime}</td>
                <td className="px-5 py-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button className="p-2 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-colors">
                      {p.status === 'running' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                    <button className="p-2 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-colors">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}