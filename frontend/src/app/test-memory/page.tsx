"use client"

import { useEffect, useState } from 'react'
import { useMemories, useConversationPersistence } from '@/hooks/use-memory-persistence'

export default function TestMemoryPage() {
  const { data: memories } = useMemories()
  const { loadConversation } = useConversationPersistence()
  const [testResults, setTestResults] = useState<string[]>([])

  useEffect(() => {
    const runTests = async () => {
      const results: string[] = []
      
      // Test 1: Load memories
      results.push(`✓ Memories loaded: ${memories ? memories.length : 0} found`)
      
      // Test 2: Test localStorage
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem('test-key', 'test-value')
          const retrieved = localStorage.getItem('test-key')
          results.push(retrieved === 'test-value' ? '✓ localStorage works' : '✗ localStorage failed')
          localStorage.removeItem('test-key')
        } catch (e) {
          results.push('✗ localStorage error: ' + String(e))
        }
      }
      
      // Test 3: Load conversation
      try {
        const conversation = loadConversation()
        results.push(`✓ Conversation loaded: ${conversation.length} messages`)
      } catch (e) {
        results.push('✗ Conversation load error: ' + String(e))
      }
      
      setTestResults(results)
    }
    
    runTests()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memories])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Memory System Test</h1>
      <div className="space-y-2">
        {testResults.map((result, i) => (
          <div key={i} className={result.startsWith('✓') ? 'text-green-600' : 'text-red-600'}>
            {result}
          </div>
        ))}
      </div>
      
      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-2">Current Memories:</h2>
        {memories && memories.length > 0 ? (
          <div className="space-y-2">
            {memories.map(memory => (
              <div key={memory.id} className="p-2 border rounded">
                <div className="font-medium">{memory.content.slice(0, 100)}</div>
                <div className="text-sm text-gray-500">Type: {memory.metadata.type}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500">No memories found</div>
        )}
      </div>
    </div>
  )
}