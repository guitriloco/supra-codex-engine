export interface Pipeline {
  id: string
  name: string
  status: 'running' | 'paused' | 'idle' | 'error'
  nodes: number
  tasks: number
  uptime: string
}

export interface Node {
  name: string
  region: string
  status: 'online' | 'offline'
  cpu: number
  mem: number
  tasks: number
}

export interface PipelineRunResult {
  id: string
  url: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  extractedData?: Record<string, unknown>
  error?: string
  createdAt: string
}

export interface MarketplaceModule {
  id: string
  name: string
  description: string
  author: string
  rating: number
  downloads: number
  price: number
  price_label: string
  category: string
  version: string
  install_count: number
  features: string[]
  requirements: string[]
  installed: boolean
}

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const body = await response.text().catch(() => '')
      throw new ApiError(response.status, `API request failed: ${response.statusText}`, body)
    }

    return await response.json()
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError(0, 'Network error — is the API server running?', String(err))
  }
}

export class ApiError extends Error {
  status: number
  body: string

  constructor(status: number, message: string, body: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

/** Submit a new pipeline job to scrape a URL */
export async function submitPipeline(url: string): Promise<PipelineRunResult> {
  return request<PipelineRunResult>('/api/pipelines', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

/** Get the current status of a pipeline run */
export async function getPipelineStatus(id: string): Promise<PipelineRunResult> {
  return request<PipelineRunResult>(`/api/pipelines/${id}`)
}

/** List all registered compute nodes */
export async function listNodes(): Promise<Node[]> {
  return request<Node[]>('/api/nodes')
}

/** Get node details by name */
export async function getNode(name: string): Promise<Node> {
  return request<Node>(`/api/nodes/${name}`)
}

/** List all pipelines */
export async function listPipelines(): Promise<Pipeline[]> {
  return request<Pipeline[]>('/api/pipelines')
}

/** Pause a running pipeline */
export async function pausePipeline(id: string): Promise<void> {
  await request(`/api/pipelines/${id}/pause`, { method: 'POST' })
}

/** Resume a paused pipeline */
export async function resumePipeline(id: string): Promise<void> {
  await request(`/api/pipelines/${id}/resume`, { method: 'POST' })
}

// ──────────────────────────────────────────────────────────────────────────────
// Marketplace
// ──────────────────────────────────────────────────────────────────────────────

/** List all available marketplace modules */
export async function listMarketplaceModules(): Promise<MarketplaceModule[]> {
  return request<MarketplaceModule[]>('/api/marketplace/modules')
}

/** Get details for a specific marketplace module */
export async function getMarketplaceModule(id: string): Promise<MarketplaceModule> {
  return request<MarketplaceModule>(`/api/marketplace/modules/${id}`)
}

/** Install a marketplace module */
export async function installModule(moduleId: string): Promise<{ message: string; module_id: string }> {
  return request(`/api/marketplace/modules/${moduleId}/install`, { method: 'POST' })
}

/** Uninstall a marketplace module */
export async function uninstallModule(moduleId: string): Promise<{ message: string; module_id: string }> {
  return request(`/api/marketplace/modules/${moduleId}/uninstall`, { method: 'POST' })
}

/** List all installed modules */
export async function listInstalledModules(): Promise<MarketplaceModule[]> {
  return request<MarketplaceModule[]>('/api/marketplace/installed')
}

// ──────────────────────────────────────────────────────────────────────────────
// Xerebro AI Brain Panel
// ──────────────────────────────────────────────────────────────────────────────

export interface XerebroModelInfo {
  name: string
  size: number
  modified_at: string
}

export interface XerebroModelsResponse {
  available: boolean
  models: XerebroModelInfo[]
  default_model: string
  error?: string
}

export interface XerebroChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface XerebroChatRequest {
  prompt: string
  model?: string
  system_prompt?: string
  temperature?: number
  max_tokens?: number
  history?: XerebroChatMessage[]
  context?: Record<string, unknown>
}

export interface XerebroChatResponse {
  success: boolean
  response: string
  model: string
  tokens_used: number
  error?: string
}

/** List Ollama models available to the local Xerebro brain */
export async function listXerebroModels(): Promise<XerebroModelsResponse> {
  return request<XerebroModelsResponse>('/api/v1/xerebro/models')
}

/** Send a chat message to the Xerebro brain and get a response */
export async function xerebroChat(req: XerebroChatRequest): Promise<XerebroChatResponse> {
  return request<XerebroChatResponse>('/api/v1/xerebro/chat', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

// ──────────────────────────────────────────────────────────────────────────────
// Visual Pipeline Builder
// ──────────────────────────────────────────────────────────────────────────────

export interface PipelineStepDef {
  id: string
  type: 'scrape' | 'enrich' | 'filter' | 'transform' | 'export'
  name: string
  config: Record<string, any>
}

export interface PipelineDefinition {
  id?: string
  name: string
  description: string
  steps: PipelineStepDef[]
  created_at?: string
  updated_at?: string
}

export interface PipelineSummary {
  id: string
  name: string
  description: string
  steps: number
  types: string[]
  updated_at: string
}

export interface PipelineRunStepResult {
  step_id: string
  type: string
  status: 'success' | 'failed' | 'skipped'
  output?: any
  summary?: string
  error?: string
}

export interface PipelineRunResult {
  id: string
  name: string
  status: string
  duration_ms: number
  steps: PipelineRunStepResult[]
  result?: any
}

/** Save (create or update) a pipeline definition */
export async function savePipelineDefinition(pipeline: PipelineDefinition): Promise<{ id: string; message: string; pipeline: PipelineDefinition }> {
  return request('/api/v1/pipelines', {
    method: 'POST',
    body: JSON.stringify(pipeline),
  })
}

/** List saved pipeline definitions */
export async function listPipelineDefinitions(): Promise<PipelineSummary[]> {
  return request<PipelineSummary[]>('/api/v1/pipelines')
}

/** Get a saved pipeline definition by id */
export async function getPipelineDefinition(id: string): Promise<PipelineDefinition> {
  return request<PipelineDefinition>(`/api/v1/pipelines/${id}`)
}

/** Delete a saved pipeline definition */
export async function deletePipelineDefinition(id: string): Promise<{ message: string; id: string }> {
  return request(`/api/v1/pipelines/${id}`, { method: 'DELETE' })
}

/** Execute a saved pipeline definition */
export async function runPipelineDefinition(id: string): Promise<PipelineRunResult> {
  return request<PipelineRunResult>(`/api/v1/pipelines/${id}/run`, { method: 'POST' })
}