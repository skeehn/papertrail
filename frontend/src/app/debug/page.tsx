"use client"

import { useState } from 'react'
import { useMemories, useCreateMemory } from '@/hooks/use-memory-persistence'
import { Button } from '@/components/ui/button'

export default function DebugPage() {
  const { data: memories, isLoading } = useMemories()
  const createMemory = useCreateMemory()
  const [testMessage, setTestMessage] = useState('Hello, this is a test message!')

  const createTestMemory = () => {
    const memory = {
      content: testMessage,
      metadata: {
        type: 'user_message' as const,
        conversation_id: `test_${Date.now()}`,
        entities: ['test', 'debug'],
        topics: ['testing'],
      }
    }
    
    console.log('Creating test memory:', memory)
    createMemory.mutate(memory)
  }

  const checkLocalStorage = () => {
    const stored = localStorage.getItem('papertrail_memories')
    const conversation = localStorage.getItem('papertrail_conversation')
    console.log('localStorage memories:', stored)
    console.log('localStorage conversation:', conversation)
    alert(`Memories: ${stored ? JSON.parse(stored).length : 0} items\nConversation: ${conversation ? JSON.parse(conversation).length : 0} messages`)
  }

  const clearStorage = () => {
    localStorage.clear()
    window.location.reload()
  }

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Debug Memory System</h1>
      
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Memories ({isLoading ? 'loading...' : memories?.length || 0})</h2>
        {memories?.map((memory, i) => (
          <div key={memory.id} className="p-2 border rounded">
            <div className="text-sm text-gray-600">{memory.metadata.type}</div>
            <div>{memory.content.slice(0, 100)}...</div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <input 
          value={testMessage}
          onChange={(e) => setTestMessage(e.target.value)}
          className="w-full p-2 border rounded"
          placeholder="Test message content"
        />
        <div className="flex gap-2">
          <Button onClick={createTestMemory}>Create Test Memory</Button>
          <Button onClick={checkLocalStorage} variant="outline">Check localStorage</Button>
          <Button onClick={clearStorage} variant="destructive">Clear All</Button>
        </div>
      </div>
    </div>
  )
}