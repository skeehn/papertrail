import { useEffect, useRef, useState, useCallback } from 'react'

export type WebSocketMessageType =
  | 'connection_ack'
  | 'heartbeat'
  | 'error'
  | 'processing_start'
  | 'processing_update'
  | 'processing_complete'
  | 'processing_error'
  | 'agent_response'
  | 'agent_thinking'
  | 'agent_error'
  | 'graph_update'
  | 'graph_node_added'
  | 'graph_edge_added'
  | 'notification'

export interface WebSocketMessage {
  type: WebSocketMessageType
  data: Record<string, any>
  timestamp: string
}

interface UseWebSocketOptions {
  url?: string
  autoConnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  connectionId: string | null
  sendMessage: (type: string, data: Record<string, any>) => void
  subscribe: (topic: string) => void
  unsubscribe: (topic: string) => void
  lastMessage: WebSocketMessage | null
  error: string | null
  connect: () => void
  disconnect: () => void
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [connectionId, setConnectionId] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const subscriptionsRef = useRef<Set<string>>(new Set())

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        // WebSocket connected
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)

          // Handle connection acknowledgment
          if (message.type === 'connection_ack') {
            setConnectionId(message.data.connection_id || null)
          }

          // Handle heartbeat
          if (message.type === 'heartbeat') {
            // Optionally send pong response
            ws.send(JSON.stringify({ type: 'pong' }))
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        // WebSocket error event doesn't provide much detail
        // The actual error will be in onclose with a code
        console.warn('WebSocket error event:', event)
        // Don't set error here - wait for onclose to get the actual error code
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        setConnectionId(null)

        // Declare errorMessage outside the if block so it's accessible everywhere
        let errorMessage: string | null = null

        // Provide more detailed error messages based on close code
        if (event.code !== 1000) { // 1000 is normal closure
          errorMessage = 'WebSocket connection closed'
          if (event.code === 1006) {
            errorMessage = 'WebSocket connection failed. Is the backend running?'
          } else if (event.code === 1001) {
            errorMessage = 'WebSocket endpoint not found'
          } else if (event.code === 1002) {
            errorMessage = 'WebSocket protocol error'
          } else if (event.code === 1003) {
            errorMessage = 'WebSocket unsupported data type'
          } else if (event.code === 1011) {
            errorMessage = 'WebSocket server error'
          } else if (event.code === 1012) {
            errorMessage = 'WebSocket service restarting'
          }
          
          // Only set error if we're not going to reconnect
          if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
            setError(`${errorMessage} (code: ${event.code})`)
          } else {
            console.warn(`WebSocket closed (code: ${event.code}), reconnecting...`)
          }
        }

        // Attempt to reconnect if not manually disconnected
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Reconnecting WebSocket (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`)
            connect()
          }, reconnectInterval)
        } else {
          if (!errorMessage) {
            setError('Max reconnection attempts reached')
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
    }
  }, [url, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    reconnectAttemptsRef.current = maxReconnectAttempts // Prevent reconnection

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setConnectionId(null)
    subscriptionsRef.current.clear()
  }, [maxReconnectAttempts])

  const sendMessage = useCallback(
    (type: string, data: Record<string, any>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type, data }))
      } else {
        console.warn('WebSocket is not connected')
      }
    },
    []
  )

  const subscribe = useCallback(
    (topic: string) => {
      if (!subscriptionsRef.current.has(topic)) {
        subscriptionsRef.current.add(topic)
        sendMessage('subscribe', { topic })
      }
    },
    [sendMessage]
  )

  const unsubscribe = useCallback(
    (topic: string) => {
      if (subscriptionsRef.current.has(topic)) {
        subscriptionsRef.current.delete(topic)
        sendMessage('unsubscribe', { topic })
      }
    },
    [sendMessage]
  )

  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    isConnected,
    connectionId,
    sendMessage,
    subscribe,
    unsubscribe,
    lastMessage,
    error,
    connect,
    disconnect,
  }
}
