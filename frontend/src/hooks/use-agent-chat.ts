import { useState } from 'react'

export type AgentType = 'synthesizer' | 'critic' | 'connector' | 'reasoning'

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agentType?: AgentType
  timestamp?: number
}

export interface AgentResponse {
  response: string
  sources: Array<{ paper_id: string; title: string; excerpt: string }>
  confidence: number
  agent_type: AgentType
  processing_time: number
}

interface UseAgentChatReturn {
  messages: AgentMessage[]
  isLoading: boolean
  error: string | null
  selectedAgent: AgentType
  setSelectedAgent: (agent: AgentType) => void
  sendMessage: (query: string) => Promise<void>
  clearMessages: () => void
}

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('synthesizer')

  const sendMessage = async (query: string) => {
    if (!query.trim()) return

    const userMessage: AgentMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)
    setError(null)

    try {
      let response: Response
      let data: AgentResponse

      // Reasoning agent uses a different endpoint
      if (selectedAgent === 'reasoning') {
        response = await fetch('/api/insights/reasoning', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            context: null,
          }),
        })

        if (!response.ok) {
          throw new Error('Failed to get reasoning response')
        }

        const reasoningData = await response.json()
        // Transform reasoning response to match AgentResponse format
        data = {
          response: reasoningData.answer || reasoningData.response || 'No response generated',
          sources: reasoningData.sources || [],
          confidence: reasoningData.confidence || 0.8,
          agent_type: 'reasoning',
          processing_time: reasoningData.processing_time || 0,
        }
      } else {
        response = await fetch('/api/agents/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            agent_type: selectedAgent,
            query,
            paper_ids: [],
          }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || errorData.error || 'Failed to get agent response')
        }

        data = await response.json()
      }

      const assistantMessage: AgentMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        agentType: data.agent_type,
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
      setError(errorMessage)
      // Don't throw - let the UI handle the error
    } finally {
      setIsLoading(false)
    }
  }

  const clearMessages = () => {
    setMessages([])
    setError(null)
  }

  return {
    messages,
    isLoading,
    error,
    selectedAgent,
    setSelectedAgent,
    sendMessage,
    clearMessages,
  }
}
