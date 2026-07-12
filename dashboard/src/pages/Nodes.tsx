import { Card, CardHeader, CardValue, CardLabel } from '@/components/Card'
import { Server, Globe, Wifi, WifiOff, HardDrive } from 'lucide-react'

const nodes = [
  { name: 'us-west-2', region: 'Oregon, USA', status: 'online', cpu: 32, mem: 48, tasks: 124 },
  { name: 'eu-central-1', region: 'Frankfurt, DE', status: 'online', cpu: 18, mem: 22, tasks: 87 },
  { name: 'ap-southeast-1', region: 'Singapore', status: 'online', cpu: 45, mem: 61, tasks: 203 },
  { name: 'sa-east-1', region: 'São Paulo, BR', status: 'offline', cpu: 0, mem: 0, tasks: 0 },
  { name: 'us-east-1', region: 'Virginia, USA', status: 'online', cpu: 27, mem: 34, tasks: 156 },
]

export default function Nodes() {
  const online = nodes.filter((n) => n.status === 'online').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Cluster Nodes</h1>
        <p className="text-sm text-surface-500 mt-1">Distributed compute infrastructure</p>
      </div>

      {/* Cluster summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-primary-600/10 flex items-center justify-center">
              <Server className="w-5 h-5 text-primary-400" />
            </div>
          </CardHeader>
          <CardValue>{nodes.length}</CardValue>
          <CardLabel>Total Nodes</CardLabel>
        </Card>
        <Card>
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-success-500/10 flex items-center justify-center">
              <Wifi className="w-5 h-5 text-success-400" />
            </div>
          </CardHeader>
          <CardValue>{online}</CardValue>
          <CardLabel>Online Nodes</CardLabel>
        </Card>
        <Card>
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-accent-400" />
            </div>
          </CardHeader>
          <CardValue>570</CardValue>
          <CardLabel>Total Active Tasks</CardLabel>
        </Card>
      </div>

      {/* Node list */}
      <Card className="p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-800 text-xs text-surface-500 uppercase tracking-wider">
              <th className="text-left px-5 py-3 font-medium">Node</th>
              <th className="text-left px-5 py-3 font-medium">Region</th>
              <th className="text-left px-5 py-3 font-medium">Status</th>
              <th className="text-left px-5 py-3 font-medium">CPU</th>
              <th className="text-left px-5 py-3 font-medium">Memory</th>
              <th className="text-right px-5 py-3 font-medium">Tasks</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800">
            {nodes.map((node) => (
              <tr key={node.name} className="hover:bg-surface-800/30 transition-colors">
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center">
                      <Server className="w-4 h-4 text-surface-400" />
                    </div>
                    <span className="text-sm font-medium text-surface-200">{node.name}</span>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center gap-2 text-sm text-surface-400">
                    <Globe className="w-3.5 h-3.5" />
                    {node.region}
                  </div>
                </td>
                <td className="px-5 py-4">
                  {node.status === 'online' ? (
                    <span className="flex items-center gap-1.5 text-xs text-success-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-success-400" />
                      Online
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-xs text-surface-500">
                      <WifiOff className="w-3.5 h-3.5" />
                      Offline
                    </span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-20 h-1.5 rounded-full bg-surface-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          node.cpu > 80 ? 'bg-danger-500' : node.cpu > 60 ? 'bg-warning-500' : 'bg-success-500'
                        }`}
                        style={{ width: `${node.cpu}%` }}
                      />
                    </div>
                    <span className="text-xs text-surface-500">{node.cpu}%</span>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-20 h-1.5 rounded-full bg-surface-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          node.mem > 80 ? 'bg-danger-500' : node.mem > 60 ? 'bg-warning-500' : 'bg-primary-500'
                        }`}
                        style={{ width: `${node.mem}%` }}
                      />
                    </div>
                    <span className="text-xs text-surface-500">{node.mem}%</span>
                  </div>
                </td>
                <td className="px-5 py-4 text-right text-sm text-surface-400">{node.tasks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}