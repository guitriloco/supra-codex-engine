import { Check, X, ArrowRight, Tag } from 'lucide-react'
import { Button } from '@/components/Button'
import { useAuth } from '@/context/AuthContext'
import { Link } from 'react-router-dom'

interface Tier {
  name: string
  price: string
  period: string
  description: string
  highlight: boolean
  features: { name: string; included: boolean }[]
  cta: string
  ctaVariant: 'primary' | 'secondary'
  ctaTo: string
}

const tiers: Tier[] = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'For hobbyists and small projects. Get started with sovereign AI orchestration.',
    highlight: false,
    features: [
      { name: 'Up to 3 nodes', included: true },
      { name: '5 pipeline runs / month', included: true },
      { name: 'Community support', included: true },
      { name: 'Basic dashboard', included: true },
      { name: 'Nectar Marketplace access', included: false },
      { name: 'Priority support', included: false },
      { name: 'Custom integrations', included: false },
      { name: 'SSO / SAML', included: false },
      { name: 'Dedicated support', included: false },
      { name: 'SLA guarantee', included: false },
    ],
    cta: 'Start Free',
    ctaVariant: 'secondary',
    ctaTo: '/',
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For freelancers and agencies running production automation pipelines.',
    highlight: true,
    features: [
      { name: 'Up to 25 nodes', included: true },
      { name: 'Unlimited pipeline runs', included: true },
      { name: 'Priority support', included: true },
      { name: 'Advanced dashboard', included: true },
      { name: 'Nectar Marketplace access', included: true },
      { name: '15% marketplace commission', included: true },
      { name: 'Custom integrations', included: false },
      { name: 'SSO / SAML', included: false },
      { name: 'Dedicated support', included: false },
      { name: 'SLA guarantee', included: false },
    ],
    cta: 'Go Pro',
    ctaVariant: 'primary',
    ctaTo: '/settings/billing',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For organizations that need dedicated infrastructure, SLA guarantees, and SSO.',
    highlight: false,
    features: [
      { name: 'Unlimited nodes', included: true },
      { name: 'Unlimited pipeline runs', included: true },
      { name: 'Dedicated support', included: true },
      { name: 'Full dashboard + analytics', included: true },
      { name: 'Nectar Marketplace access', included: true },
      { name: '10% marketplace commission', included: true },
      { name: 'Custom integrations', included: true },
      { name: 'SSO / SAML', included: true },
      { name: 'SLA guarantee', included: true },
      { name: 'On-prem deployment', included: true },
    ],
    cta: 'Contact Sales',
    ctaVariant: 'secondary',
    ctaTo: 'mailto:sales@supracodex.io',
  },
]

export default function Pricing() {
  const { user } = useAuth()
  const currentTier = user?.tier

  return (
    <div className="space-y-8">
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 mb-3 px-3 py-1 rounded-full border border-primary-600/20 bg-primary-600/5">
          <Tag className="w-3.5 h-3.5 text-primary-400" />
          <span className="text-xs text-primary-400 font-medium">Pricing</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Plans that scale with you</h1>
        <p className="mt-3 text-sm text-surface-400 leading-relaxed">
          From hobbyist to enterprise. All plans include local-first compute, no vendor lock-in,
          and full data sovereignty.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {tiers.map((tier) => {
          const isCurrentPlan = tier.name.toLowerCase() === currentTier
          return (
            <div
              key={tier.name}
              className={`relative rounded-2xl border p-6 flex flex-col transition-all duration-300
                ${
                  tier.highlight
                    ? 'border-primary-600/30 bg-gradient-to-b from-primary-600/5 to-surface-900 glow-blue scale-[1.02] md:scale-105 z-10'
                    : 'border-surface-800 bg-surface-900/50 hover:border-surface-700'
                }`}
            >
              {tier.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-primary-600 text-white text-xs font-semibold shadow-lg shadow-primary-600/20">
                  Most Popular
                </div>
              )}
              {isCurrentPlan && !tier.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-surface-700 text-surface-200 text-xs font-medium border border-surface-600">
                  Current Plan
                </div>
              )}

              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white">{tier.name}</h2>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-white">{tier.price}</span>
                  {tier.period && (
                    <span className="text-sm text-surface-500">{tier.period}</span>
                  )}
                </div>
                <p className="mt-2 text-xs text-surface-500 leading-relaxed">{tier.description}</p>
              </div>

              <ul className="flex-1 space-y-2.5 mb-6">
                {tier.features.map((feature) => (
                  <li key={feature.name} className="flex items-start gap-2.5 text-sm">
                    {feature.included ? (
                      <Check className="w-4 h-4 text-success-400 flex-shrink-0 mt-0.5" />
                    ) : (
                      <X className="w-4 h-4 text-surface-700 flex-shrink-0 mt-0.5" />
                    )}
                    <span
                      className={
                        feature.included ? 'text-surface-300' : 'text-surface-600'
                      }
                    >
                      {feature.name}
                    </span>
                  </li>
                ))}
              </ul>

              {tier.ctaTo.startsWith('mailto:') ? (
                <a href={tier.ctaTo} className="w-full block">
                  <Button
                    variant={tier.ctaVariant}
                    size="lg"
                    className="w-full"
                    disabled={isCurrentPlan}
                  >
                    {isCurrentPlan ? 'Current Plan' : tier.cta}
                    {!isCurrentPlan && <ArrowRight className="w-4 h-4" />}
                  </Button>
                </a>
              ) : (
                <Link to={isCurrentPlan ? '#' : tier.ctaTo} className="w-full block">
                  <Button
                    variant={tier.ctaVariant}
                    size="lg"
                    className="w-full"
                    disabled={isCurrentPlan}
                  >
                    {isCurrentPlan ? 'Current Plan' : tier.cta}
                    {!isCurrentPlan && <ArrowRight className="w-4 h-4" />}
                  </Button>
                </Link>
              )}
            </div>
          )
        })}
      </div>

      {/* FAQ / Trust strip */}
      <div className="max-w-2xl mx-auto pt-8 text-center border-t border-surface-800/50">
        <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-surface-600">
          <span>No hidden fees</span>
          <span className="w-1 h-1 rounded-full bg-surface-700" />
          <span>Cancel anytime</span>
          <span className="w-1 h-1 rounded-full bg-surface-700" />
          <span>30-day money-back guarantee</span>
          <span className="w-1 h-1 rounded-full bg-surface-700" />
          <span>Self-hosted always</span>
        </div>
      </div>
    </div>
  )
}