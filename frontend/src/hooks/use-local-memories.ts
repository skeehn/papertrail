"use client"

import { useState, useEffect } from 'react'

interface LocalMemory {
  id: string
  content: string
  metadata: {
    type: 'user_message' | 'assistant_message' | 'conversation_summary'
    timestamp: string
    conversation_id?: string
    entities?: string[]
    topics?: string[]
  }
  created_at: string
  updated_at: string
}

const MEMORIES_KEY = 'papertrail_memories'

export const useLocalMemories = () => {
  const [memories, setMemories] = useState<LocalMemory[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Load memories from localStorage
  useEffect(() => {
    const loadMemories = () => {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          const stored = localStorage.getItem(MEMORIES_KEY)
          const parsedMemories = stored ? JSON.parse(stored) : []
          setMemories(parsedMemories)
          console.log('📚 Loaded', parsedMemories.length, 'memories from localStorage')
        }
      } catch (error) {
        console.error('Error loading memories from localStorage:', error)
        setMemories([])
      } finally {
        setIsLoading(false)
      }
    }

    loadMemories()
  }, [])

  // Save memories to localStorage
  const saveMemories = (newMemories: LocalMemory[]) => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(MEMORIES_KEY, JSON.stringify(newMemories))
        setMemories(newMemories)
        console.log('💾 Saved', newMemories.length, 'memories to localStorage')
      }
    } catch (error) {
      console.error('Error saving memories to localStorage:', error)
    }
  }

  // Add a new memory
  const addMemory = (content: string, metadata: LocalMemory['metadata']) => {
    const newMemory: LocalMemory = {
      id: `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content,
      metadata: {
        ...metadata,
        timestamp: new Date().toISOString(),
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    // Check for duplicates
    const isDuplicate = memories.some(existing => 
      existing.content === content && 
      existing.metadata.type === metadata.type &&
      Math.abs(new Date(existing.created_at).getTime() - new Date().getTime()) < 5000
    )

    if (isDuplicate) {
      console.log('🔄 Skipping duplicate memory')
      return null
    }

    const updatedMemories = [...memories, newMemory]
    saveMemories(updatedMemories)
    return newMemory
  }

  // Clear all memories
  const clearMemories = () => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.removeItem(MEMORIES_KEY)
        setMemories([])
        console.log('🗑️ Cleared all memories')
      }
    } catch (error) {
      console.error('Error clearing memories:', error)
    }
  }

  // Search memories
  const searchMemories = (query: string, limit: number = 5) => {
    const queryLower = query.toLowerCase()
    const results = memories
      .filter(memory => 
        memory.content.toLowerCase().includes(queryLower) ||
        memory.metadata.entities?.some(entity => 
          entity.toLowerCase().includes(queryLower)
        ) ||
        memory.metadata.topics?.some(topic => 
          topic.toLowerCase().includes(queryLower)
        )
      )
      .slice(0, limit)
    
    return results
  }

  return {
    memories,
    isLoading,
    addMemory,
    clearMemories,
    searchMemories,
    count: memories.length
  }
}