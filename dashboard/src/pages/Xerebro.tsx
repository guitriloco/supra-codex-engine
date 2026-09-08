import { useEffect, useRef, useState } from 'react'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import {
  Brain,
  Send,
  Trash2,
  Globe,
  Loader2,
  Settings2,
  Zap,
  AlertTriangle,
} from 'lucide-react'
import {
  listXerebroModels,
  xerebroChat,
  XerebroModelsResponse,
  XerebroChatMessage,
} from '@/services/api'

const DEFAULT_SYSTEM_PROMPT =
  'You are Xerebro, the AI brain of Supra-Codex Engine. ' +
  'You help orchestrate automation pipelines: analyzing web content, ' +
  'deciding data extraction strategies, and enriching results. ' +
  'Respond with concise, actionable answers.'

export default function Xerebro() {
  const [models, setModels] = useState<XerebroModelsResponse>({
    available: false,
    models: [],
    default_model: 'llama3.2',
  })
  const [model, setModel] = useState('llama3.2')
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(1024)
  const [showSettings, setShowSettings] = useState(false)
  const [messages, setMessages] = useState<XerebroChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [totalTokens, setTotalTokens] = useState(0)
  const [analyzeUrl, setAnalyzeUrl] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [healthLoading, setHealthLoading] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadModels()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadModels() {
    try {
      const res = await listXerebroModels()
      setModels(res)
      if (res.models.length > 0) {
        setModel(res.models[0].name)
      } else if (res.default_model) {
        setModel(res.default_model)
      }
    } catch {
      setModels({ available: false, models: [], default_model: 'llama3.2' })
    } finally {
      setHealthLoading(false)
    }
  }

  async function sendMessage(promptText: string, context?: Record<string, unknown>) {
    const text = (promptText || input).trim()
    if (!text || loading) return
    if (messages.length === 0 && !context) {
      // First message: seed with system prompt
      const userMsg: XerebroChatMessage = { role: 'user', content: text }
      setMessages([userMsg])
      const historyForRequest: XerebroChatMessage[] = []
      const res = await doChat(text, historyForRequest, context)
      if (res) {
        setMessages([
          userMsg,
          { role: 'assistant', content: res.response || res.error || '' },
        ])
      }
      return
    }

    const newMessages: XerebroChatMessage[] = [...messages]
    if (context) {
      // Analyze-this-page mode: not appended to visible chat, single-shot
      setAnalyzing(true)
      const res = await doChat(text, messages, context)
      setAnalyzing(false)
      if (res) {
        setMessages([
          ...newMessages,
          { role: 'user', content: `Analyze page: ${(context.url as string) || ''}` },
          { role: 'assistant', content: res.response || res.error || '' },
        ])
      }
      return
    }

    const userMsg: XerebroChatMessage = { role: 'user', content: text }
    const next = [...newMessages, userMsg]
    setMessages(next)
    setInput('')
    setLoading(true)
    const historyForRequest = messages // prior history before this turn
    const res = await doChat(text, historyForRequest, undefined)
    setLoading(false)
    if (res) {
      setMessages([
        ...next,
        { role: 'assistant', content: res.response || res.error || '' },
      ])
    }
  }

  async function doChat(
    prompt: string,
    history: XerebroChatMessage[],
    context?: Record<string, unknown>,
  ) {
    try {
      const res = await xerebroChat({
        prompt,
        model,
        system_prompt: systemPrompt.trim() || undefined,
        temperature,
        max_tokens: maxTokens,
        history,
        context,
      })
      if (res.tokens_used) setTotalTokens((t) => t + res.tokens_used)
      return res
    } catch (e: any) {
      return {
        success: false,
        response: '',
        model,
        tokens_used: 0,
        error: e?.message || 'Network error — is the API server running?',
      }
    }
  }

  function clearChat() {
    setMessages([])
    setTotalTokens(0)
    setInput('')
  }

  function handleAnalyze() {
    const url = analyzeUrl.trim()
    if (!url) return
    sendMessage(
      'Analyze this page in detail. Extract the main topic, key entities ' +
        '(people, organizations, products, prices), and provide a concise summary.',
      { url },
    )
  }

  const estTokens = (str: string) => Math.ceil((str?.length || 0) / 4)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Xerebro AI Brain</h1>
          <p className="text-sm text-surface-500 mt-1">
            Chat directly with your local LLM — sovereign, private compute
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={clearChat}>
            <Trash2 className="w-4 h-4" />
            Clear
          </Button>
          <Button variant="secondary" onClick={() => setShowSettings(!showSettings)}>
            <Settings2 className="w-4 h-4" />
            Settings
          </Button>
          <span
            className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border ${
              models.available
                ? 'bg-success-500/10 text-success-400 border-success-500/20'
                : 'bg-warning-500/10 text-warning-400 border-warning-500/20'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                models.available ? 'bg-success-400' : 'bg-warning-400'
              }`}
            />
            {healthLoading ? 'Checking…' : models.available ? 'Brain Online' : 'Ollama Offline'}
          </span>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <Card className="glow-blue">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="mt-2 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 focus:outline-none focus:border-primary-600/50"
              >
                {models.models.length > 0 ? (
                  models.models.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name}
                      {m.size ? ` (${(m.size / 1e9).toFixed(1)}GB)` : ''}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="llama3.2">llama3.2</option>
                    <option value="mistral">mistral</option>
                    <option value="gemma2">gemma2</option>
                  </>
                )}
              </select>
              {!models.available && (
                <p className="mt-2 text-xs text-warning-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Ollama unreachable — install it and run{' '}
                  <code className="px-1 py-0.5 bg-surface-800 rounded">ollama pull llama3.2</code>
                </p>
              )}
            </div>
            <div>
              <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">
                Max tokens: <span className="text-primary-400">{maxTokens}</span>
              </label>
              <input
                type="range"
                min={128}
                max={4096}
                step={128}
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="mt-3 w-full accent-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">
                  Temperature: <span className="text-primary-400">{temperature.toFixed(2)}</span>
                </label>
                <span className="text-[10px] text-surface-600">deterministic ↔ creative</span>
              </div>
              <input
                type="range"
                min={0}
                max={2}
                step={0.05}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
                className="mt-2 w-full accent-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-medium text-surface-400 uppercase tracking-wider">
                System prompt
              </label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={3}
                className="mt-2 w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 focus:outline-none focus:border-primary-600/50 resize-none"
                placeholder="Define Xerebro's role and behaviour…"
              />
              <div className="text-right text-[10px] text-surface-600 mt-1">
                ~{estTokens(systemPrompt)} tokens
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Analyze this page */}
      <Card className="glow-purple">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-600/20 flex items-center justify-center flex-shrink-0">
            <Globe className="w-4 h-4 text-accent-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-surface-200">Analyze this page</p>
            <p className="text-xs text-surface-500">
              Paste a URL and have Xerebro scrape &amp; reason over the page content
            </p>
          </div>
          <input
            type="text"
            value={analyzeUrl}
            onChange={(e) => setAnalyzeUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-accent-500/50"
          />
          <Button onClick={handleAnalyze} disabled={analyzing || !analyzeUrl.trim()}>
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
            {analyzing ? 'Analyzing…' : 'Analyze'}
          </Button>
        </div>
      </Card>

      {/* Chat window */}
      <Card className="glow-blue p-0 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-surface-800">
          <div className="flex items-center gap-2 text-xs text-surface-500">
            <Brain className="w-4 h-4 text-primary-400" />
            Session with {model}
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-surface-500">
              <Zap className="w-3.5 h-3.5 text-warning-400" />
              <span className="text-surface-400 font-medium">{totalTokens}</span> tokens used
            </span>
            <span className="text-surface-600">{messages.length} messages</span>
          </div>
        </div>

        <div className="h-[420px] overflow-y-auto px-5 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Brain className="w-12 h-12 text-surface-700" />
              <p className="mt-3 text-sm font-medium text-surface-400">Talk to Xerebro</p>
              <p className="text-xs text-surface-600 mt-1 max-w-sm">
                Ask it to analyze data, draft a scraping strategy, or reason over scraped page
                content. Everything runs on your own hardware.
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-md'
                    : 'bg-surface-800 text-surface-200 rounded-bl-md'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-surface-800 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                <span className="text-xs text-surface-500">Xerebro is thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-5 py-3 border-t border-surface-800">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              placeholder="Ask Xerebro anything…"
              className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-sm text-surface-200 placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30"
            />
            <Button onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>
              <Send className="w-4 h-4" />
              Send
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
