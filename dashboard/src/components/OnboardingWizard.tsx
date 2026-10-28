import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  GitBranch,
  Hexagon,
  Loader2,
  Server,
  ShoppingCart,
  X,
} from 'lucide-react'
import { Button } from '@/components/Button'
import {
  ONBOARDING_RESET_EVENT,
  completeOnboarding,
  isOnboardingComplete,
} from '@/lib/onboarding'
import { listInstalledModules, listNodes, listPipelines } from '@/services/api'

interface OnboardingStep {
  icon: typeof Server
  title: string
  description: string
  route: string
  cta: string
  /** Live count of the thing this step is about, or null while unknown. */
  progressLabel: (counts: Counts) => string | null
}

interface Counts {
  nodes: number
  onlineNodes: number
  pipelines: number
  runningPipelines: number
  modules: number
}

const steps: OnboardingStep[] = [
  {
    icon: Server,
    title: 'Add a Node',
    description:
      'Register your first compute node and start running sovereign workloads on hardware you already own.',
    route: '/nodes',
    cta: 'Open Nodes',
    progressLabel: (c) =>
      c.nodes === 0
        ? 'No nodes registered yet'
        : `${c.onlineNodes}/${c.nodes} node${c.nodes === 1 ? '' : 's'} online`,
  },
  {
    icon: GitBranch,
    title: 'Run a Pipeline',
    description:
      'Build or launch an automation pipeline — scraping, enrichment, and analysis in one resilient flow.',
    route: '/pipelines/builder',
    cta: 'Open Builder',
    progressLabel: (c) =>
      c.pipelines === 0
        ? 'No pipelines defined yet'
        : `${c.pipelines} pipeline${c.pipelines === 1 ? '' : 's'} · ${c.runningPipelines} running`,
  },
  {
    icon: ShoppingCart,
    title: 'Browse the Marketplace',
    description:
      'Install pre-built automation modules from Nectar to skip straight to value without writing glue code.',
    route: '/marketplace',
    cta: 'Browse Nectar',
    progressLabel: (c) =>
      c.modules === 0 ? 'No modules installed yet' : `${c.modules} module${c.modules === 1 ? '' : 's'} installed`,
  },
]

export function OnboardingWizard() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(0)
  const [counts, setCounts] = useState<Counts | null>(null)

  // First-run check + Settings "restart tour" listener.
  useEffect(() => {
    if (!isOnboardingComplete()) setOpen(true)

    const reopen = () => {
      setStep(0)
      setOpen(true)
    }
    window.addEventListener(ONBOARDING_RESET_EVENT, reopen)
    return () => window.removeEventListener(ONBOARDING_RESET_EVENT, reopen)
  }, [])

  // Pull real workspace state so the tour reflects what the user already has.
  useEffect(() => {
    if (!open) return
    let cancelled = false
    ;(async () => {
      const [nodesResult, pipelinesResult, modulesResult] = await Promise.allSettled([
        listNodes(),
        listPipelines(),
        listInstalledModules(),
      ])
      if (cancelled) return
      const nodes = nodesResult.status === 'fulfilled' ? nodesResult.value : []
      const pipelines = pipelinesResult.status === 'fulfilled' ? pipelinesResult.value : []
      const modules = modulesResult.status === 'fulfilled' ? modulesResult.value : []
      setCounts({
        nodes: nodes.length,
        onlineNodes: nodes.filter((n) => n.status === 'online').length,
        pipelines: pipelines.length,
        runningPipelines: pipelines.filter((p) => p.status === 'running').length,
        modules: modules.length,
      })
    })()
    return () => {
      cancelled = true
    }
  }, [open])

  const close = useCallback(() => {
    completeOnboarding()
    setOpen(false)
  }, [])

  // Escape closes the tour.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, close])

  const goToStepRoute = useCallback(() => {
    const target = steps[step]
    completeOnboarding()
    setOpen(false)
    navigate(target.route)
  }, [navigate, step])

  if (!open) return null

  const current = steps[step]
  const Icon = current.icon
  const isLast = step === steps.length - 1
  const progress = counts ? current.progressLabel(counts) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={close} />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="relative w-full max-w-lg rounded-2xl border border-surface-800 bg-surface-900 p-6 shadow-2xl glow-blue"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-600/20 flex items-center justify-center">
              <Hexagon className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 id="onboarding-title" className="text-base font-bold text-white">
                Sovereign Compute Awaits
              </h2>
              <p className="text-xs text-surface-500">Get set up in three quick steps</p>
            </div>
          </div>
          <button
            onClick={close}
            className="p-1.5 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          {steps.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              aria-label={`Go to step ${i + 1}`}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? 'bg-primary-500' : 'bg-surface-800'
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="flex flex-col items-center text-center py-4">
          <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center mb-4">
            <Icon className="w-8 h-8 text-primary-400" />
          </div>
          <p className="text-xs font-medium text-surface-500 uppercase tracking-wider mb-2">
            Step {step + 1} of {steps.length}
          </p>
          <h3 className="text-xl font-bold text-white mb-2">{current.title}</h3>
          <p className="text-sm text-surface-400 max-w-sm leading-relaxed">{current.description}</p>

          <div className="mt-4 h-5">
            {counts === null ? (
              <span className="inline-flex items-center gap-1.5 text-xs text-surface-600">
                <Loader2 className="w-3 h-3 animate-spin" />
                Checking your workspace…
              </span>
            ) : (
              progress && (
                <span className="inline-flex items-center gap-1.5 text-xs text-surface-400 bg-surface-800/60 border border-surface-700 rounded-full px-2.5 py-1">
                  <CheckCircle2 className="w-3 h-3 text-success-400" />
                  {progress}
                </span>
              )
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-6">
          <div className="flex items-center gap-2">
            {step > 0 && (
              <Button variant="secondary" size="sm" onClick={() => setStep((s) => Math.max(0, s - 1))}>
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={close}>
              Skip tour
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={goToStepRoute}>
              {current.cta}
            </Button>
            {isLast ? (
              <Button size="sm" onClick={close}>
                Get Started
              </Button>
            ) : (
              <Button size="sm" onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}>
                Next
                <ArrowRight className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
