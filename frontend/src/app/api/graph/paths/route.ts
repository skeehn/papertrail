import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const source = searchParams.get('source')
    const target = searchParams.get('target')
    const maxLength = searchParams.get('max_length') || '5'

    if (!source || !target) {
      return NextResponse.json(
        { error: 'Source and target parameters are required' },
        { status: 400 }
      )
    }

    const url = new URL(`${BACKEND_URL}/api/v1/graph/paths`)
    url.searchParams.set('source', source)
    url.searchParams.set('target', target)
    url.searchParams.set('max_length', maxLength)

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || 'Failed to find paths' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error finding paths:', error)
    return NextResponse.json(
      { error: 'Failed to find paths' },
      { status: 500 }
    )
  }
}
