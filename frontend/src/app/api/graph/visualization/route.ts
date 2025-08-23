import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const layout = searchParams.get('layout') || 'force'
    const node_size = searchParams.get('node_size') || 'degree'
    const edge_weight = searchParams.get('edge_weight') || 'strength'
    
    const queryParams = new URLSearchParams({
      layout,
      node_size,
      edge_weight,
    })
    
    const response = await fetch(`${BACKEND_URL}/api/v1/graph/visualization?${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching graph visualization data:', error)
    return NextResponse.json(
      { error: 'Failed to fetch graph visualization data' },
      { status: 500 }
    )
  }
}