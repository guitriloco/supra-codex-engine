import { useEffect, useState } from 'react'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import {
  Plus,
  Globe,
  Brain,
  Filter,
  Wand2,
  Download,
  Trash2,
  Save,
  Play,
  X,
  ChevronUp,
  ChevronDown,
  Loader2,
  FolderOpen,
  CheckCircle2,
} from 'lucide-react'
import {
  savePipelineDefinition,
  listPipelineDefinitions,
  getPipelineDefinition,
  deletePipelineDefinition,
  runPipelineDefinition,
  PipelineStepDef,
  PipelineDefinition,
  PipelineSummary,
  PipelineRunResult,
} from '@/services/api'

const STEP_TYPES = [
  { type: 'scrape' as const, label: 'Scrape URL', icon: Globe, desc: 'Fetch and extract a web page', color: 'text-primary-400 bg-primary-600/15 border-primary-600/30' },
  { type: 'enrich' as const, label: 'Enrich with AI', icon: Brain, desc: 'Let Xerebro reason over the data', color: 'text-accent-400 bg-accent-600/15 border-accent-600/30' },
  { type: 'filter' as const, label: 'Filter / Transform', icon: Filter, desc: 'Keep or drop rows by rules', color: 'text-warning-400 bg-warning-500/15 border-warning-500/30' },
  { type: 'export' as const, label: 'Export', icon: Download, desc: 'Output as JSON/CSV or webhook', color: 'text-success-400 bg-success-500/15 border-success-500/30' },
]

function newStepId() {
  return `step_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`
}

function emptyPipeline(): PipelineDefinition {
  return { name: '', description: '', steps: [] }
}

function defaultConfig(type: string): Record<string, any> {
  switch (type) {
    case 'scrape': return { url: '' }
    case 'enrich': return { prompt: 'Extract the main topic, key entities, and a concise summary. Return JSON.', temperature: 0.1, max_tokens: 1024 }
    case 'filter': return { field: 'body_text', contains: '' }
    case 'export': return { format: 'json' }
    default: return {}
  }
}

const STEP_LABEL: Record<string, string> = {
  scrape: 'Scrape URL',
  enrich: 'Enrich with AI',
  filter: 'Filter / Transform',
  export: 'Export',
}

export default function PipelineBuilder() {
  const [pipeline, setPipeline] = useState<PipelineDefinition>(emptyPipeline())
  const [savedPipelines, setSavedPipelines] = useState<PipelineSummary[]>([])
  const [currentId, setCurrentId] = useState<string | undefined>(undefined)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<PipelineRunResult | null>(null)
  const [showLibrary, setShowLibrary] = useState(false)
  const [toast, setToast] = useState('')

  useEffect(() => {
    loadLibrary()
  }, [])

  function notify(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  async function loadLibrary() {
    try {
      const list = await listPipelineDefinitions()
      setSavedPipelines(list)
    } catch {
      notify('Could not load pipeline library')
    }
  }

  function setStepConfig(id: string, key: string, value: any) {
    setPipeline((p) => ({
      ...p,
      steps: p.steps.map((s) =>
        s.id === id ? { ...s, config: { ...s.config, [key]: value } } : s,
      ),
    }))
    setDirty(true)
  }

  function setStepName(id: string, name: string) {
    setPipeline((p) => ({
      ...p,
      steps: p.steps.map((s) => (s.id === id ? { ...s, name } : s)),
    }))
    setDirty(true)
  }

  function addStep(type: PipelineStepDef['type']) {
    const step: PipelineStepDef = {
      id: newStepId(),
      type,
      name: STEP_LABEL[type],
      config: defaultConfig(type),
    }
    setPipeline((p) => ({ ...p, steps: [...p.steps, step] }))
    setDirty(true)
  }

  function removeStep(id: string) {
    setPipeline((p) => ({ ...p, steps: p.steps.filter((s) => s.id !== id) }))
    setDirty(true)
  }

  function moveStep(index: number, dir: -1 | 1) {
    const target = index + dir
    if (target < 0 || target >= pipeline.steps.length) return
    setPipeline((p) => {
      const steps = [...p.steps]
      ;[steps[index], steps[target]] = [steps[target], steps[index]]
      return { ...p, steps }
    })
    setDirty(true)
  }

  async function handleSave() {
    if (!pipeline.name.trim()) {
      notify('Give the pipeline a name first')
      return
    }
    if (pipeline.steps.length === 0) {
      notify('Add at least one step')
      return
    }
    setSaving(true)
    try {
      const res = await savePipelineDefinition({
        ...pipeline,
        id: currentId,
      })
      setCurrentId(res.id)
      setDirty(false)
      notify(`Saved "${pipeline.name}"`)
      await loadLibrary()
    } catch (e: any) {
      notify(e?.message || 'Failed to save pipeline')
    } finally {
      setSaving(false)
    }
  }

  async function handleRun() {
    if (!currentId) {
      // Save first if never saved
      await handleSave()
      if (!currentId) return
    }
    setRunning(true)
    setRunResult(null)
    try {
      const res = await runPipelineDefinition(currentId!)
      setRunResult(res)
    } catch (e: any) {
      notify(e?.message || 'Pipeline run failed')
    } finally {
      setRunning(false)
    }
  }

  async function handleLoad(id: string) {
    try {
      const def = await getPipelineDefinition(id)
      setCurrentId(id)
      setPipeline({
        name: def.name || '',
        description: def.description || '',
        steps: def.steps || [],
      })
      setDirty(false)
      setRunResult(null)
      setShowLibrary(false)
      notify(`Loaded "${def.name}"`)
    } catch (e: any) {
      notify(e?.message || 'Failed to load pipeline')
    }
  }

  async function handleDelete(id: string) {
    try {
      await deletePipelineDefinition(id)
      notify('Pipeline deleted')
      await loadLibrary()
      if (currentId === id) {
        setCurrentId(undefined)
        setPipeline(emptyPipeline())
      }
    } catch (e: any) {
      notify(e?.message || 'Failed to delete pipeline')
    }
  }

  function newPipeline() {
    setCurrentId(undefined)
    setPipeline(emptyPipeline())
    setDirty(false)
    setRunResult(null)
    notify('New pipeline')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Pipeline Builder</h1>
          <p className="text-sm text-surface-500 mt-1">
            Design automation workflows step by step
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setShowLibrary(!showLibrary)}>
            <FolderOpen className="w-4 h-4" />
            Library
          </Button>
          <Button variant="secondary" onClick={newPipeline}>
            <Plus className="w-4 h-4" />
            New
          </Button>
          <Button variant="secondary" onClick={handleSave} isLoading={saving}>
            <Save className="w-4 h-4" />
            Save
          </Button>
          <Button onClick={handleRun} isLoading={running} disabled={pipeline.steps.length === 0}>
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? 'Running…' : 'Run'}
          </Button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 rounded-lg border border-surface-800 bg-surface-900 px-4 py-3 shadow-xl">
          <p className="text-sm text-surface-200">{toast}</p>
        </div>
      )}

      {/* Library drawer */}
      {showLibrary && (
        <Card className="glow-blue">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-surface-200">Saved Pipelines</h3>
            <button onClick={() => setShowLibrary(false)} className="p-1 rounded-lg text-surface-500 hover:text-surface-300">
              <X className="w-4 h-4" />
            </button>
          </div>
          {savedPipelines.length === 0 ? (
            <p className="text-sm text-surface-500">No saved pipelines yet. Build one and click Save.</p>
          ) : (
            <div className="space-y-2">
              {savedPipelines.map((p) => (
                <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/50 hover:border-surface-700">
                  <div>
                    <p className="text-sm font-medium text-surface-200">{p.name}</p>
                    <p className="text-xs text-surface-500">
                      {p.description || 'No description'} · {p.steps} steps ·{' '}
                      {p.types.join(', ')}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="sm" variant="secondary" onClick={() => handleLoad(p.id)}>
                      Load
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(p.id)}>
                      <Trash2 className="w-3.5 h-3.5 text-danger-400" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Name & description */}
      <Card>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">Pipeline name</label>
            <input
              type="text"
              value={pipeline.name}
              onChange={(e) => { setPipeline({ ...pipeline, name: e.target.value }); setDirty(true) }}
              placeholder="e.g. Competitor price monitor"
              className="mt-2 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-primary-600/50"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">Description</label>
            <input
              type="text"
              value={pipeline.description}
              onChange={(e) => { setPipeline({ ...pipeline, description: e.target.value }); setDirty(true) }}
              placeholder="What does this workflow do?"
              className="mt-2 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-primary-600/50"
            />
          </div>
        </div>
        {dirty && <p className="mt-3 text-xs text-warning-400">● Unsaved changes</p>}
      </Card>

      {/* Step palette */}
      <div>
        <p className="text-xs font-medium text-surface-400 uppercase tracking-wider mb-2">Add a step</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {STEP_TYPES.map((s) => (
            <button
              key={s.type}
              onClick={() => addStep(s.type)}
              className={`flex items-start gap-3 p-4 rounded-xl border bg-surface-900 hover:border-surface-700 hover:bg-surface-800/50 transition-all text-left ${s.color.split(' ').slice(-1)[0]}`}
            >
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${s.color}`}>
                <s.icon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-surface-200">{s.label}</p>
                <p className="text-xs text-surface-500 mt-0.5">{s.desc}</p>
              </div>
              <Plus className="w-4 h-4 text-surface-500 ml-auto mt-1" />
            </button>
          ))}
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        <p className="text-xs font-medium text-surface-400 uppercase tracking-wider">
          Workflow ({pipeline.steps.length} steps)
        </p>
        {pipeline.steps.length === 0 && (
          <Card className="text-center">
            <Wand2 className="w-8 h-8 text-surface-700 mx-auto" />
            <p className="mt-2 text-sm text-surface-500">Your workflow is empty. Add steps above to get started.</p>
          </Card>
        )}
        {pipeline.steps.map((step, i) => {
          const meta = STEP_TYPES.find((s) => s.type === step.type)
          const Icon = meta?.icon || Wand2
          return (
            <Card key={step.id} className="p-0 overflow-hidden">
              {/* Step header */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-800 bg-surface-950/50">
                <span className="text-xs font-bold text-surface-600 w-5">{i + 1}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${STEP_TYPES.find((s) => s.type === step.type)?.color || 'bg-surface-800 text-surface-400'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium text-surface-200">{meta?.label}</span>
                <div className="flex items-center gap-1 ml-auto">
                  <button onClick={() => moveStep(i, -1)} disabled={i === 0} className="p-1.5 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 disabled:opacity-30">
                    <ChevronUp className="w-4 h-4" />
                  </button>
                  <button onClick={() => moveStep(i, 1)} disabled={i === pipeline.steps.length - 1} className="p-1.5 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 disabled:opacity-30">
                    <ChevronDown className="w-4 h-4" />
                  </button>
                  <button onClick={() => removeStep(step.id)} className="p-1.5 rounded-lg text-surface-500 hover:text-danger-400 hover:bg-surface-800">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="p-4">
                {/* Step config */}
                {step.type === 'scrape' && (
                  <div>
                    <label className="text-xs text-surface-400">URL to scrape</label>
                    <input
                      type="text"
                      value={step.config.url || ''}
                      onChange={(e) => setStepConfig(step.id, 'url', e.target.value)}
                      placeholder="https://example.com"
                      className="mt-1.5 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-primary-600/50"
                    />
                  </div>
                )}
                {step.type === 'enrich' && (
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-surface-400">Prompt template</label>
                      <textarea
                        value={step.config.prompt || ''}
                        onChange={(e) => setStepConfig(step.id, 'prompt', e.target.value)}
                        rows={2}
                        className="mt-1.5 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 focus:outline-none focus:border-accent-500/50 resize-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs text-surface-400">Temperature: <span className="text-accent-400">{step.config.temperature ?? 0.1}</span></label>
                        <input
                          type="range" min={0} max={2} step={0.05}
                          value={step.config.temperature ?? 0.1}
                          onChange={(e) => setStepConfig(step.id, 'temperature', Number(e.target.value))}
                          className="mt-2 w-full accent-accent-500"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-surface-400">Max tokens: <span className="text-accent-400">{step.config.max_tokens ?? 1024}</span></label>
                        <input
                          type="range" min={128} max={4096} step={128}
                          value={step.config.max_tokens ?? 1024}
                          onChange={(e) => setStepConfig(step.id, 'max_tokens', Number(e.target.value))}
                          className="mt-2 w-full accent-accent-500"
                        />
                      </div>
                    </div>
                  </div>
                )}
                {step.type === 'filter' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-surface-400">Field</label>
                      <select
                        value={step.config.field || 'body_text'}
                        onChange={(e) => setStepConfig(step.id, 'field', e.target.value)}
                        className="mt-1.5 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 focus:outline-none"
                      >
                        <option value="body_text">body_text</option>
                        <option value="title">title</option>
                        <option value="all">all</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-surface-400">Keep when it contains</label>
                      <input
                        type="text"
                        value={step.config.contains || ''}
                        onChange={(e) => setStepConfig(step.id, 'contains', e.target.value)}
                        placeholder="e.g. pricing (empty = keep all)"
                        className="mt-1.5 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-warning-500/50"
                      />
                    </div>
                  </div>
                )}
                {step.type === 'export' && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs text-surface-400">Output format</label>
                      <select
                        value={step.config.format || 'json'}
                        onChange={(e) => setStepConfig(step.id, 'format', e.target.value)}
                        className="mt-1.5 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 focus:outline-none"
                      >
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                        <option value="webhook">Webhook</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )
        })}
      </div>

      {/* Run results */}
      {runResult && (
        <Card className="glow-success" >
          <div className="flex items-center justify-between border-b border-surface-800 pb-3 mb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-success-400" />
              <h3 className="text-sm font-semibold text-surface-200">
                Run complete — {runResult.name}
              </h3>
            </div>
            <span className="text-xs text-surface-500">{runResult.duration_ms.toFixed(0)} ms</span>
          </div>
          {/* Step statuses */}
          <div className="space-y-2 mb-4">
            {runResult.steps.map((s, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-surface-800 bg-surface-950/50">
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    s.status === 'success' ? 'bg-success-400' : s.status === 'failed' ? 'bg-danger-400' : 'bg-warning-400'
                  }`}
                />
                <span className="text-xs text-surface-500 w-5">{i + 1}</span>
                <span className="text-sm text-surface-200">{STEP_LABEL[s.type] || s.type}</span>
                {s.summary && <span className="text-xs text-surface-500 ml-auto">{s.summary}</span>}
                {s.error && <span className="text-xs text-danger-400 ml-auto">{s.error}</span>}
              </div>
            ))}
          </div>
          {/* Result JSON */}
          {runResult.result && (
            <pre className="max-h-72 overflow-auto rounded-lg bg-surface-950 border border-surface-800 p-4 text-xs text-surface-300 whitespace-pre-wrap">
              {JSON.stringify(runResult.result, null, 2)}
            </pre>
          )}
        </Card>
      )}
    </div>
  )
}
