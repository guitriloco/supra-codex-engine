import { Card, CardHeader, CardTitle } from '@/components/Card'
import { Button } from '@/components/Button'
import { NotificationPreferences } from '@/components/NotificationPreferences'
import { resetOnboarding } from '@/lib/onboarding'
import { User, Bell, Key, CreditCard, Palette, Compass, RotateCcw } from 'lucide-react'
import { Link } from 'react-router-dom'

const sections = [
  { icon: User, label: 'Profile', description: 'Manage your personal information', to: '/settings' },
  { icon: Bell, label: 'Notifications', description: 'Configure alert preferences', to: '/settings#notifications' },
  { icon: Key, label: 'API Keys', description: 'Manage authentication tokens', to: '/settings' },
  { icon: CreditCard, label: 'Billing', description: 'Subscription & payment details', to: '/settings/billing' },
  { icon: Palette, label: 'Appearance', description: 'Theme and display settings', to: '/settings' },
]

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-surface-500 mt-1">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map((section) => (
          <Link key={section.label} to={section.to}>
            <Card hover className="flex items-center gap-4 cursor-pointer">
              <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
                <section.icon className="w-5 h-5 text-surface-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-surface-200">{section.label}</h3>
                <p className="text-xs text-surface-500">{section.description}</p>
              </div>
              <div className="w-2 h-2 border-r-2 border-b-2 border-surface-600 rotate-[-45deg]" />
            </Card>
          </Link>
        ))}
      </div>

      {/* Notification delivery preferences */}
      <NotificationPreferences />

      {/* Subscription info */}
      <Card>
        <CardHeader>
          <CardTitle>Current Plan</CardTitle>
          <span className="px-3 py-1 bg-primary-600/10 text-primary-400 rounded-md text-xs font-medium border border-primary-600/20">
            Pro
          </span>
        </CardHeader>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-surface-500">Nodes</span>
            <p className="text-white font-medium">Up to 25</p>
          </div>
          <div>
            <span className="text-surface-500">Pipelines</span>
            <p className="text-white font-medium">Unlimited</p>
          </div>
          <div>
            <span className="text-surface-500">Support</span>
            <p className="text-white font-medium">Priority</p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-surface-800">
          <Link to="/settings/billing">
            <Button variant="secondary">Manage Subscription</Button>
          </Link>
        </div>
      </Card>

      {/* Help / onboarding */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-surface-400" />
            <CardTitle>Product Tour</CardTitle>
          </div>
        </CardHeader>
        <p className="text-xs text-surface-500 mb-4">
          Replay the three-step setup tour — adding a node, running a pipeline and browsing the
          Nectar Marketplace.
        </p>
        <Button variant="secondary" size="sm" onClick={resetOnboarding}>
          <RotateCcw className="w-3.5 h-3.5" />
          Restart tour
        </Button>
      </Card>
    </div>
  )
}
