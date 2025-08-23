import { NextRequest, NextResponse } from 'next/server'

// This is a server-side proxy to work with localStorage-style data
// Since server-side can't access localStorage, we'll use a simple fallback

export async function GET() {
  try {
    // For now, return empty array and let client handle localStorage
    // This triggers the useMemories hook to use localStorage fallback
    return NextResponse.json([])
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch local memories' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Since we can't directly manipulate localStorage from server-side,
    // we'll return a success response and let the client handle storage
    // The client-side memory persistence will handle localStorage
    
    const memory = {
      id: `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    
    return NextResponse.json(memory)
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create local memory' },
      { status: 500 }
    )
  }
}