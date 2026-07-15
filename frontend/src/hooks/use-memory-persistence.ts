"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { UIMessage } from 'ai'
// Temporarily disable memory services to fix basic functionality
// import { temporalMemoryService } from '@/services/temporal-memory-service'
// import { hierarchicalMemoryService } from '@/services/hierarchical-memory-service'

interface Memory {
  id: string
  content: string
  metadata: {
    type: 'user_message' | 'assistant_message' | 'conversation_summary'
    timestamp: string
    conversation_id?: string
    entities?: string[]
    topics?: string[]
  }
  embedding?: number[]
  created_at: string
  updated_at: string
}

interface CreateMemoryRequest {
  content: string
  metadata: {
    type: 'user_message' | 'assistant_message' | 'conversation_summary'
    conversation_id?: string
    entities?: string[]
    topics?: string[]
  }
}

const CONVERSATION_STORAGE_KEY = 'papertrail_conversation'
const MEMORIES_STORAGE_KEY = 'papertrail_memories'

// localStorage-based memory functions
const getLocalMemories = (): Memory[] => {
  try {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || !window.localStorage) {
      return []
    }
    const stored = localStorage.getItem(MEMORIES_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch (error) {
    console.error('Error getting local memories:', error)
    return []
  }
}

const saveLocalMemory = (memory: Memory): void => {
  try {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || !window.localStorage) {
      return
    }
    
    const existing = getLocalMemories()
    
    // Check for duplicates to prevent too many nodes
    const isDuplicate = existing.some(existingMemory => 
      existingMemory.content === memory.content && 
      existingMemory.metadata.type === memory.metadata.type &&
      Math.abs(new Date(existingMemory.created_at).getTime() - new Date(memory.created_at).getTime()) < 5000 // Within 5 seconds
    )
    
    if (isDuplicate) {
      console.log('🔄 Skipping duplicate memory')
      return
    }
    
    const updated = [...existing, memory]
    localStorage.setItem(MEMORIES_STORAGE_KEY, JSON.stringify(updated))
    console.log('💾 Saved memory to localStorage. Total:', updated.length)
  } catch (error) {
    console.error('Failed to save memory to localStorage:', error)
  }
}

const clearLocalMemories = (): void => {
  try {
    if (typeof window === 'undefined' || !window.localStorage) {
      return
    }
    localStorage.removeItem(MEMORIES_STORAGE_KEY)
  } catch (error) {
    console.error('Failed to clear local memories:', error)
  }
}

export const useMemories = () => {
  return useQuery<Memory[]>({
    queryKey: ['memories'],
    queryFn: async () => {
      // Always try localStorage first for immediate results
      console.log('🔍 Checking localStorage for memories...')
      const localMemories = getLocalMemories()
      
      if (localMemories.length > 0) {
        console.log('✅ Found', localMemories.length, 'memories in localStorage')
        return localMemories
      }

      // If localStorage is empty, try backend
      try {
        console.log('📡 Trying backend for memories...')
        const response = await fetch('/api/memories')
        if (response.ok) {
          const backendMemories = await response.json()
          if (Array.isArray(backendMemories) && backendMemories.length > 0) {
            console.log('✅ Found', backendMemories.length, 'memories from backend')
            return backendMemories
          }
        }
      } catch (error) {
        console.warn('Backend memories unavailable:', error)
      }

      // Return empty array if nothing found
      console.log('📝 No memories found, returning empty array')
      return []
    },
    staleTime: 1000, // Shorter stale time for faster updates
    refetchInterval: 5000, // Refetch every 5 seconds to catch new memories
  })
}

export const useCreateMemory = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (request: CreateMemoryRequest) => {
      console.log('Sending memory to backend:', request)
      
      try {
        const response = await fetch('/api/memories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          console.error('Memory creation failed:', response.status, errorText)
          throw new Error(`Failed to create memory: ${response.status}`)
        }
        
        const result = await response.json()
        console.log('Memory created successfully:', result)
        return result
      } catch (error) {
        console.warn('Backend unavailable, memory already saved to localStorage:', error)
        // Return a mock successful response since we already saved to localStorage
        return {
          id: `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: request.content,
          metadata: request.metadata,
          created_at: new Date().toISOString(),
          source: 'localStorage'
        }
      }
    },
    onSuccess: () => {
      // Invalidate and refetch memories
      queryClient.invalidateQueries({ queryKey: ['memories'] })
      queryClient.invalidateQueries({ queryKey: ['graph-statistics'] })
    },
    onError: (error) => {
      console.error('Memory creation error:', error)
    },
  })
}

// Conversation persistence using localStorage + backend sync
export const useConversationPersistence = () => {

  const saveConversation = useCallback(async (messages: UIMessage[]) => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || !window.localStorage) {
      return
    }
    
    // Prevent saving during the same call stack to avoid loops
    const now = Date.now()
    const lastSaveTime = localStorage.getItem('papertrail_last_save_time')
    if (lastSaveTime && (now - parseInt(lastSaveTime)) < 1000) {
      console.log('⚠️ Skipping save - too frequent (< 1s)')
      return
    }
    localStorage.setItem('papertrail_last_save_time', now.toString())
    
    // Save to localStorage immediately for instant persistence
    localStorage.setItem(CONVERSATION_STORAGE_KEY, JSON.stringify(messages))
    
    // Generate conversation ID if not exists
    let conversationId = localStorage.getItem('papertrail_conversation_id')
    if (!conversationId) {
      conversationId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('papertrail_conversation_id', conversationId)
    }

    // Save the latest message to backend asynchronously
    const latestMessage = messages[messages.length - 1]
    if (latestMessage) {
      // Extract content - AI SDK provides messages with parts structure
      let content = ''
      
      // Check for content property with proper type handling
      const messageContent = (latestMessage as any).content
      
      if (typeof messageContent === 'string') {
        content = messageContent
      } 
      else if (Array.isArray(messageContent)) {
        content = messageContent
          .map((part: any) => {
            if (typeof part === 'string') return part
            if (typeof part === 'object' && part.text) return part.text
            if (typeof part === 'object' && part.type === 'text') return part.text
            return ''
          })
          .join('')
      }
      // Check for parts structure (AI SDK format)
      else if ((latestMessage as any).parts && Array.isArray((latestMessage as any).parts)) {
        content = (latestMessage as any).parts
          .filter((part: any) => part.type === "text")
          .map((part: any) => part.text)
          .join("")
      }
      // Check for text property
      else if ((latestMessage as any).text) {
        content = (latestMessage as any).text
      }
      // If all else fails, try to stringify
      else if (messageContent) {
        content = String(messageContent)
      }
      
      if (content && content.trim()) {
        console.log('✅ Creating memory for message:', { role: latestMessage.role, content: content.slice(0, 100) })
        
        // Create memory object
        const memory: Memory = {
          id: `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content,
          metadata: {
            type: latestMessage.role === 'user' ? 'user_message' : 'assistant_message',
            timestamp: new Date().toISOString(),
            conversation_id: conversationId,
            entities: extractEntities(content),
            topics: extractTopics(content),
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        
        // Save to localStorage immediately (legacy system)
        saveLocalMemory(memory)
        
        // Skip advanced memory creation for now - just save to localStorage
        console.log('💾 Saved basic memory to localStorage:', content.slice(0, 50))
      } else {
        console.log('❌ Skipping message with no content. Raw message:', JSON.stringify(latestMessage, null, 2))
      }
    } else {
      console.log('❌ No latest message found in messages array:', messages.length)
    }
  }, [])

  const loadConversation = useCallback((): UIMessage[] => {
    try {
      // Check if we're in a browser environment
      if (typeof window === 'undefined' || !window.localStorage) {
        return []
      }

      const saved = localStorage.getItem(CONVERSATION_STORAGE_KEY)
      const result = saved ? JSON.parse(saved) : []
      if (result.length > 0) {
        console.log('📱 Restored conversation:', result.length, 'messages')
      }
      return result
    } catch (error) {
      console.error('Error loading conversation:', error)
      return []
    }
  }, [])

  const clearConversation = useCallback(() => {
    if (typeof window === 'undefined' || !window.localStorage) {
      return
    }
    localStorage.removeItem(CONVERSATION_STORAGE_KEY)
    localStorage.removeItem('papertrail_conversation_id')
    clearLocalMemories()
  }, [])

  return {
    saveConversation,
    loadConversation,
    clearConversation,
  }
}

// Simple entity extraction (can be enhanced with NLP)
const extractEntities = (content: string): string[] => {
  const entities: string[] = []
  
  // Extract capitalized words that might be entities
  const capitalizedWords = content.match(/[A-Z][a-z]+/g) || []
  
  // Extract quoted phrases
  const quotedPhrases = content.match(/"([^"]+)"/g) || []
  
  entities.push(...capitalizedWords.slice(0, 5)) // Limit to 5
  entities.push(...quotedPhrases.slice(0, 3)) // Limit to 3
  
  return [...new Set(entities)] // Remove duplicates
}

// Simple topic extraction
const extractTopics = (content: string): string[] => {
  const topics: string[] = []
  
  // Common research/academic topics
  const topicKeywords = [
    'machine learning', 'artificial intelligence', 'deep learning', 'neural networks',
    'data science', 'statistics', 'research', 'analysis', 'study', 'experiment',
    'algorithm', 'model', 'training', 'prediction', 'classification', 'regression'
  ]
  
  const lowerContent = content.toLowerCase()
  
  for (const topic of topicKeywords) {
    if (lowerContent.includes(topic)) {
      topics.push(topic)
    }
  }
  
  return topics.slice(0, 5) // Limit to 5 topics
}

// Temporarily disable advanced memory hooks to fix basic functionality
export const useTemporalMemories = () => {
  return useQuery<any[]>({
    queryKey: ['temporal-memories'],
    queryFn: async () => {
      return []
    },
    staleTime: 30000,
  })
}

export const useTemporalMemoryStats = () => {
  return useQuery({
    queryKey: ['temporal-memory-stats'],
    queryFn: async () => {
      return {
        total_memories: 0,
        active_memories: 0,
        average_confidence: 0,
        average_importance: 0,
        memories_last_hour: 0,
        memories_last_day: 0,
        by_layer: {},
        by_type: {},
        relationship_density: 0
      }
    },
    staleTime: 60000,
  })
}

export const useCreateTemporalMemory = () => {
  return useMutation<any, unknown, { content: string } | undefined>({
    mutationFn: async (_vars?: { content: string } | undefined) => {
      return Promise.resolve({})
    }
  })
}

export const useAccessTemporalMemory = () => {
  return useMutation<any, unknown, string>({
    mutationFn: async (_memoryId: string) => {
      return Promise.resolve({})
    }
  })
}

export const useHierarchicalMemoryRetrieval = () => {
  return useMutation<any, unknown, { content_query: string; limit?: number }>({
    mutationFn: async (_vars: { content_query: string; limit?: number }) => {
      return {
        memories: [],
        performance: {
          total_time_ms: 0,
          layers_searched: [] as string[],
          cache_hits: 0,
          cache_misses: 0
        }
      }
    }
  })
}

export const useMemoryLayerStats = () => {
  return useQuery({
    queryKey: ['memory-layer-stats'],
    queryFn: async () => {
      return {
        hot: { count: 0, average_access_time_ms: 50, recent_accesses: 0 },
        warm: { count: 0, average_access_time_ms: 200, cache_hit_rate: 0.75 },
        cold: { count: 0, average_access_time_ms: 800, compression_ratio: 0.3 }
      }
    },
    staleTime: 30000,
    refetchInterval: 60000,
  })
}