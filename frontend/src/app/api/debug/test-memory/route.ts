import { NextResponse } from 'next/server'

export async function POST() {
  // Create a test memory directly in localStorage (simulated)
  const testMemory = {
    id: `test_${Date.now()}`,
    content: 'This is a test memory to verify the system works.',
    metadata: {
      type: 'user_message' as const,
      timestamp: new Date().toISOString(),
      conversation_id: 'test_conv_123',
      entities: ['test', 'memory', 'system'],
      topics: ['testing', 'debugging']
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }

  // Return the test memory so frontend can save it
  return NextResponse.json({
    success: true,
    memory: testMemory,
    instructions: 'Call /api/memories with this memory data to test the system'
  })
}