import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // Try backend first
    const response = await fetch(`${BACKEND_URL}/api/v1/memories/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (response.ok) {
      const data = await response.json()
      
      // If backend returns data, use it
      if (Array.isArray(data) && data.length > 0) {
        return NextResponse.json(data)
      }
    }

    // Backend returned empty or failed - return empty array
    // The useMemories hook will handle localStorage fallback
    console.log('Backend memories empty, returning empty array for localStorage fallback')
    return NextResponse.json([])
    
  } catch (error) {
    console.error('Error fetching memories:', error)
    // Return empty array to trigger localStorage fallback
    return NextResponse.json([])
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    const response = await fetch(`${BACKEND_URL}/api/v1/memories/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error creating memory:', error)
    return NextResponse.json(
      { error: 'Failed to create memory' },
      { status: 500 }
    )
  }
}