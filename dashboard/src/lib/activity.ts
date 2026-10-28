import type { PipelineEvent } from '@/hooks/useWebSocket'
import type { Node, Pipeline } from '@/services/api'

/** Where an activity row came from. Drives the icon + accent colour. */
export type ActivityKind = 'pipeline' | 'node' | 'install' | 'system'

/** Visual severity of an activity row. */
export type ActivityTone = 'ok' | 'warn' | 'error' | 'idle'

export interface ActivityItem {
  id: string
  kind: ActivityKind
  title: string
  detail: string
  /** Epoch millis. `0` means "state snapshot" with no known timestamp. */
  timestamp: number
  /** True when the row describes something happening right now. */
  live: boolean
  tone: ActivityTone
  /** Optional in-app route the row links to. */
  href?: string
}

function truncate(value: unknown, max = 90): string {
  const text = typeof value === 'string' ? value : String(value ?? '')
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function pipelineStatusTone(status: Pipeline['status']): ActivityTone {
  switch (status) {
    case 'running':
      return 'ok'
    case 'paused':
      return 'warn'
    case 'error':
      return 'error'
    default:
      return 'idle'
  }
}

function pipelineStatusText(status: Pipeline['status']): string {
  switch (status) {
    case 'running':
      return 'is running'
    case 'paused':
      return 'is paused'
    case 'error':
      return 'failed'
    default:
      return 'is idle'
  }
}

/**
 * State snapshot pulled from the REST API. These rows have no server
 * timestamp, so they render with their status label rather than a
 * relative time.
 */
export function snapshotActivity(pipelines: Pipeline[], nodes: Node[]): ActivityItem[] {
  const nodeRows: ActivityItem[] = nodes.map((node) => ({
    id: `node:${node.name}`,
    kind: 'node',
    title: `Node ${node.name} is ${node.status}`,
    detail: `${node.region} · ${node.cpu}% CPU · ${node.mem}% MEM · ${node.tasks} tasks`,
    timestamp: 0,
    live: node.status === 'online',
    tone: node.status === 'online' ? 'ok' : 'idle',
    href: '/nodes',
  }))

  const pipelineRows: ActivityItem[] = pipelines.map((pipeline) => ({
    id: `pipeline:${pipeline.id}`,
    kind: 'pipeline',
    title: `Pipeline "${pipeline.name}" ${pipelineStatusText(pipeline.status)}`,
    detail: `${pipeline.tasks} tasks · ${pipeline.nodes} node${pipeline.nodes === 1 ? '' : 's'} · up ${pipeline.uptime}`,
    timestamp: 0,
    live: pipeline.status === 'running',
    tone: pipelineStatusTone(pipeline.status),
    href: '/pipelines',
  }))

  return [...pipelineRows, ...nodeRows]
}

/**
 * Translate a live WebSocket event into a feed row.
 * Returns `null` for events that are not worth surfacing (pongs, noise).
 */
export function eventToActivity(event: PipelineEvent): ActivityItem | null {
  const payload = event.payload ?? {}
  const pipelineRef = event.pipelineId ? `pipeline ${event.pipelineId.slice(0, 8)}` : 'the engine'
  const timestamp = Date.parse(event.timestamp) || Date.now()
  const id = `ws:${event.timestamp}:${event.type}:${event.pipelineId}:${String(payload.step ?? '')}`

  switch (event.type) {
    case 'status': {
      const nodeEvent = payload.event
      if (nodeEvent === 'node_registered' || nodeEvent === 'node_re-registered') {
        const hostname = String(payload.hostname ?? payload.node_id ?? 'unknown')
        return {
          id,
          kind: 'node',
          title: `Node ${hostname} came online`,
          detail: `Registered with the cluster as ${truncate(payload.node_id ?? hostname, 40)}`,
          timestamp,
          live: true,
          tone: 'ok',
          href: '/nodes',
        }
      }
      if (payload.engine) {
        const online = payload.xerebro === true
        return {
          id,
          kind: 'system',
          title: `WraithEngine ${String(payload.engine)}`,
          detail: `Xerebro ${online ? 'available' : 'offline'} · API v${String(payload.version ?? '—')}`,
          timestamp,
          live: payload.engine === 'running',
          tone: payload.engine === 'running' ? 'ok' : 'idle',
        }
      }
      return null
    }

    case 'task_update': {
      const step = String(payload.step ?? 'task')
      const state = String(payload.status ?? 'updated')
      const detail =
        typeof payload.url === 'string'
          ? payload.url
          : typeof payload.title === 'string'
            ? truncate(payload.title, 70)
            : typeof payload.node === 'string'
              ? `on node ${payload.node}`
              : pipelineRef
      return {
        id,
        kind: 'pipeline',
        title: `Step "${step}" ${state}`,
        detail: `${pipelineRef} · ${detail}`,
        timestamp,
        live: state === 'running' || state === 'dispatched',
        tone: state === 'success' ? 'ok' : 'warn',
        href: '/pipelines/live',
      }
    }

    case 'reasoning':
      return {
        id,
        kind: 'pipeline',
        title: 'Xerebro is analysing',
        detail: `${pipelineRef} · step "${String(payload.step ?? 'analysis')}"`,
        timestamp,
        live: true,
        tone: 'warn',
        href: '/xerebro',
      }

    case 'result':
      return {
        id,
        kind: 'pipeline',
        title: `Step "${String(payload.step ?? 'result')}" completed`,
        detail: truncate(payload.analysis ?? pipelineRef, 100),
        timestamp,
        live: false,
        tone: 'ok',
        href: '/pipelines/live',
      }

    case 'error':
      return {
        id,
        kind: 'pipeline',
        title: `Error in step "${String(payload.step ?? 'pipeline')}"`,
        detail: truncate(payload.error ?? 'Unknown error', 100),
        timestamp,
        live: false,
        tone: 'error',
        href: '/pipelines/live',
      }

    default:
      return null
  }
}

/** Human label used when a row has no timestamp (API snapshot rows). */
export function toneLabel(item: ActivityItem): string {
  switch (item.tone) {
    case 'ok':
      return 'Live'
    case 'warn':
      return 'Active'
    case 'error':
      return 'Failed'
    default:
      return 'Idle'
  }
}
