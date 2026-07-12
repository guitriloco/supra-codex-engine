import { useEffect, useRef, useState, useCallback } from 'react'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface PipelineEvent {
  type: 'task_update' | 'reasoning' | 'result' | 'error' | 'status'
  pipelineId: string
  payload: Record<string, unknown>
  timestamp: string
}

interface UseWebSocketOptions {
  url?: string
  onMessage?: (event: PipelineEvent) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/pipelines',
    onMessage,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options

  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [lastMessage, setLastMessage] = useState<PipelineEvent | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        setStatus('connected')
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event: MessageEvent) => {
        try {
          const parsed: PipelineEvent = JSON.parse(event.data)
          setLastMessage(parsed)
          onMessage?.(parsed)
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onerror = () => {
        if (!mountedRef.current) return
        setStatus('error')
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setStatus('disconnected')
        wsRef.current = null

        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1
          reconnectTimer.current = setTimeout(connect, reconnectInterval)
        }
      }
    } catch {
      setStatus('error')
    }
  }, [url, onMessage, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    reconnectAttempts.current = maxReconnectAttempts // Prevent auto-reconnect
    wsRef.current?.close()
    wsRef.current = null
    setStatus('disconnected')
  }, [maxReconnectAttempts])

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
      wsRef.current?.close()
    }
  }, [connect])

  return { status, lastMessage, connect, disconnect, send, isConnected: status === 'connected' }
}