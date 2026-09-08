import { Card, CardHeader, CardTitle } from '@/components/Card'
import { Button } from '@/components/Button'
import { useAuth } from '@/context/AuthContext'
import { Link } from 'react-router-dom'
import {
  CreditCard,
  ArrowUpRight,
  Download,
  CheckCircle,
  Clock,
  FileText,
  AlertCircle,
} from 'lucide-react'

interface Invoice {
  id: string
  date: string
  amount: string
  status: 'paid' | 'pending' | 'failed'
}

const planConfig = {
  free: {
    label: 'Free',
    price: '$0/mo',
    nodes: 3,
    pipelinesPerMonth: 5,
    support: 'Community',
    color: 'text-surface-400',
    bg: 'bg-surface-800',
    border: 'border-surface-700',
  },
  pro: {
    label: 'Pro',
    price: '$29/mo',
    nodes: 25,
    pipelinesPerMonth: Infinity,
    support: 'Priority',
    color: 'text-primary-400',
    bg: 'bg-primary-600/10',
    border: 'border-primary-600/20',
  },
  enterprise: {
    label: 'Enterprise',
    price: 'Custom',
    nodes: Infinity,
    pipelinesPerMonth: Infinity,
    support: 'Dedicated',
    color: 'text-accent-400',
    bg: 'bg-accent-600/10',
    border: 'border-accent-600/20',
  },
}

const invoices: Invoice[] = [
  { id: 'INV-2026-07', date: 'Jul 1, 2026', amount: '$29.00', status: 'paid' },
  { id: 'INV-2026-06', date: 'Jun 1, 2026', amount: '$29.00', status: 'paid' },
  { id: 'INV-2026-05', date: 'May 1, 2026', amount: '$29.00', status: 'paid' },
  { id: 'INV-2026-04', date: 'Apr 1, 2026', amount: '$29.00', status: 'paid' },
]

const statusConfig = {
  paid: { icon: CheckCircle, class: 'text-success-400', label: 'Paid' },
  pending: { icon: Clock, class: 'text-warning-400', label: 'Pending' },
  failed: { icon: AlertCircle, class: 'text-danger-400', label: 'Failed' },
}

export default function Billing() {
  const { user } = useAuth()
  const tier = user?.tier ?? 'free'
  const plan = planConfig[tier]

  const usedNodes = tier === 'free' ? 3 : tier === 'pro' ? 18 : 42
  const maxNodes = tier === 'free' ? 3 : tier === 'pro' ? 25 : 100
  const nodePercentage = Math.min((usedNodes / maxNodes) * 100, 100)

  const usedPipelines = tier === 'free' ? 5 : tier === 'pro' ? 247 : 1023
  const maxPipelines = tier === 'free' ? 5 : Infinity
  const pipelinePercentage = tier === 'free' ? 100 : Math.min((usedPipelines / (maxPipelines as number || 1000)) * 100, 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Billing & Subscription</h1>
          <p className="text-sm text-surface-500 mt-1">Manage your plan, payment method, and invoices</p>
        </div>
        <Link to="/pricing">
          <Button variant="secondary" size="md">
            <ArrowUpRight className="w-4 h-4" />
            View Plans
          </Button>
        </Link>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg ${plan.bg} ${plan.border} border flex items-center justify-center`}>
              <CreditCard className={`w-5 h-5 ${plan.color}`} />
            </div>
            <div>
              <CardTitle>Current Plan</CardTitle>
              <p className="text-xs text-surface-500">{plan.price} · Billed monthly</p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-md text-xs font-medium border ${plan.bg} ${plan.color} ${plan.border}`}>
            {plan.label}
          </span>
        </CardHeader>

        {/* Usage Bars */}
        <div className="space-y-4 mt-2">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-surface-400">Nodes</span>
              <span className="text-xs text-surface-500">
                {usedNodes} / {maxNodes === Infinity ? '∞' : maxNodes}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-surface-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  nodePercentage >= 90 ? 'bg-danger-400' : nodePercentage >= 70 ? 'bg-warning-400' : 'bg-primary-400'
                }`}
                style={{ width: `${nodePercentage}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-surface-400">Pipelines this month</span>
              <span className="text-xs text-surface-500">
                {usedPipelines} / {maxPipelines === Infinity ? '∞' : maxPipelines}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-surface-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  pipelinePercentage >= 90 ? 'bg-danger-400' : pipelinePercentage >= 70 ? 'bg-warning-400' : 'bg-primary-400'
                }`}
                style={{ width: `${pipelinePercentage}%` }}
              />
            </div>
          </div>
        </div>

        <div className="mt-5 pt-4 border-t border-surface-800 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-surface-500">
            <span className="font-medium text-surface-300">{plan.support}</span> support
          </div>
          <span className="text-surface-700">·</span>
          <div className="flex items-center gap-2 text-xs text-surface-500">
            {maxNodes === Infinity ? 'Unlimited' : maxNodes} nodes
          </div>
          <span className="text-surface-700">·</span>
          <div className="flex items-center gap-2 text-xs text-surface-500">
            {maxPipelines === Infinity ? 'Unlimited' : `${maxPipelines}`} pipeline{maxPipelines === 1 ? '' : 's'}/mo
          </div>
        </div>

        {tier !== 'enterprise' && (
          <div className="mt-4 flex flex-col sm:flex-row gap-3">
            <Link to="/pricing">
              <Button variant="primary" size="md">
                Upgrade Plan
              </Button>
            </Link>
            <Button variant="ghost" size="md">
              Cancel Subscription
            </Button>
          </div>
        )}
        {tier === 'enterprise' && (
          <p className="mt-4 text-xs text-surface-500">
            Enterprise plans are managed through your account representative.{' '}
            <a href="mailto:sales@supracodex.io" className="text-primary-400 hover:text-primary-300">
              Contact sales
            </a>{' '}
            for changes.
          </p>
        )}
      </Card>

      {/* Payment Method */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Method</CardTitle>
        </CardHeader>
        <div className="flex items-center gap-4">
          <div className="w-12 h-8 rounded border border-surface-700 bg-surface-800 flex items-center justify-center">
            <CreditCard className="w-5 h-5 text-surface-500" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-surface-300 font-mono">•••• •••• •••• 4242</p>
            <p className="text-xs text-surface-500">Expires 12/2028</p>
          </div>
          <Button variant="secondary" size="sm">
            Update
          </Button>
        </div>
      </Card>

      {/* Invoice History */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-800/50 text-left">
                <th className="pb-3 text-xs font-medium text-surface-500 uppercase tracking-wider">Invoice</th>
                <th className="pb-3 text-xs font-medium text-surface-500 uppercase tracking-wider">Date</th>
                <th className="pb-3 text-xs font-medium text-surface-500 uppercase tracking-wider">Amount</th>
                <th className="pb-3 text-xs font-medium text-surface-500 uppercase tracking-wider">Status</th>
                <th className="pb-3 text-xs font-medium text-surface-500 uppercase tracking-wider w-10" />
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => {
                const s = statusConfig[inv.status]
                const StatusIcon = s.icon
                return (
                  <tr key={inv.id} className="border-b border-surface-800/30 hover:bg-surface-800/20 transition-colors">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-surface-600" />
                        <span className="text-surface-300 font-mono text-xs">{inv.id}</span>
                      </div>
                    </td>
                    <td className="py-3 text-surface-500 text-xs">{inv.date}</td>
                    <td className="py-3 text-surface-300 text-xs">{inv.amount}</td>
                    <td className="py-3">
                      <span className={`inline-flex items-center gap-1.5 text-xs ${s.class}`}>
                        <StatusIcon className="w-3.5 h-3.5" />
                        {s.label}
                      </span>
                    </td>
                    <td className="py-3">
                      <button className="p-1.5 rounded-lg text-surface-600 hover:text-surface-300 hover:bg-surface-800 transition-colors" title="Download PDF">
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}