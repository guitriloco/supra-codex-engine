import { useState, useEffect, useRef, useCallback } from 'react'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { useWebSocket, type PipelineEvent } from '@/hooks/useWebSocket'
import { submitPipeline, type PipelineRunResult } from '@/services/api'
import { Send, X, ChevronDown, ChevronRight, Wifi, WifiOff, Bot, Sparkles, AlertCircle, Terminal } from 'lucide-react'

interface TaskEntry {
  id: string
  url: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  reasoning: string[]
  result?: Record<string, unknown>
  error?: string
  timestamp: string
  expanded: boolean
}

export default function LivePipeline() {
  const [url, setUrl] = useState('')
  const [tasks, setTasks] = useState<TaskEntry[]>([])
  const [submitting, setSubmitting] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)

  const handleWsMessage = useCallback((event: PipelineEvent) => {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.id === event.pipelineId)
      if (idx === -1) return prev

      const updated = [...prev]
      const task = { ...updated[idx] }

      switch (event.type) {
        case 'status':
          task.status = (event.payload.status as TaskEntry['status']) || task.status
          break
        case 'reasoning':
          if (typeof event.payload.text === 'string') {
            task.reasoning = [...task.reasoning, event.payload.text]
          }
          break
        case 'result':
          task.status = 'completed'
          task.result = event.payload as Record<string, unknown>
          break
        case 'error':
          task.status = 'failed'
          task.error = (event.payload.message as string) || 'Unknown error'
          break
      }

      updated[idx] = task
      return updated
    })
  }, [])

  const { isConnected, connect, disconnect } = useWebSocket({
    onMessage: handleWsMessage,
  })

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [tasks])

  const handleSubmit = async () => {
    if (!url.trim() || submitting) return

    setSubmitting(true)
    const newTask: TaskEntry = {
      id: crypto.randomUUID(),
      url: url.trim(),
      status: 'queued',
      reasoning: [],
      timestamp: new Date().toISOString(),
      expanded: true,
    }

    setTasks((prev) => [newTask, ...prev])
    setUrl('')

    try {
      const result: PipelineRunResult = await submitPipeline(url.trim())
      setTasks((prev) => {
        const idx = prev.findIndex((t) => t.id === newTask.id)
        if (idx === -1) return prev
        const updated = [...prev]
        updated[idx] = { ...updated[idx], id: result.id, status: result.status }
        return updated
      })
    } catch {
      setTasks((prev) => {
        const idx = prev.findIndex((t) => t.id === newTask.id)
        if (idx === -1) return prev
        const updated = [...prev]
        updated[idx] = { ...updated[idx], status: 'failed', error: 'Failed to submit pipeline' }
        return updated
      })
    } finally {
      setSubmitting(false)
    }
  }

  const toggleExpand = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, expanded: !t.expanded } : t))
    )
  }

  const clearAll = () => setTasks([])

  const statusIcon = (status: TaskEntry['status']) => {
    switch (status) {
      case 'queued':
        return <div className="w-2 h-2 rounded-full bg-surface-500" />
      case 'running':
        return <div className="w-2 h-2 rounded-full bg-warning-400 animate-pulse" />
      case 'completed':
        return <div className="w-2 h-2 rounded-full bg-success-400" />
      case 'failed':
        return <AlertCircle className="w-3.5 h-3.5 text-danger-400" />
    }
  }

  const statusLabel = (status: TaskEntry['status']) => {
    switch (status) {
      case 'queued': return 'Queued'
      case 'running': return 'Running'
      case 'completed': return 'Completed'
      case 'failed': return 'Failed'
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Live Pipeline</h1>
          <p className="text-sm text-surface-500 mt-1">Real-time pipeline monitoring & execution</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-800 bg-surface-900">
            {isConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-success-400" />
                <span className="text-xs text-success-400 font-medium">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-surface-500" />
                <span className="text-xs text-surface-500 font-medium">Disconnected</span>
              </>
            )}
          </div>
          {isConnected ? (
            <Button variant="ghost" size="sm" onClick={disconnect}>Disconnect</Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={connect}>Connect</Button>
          )}
        </div>
      </div>

      {/* URL input */}
      <Card>
        <form
          onSubmit={(e) => { e.preventDefault(); handleSubmit() }}
          className="flex items-center gap-3"
        >
          <div className="relative flex-1">
            <Send className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter a URL to scrape (e.g. https://example.com)"
              className="w-full bg-surface-950 border border-surface-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-surface-200 
                placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30 transition-all font-mono"
            />
          </div>
          <Button type="submit" isLoading={submitting} disabled={!url.trim()}>
            Submit
          </Button>
          {tasks.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearAll}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </form>
      </Card>

      {/* Task stream */}
      <div className="space-y-2">
        {tasks.length === 0 && (
          <div className="text-center py-16">
            <Terminal className="w-12 h-12 text-surface-700 mx-auto mb-4" />
            <p className="text-surface-500 text-sm">Submit a URL above to start a pipeline</p>
            <p className="text-surface-600 text-xs mt-1">Live results will appear here in real-time</p>
          </div>
        )}

        {tasks.map((task) => (
          <Card key={task.id} className="p-0 overflow-hidden">
            {/* Task header */}
            <button
              onClick={() => toggleExpand(task.id)}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-800/30 transition-colors text-left"
            >
              {task.expanded ? <ChevronDown className="w-3.5 h-3.5 text-surface-500 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-surface-500 flex-shrink-0" />}
              {statusIcon(task.status)}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-surface-200 truncate font-mono">{task.url}</p>
              </div>
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${
                task.status === 'completed' ? 'text-success-400 border-success-500/20 bg-success-500/10' :
                task.status === 'failed' ? 'text-danger-400 border-danger-500/20 bg-danger-500/10' :
                task.status === 'running' ? 'text-warning-400 border-warning-500/20 bg-warning-500/10' :
                'text-surface-500 border-surface-700 bg-surface-800'
              }`}>
                {statusLabel(task.status)}
              </span>
            </button>

            {/* Expanded content */}
            {task.expanded && (
              <div className="border-t border-surface-800 px-4 py-3 space-y-4">
                {/* Reasoning log */}
                {task.reasoning.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Bot className="w-3.5 h-3.5 text-accent-400" />
                      <span className="text-[10px] font-semibold text-accent-400 uppercase tracking-wider">Xerebro AI Reasoning</span>
                    </div>
                    <div className="bg-surface-950 rounded-lg p-3 space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs">
                      {task.reasoning.map((line, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className="text-accent-500 flex-shrink-0 mt-0.5">▸</span>
                          <span className="text-surface-300">{line}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Task result */}
                {task.result && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-success-400" />
                      <span className="text-[10px] font-semibold text-success-400 uppercase tracking-wider">Extracted Data</span>
                    </div>
                    <div className="bg-surface-950 rounded-lg p-3 font-mono text-xs">
                      <pre className="text-surface-300 whitespace-pre-wrap break-all overflow-x-auto max-h-64">
                        {JSON.stringify(task.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Error */}
                {task.error && (
                  <div className="flex items-center gap-2 text-xs text-danger-400 bg-danger-500/5 rounded-lg px-3 py-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{task.error}</span>
                  </div>
                )}

                {/* Waiting state */}
                {task.reasoning.length === 0 && !task.result && !task.error && (
                  <div className="flex items-center gap-2 text-xs text-surface-500">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-surface-600 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-surface-600 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-surface-600 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span>Waiting for pipeline data...</span>
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}