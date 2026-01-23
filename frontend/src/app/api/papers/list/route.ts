import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const skip = searchParams.get('skip') || '0'
    const limit = searchParams.get('limit') || '20'
    const search = searchParams.get('search') || ''

    const url = new URL(`${BACKEND_URL}/api/v1/papers/`)
    url.searchParams.set('skip', skip)
    url.searchParams.set('limit', limit)
    if (search) url.searchParams.set('search', search)

    const response = await fetch(url.toString(), {
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
    console.error('Error listing papers:', error)
    return NextResponse.json(
      { error: 'Failed to list papers' },
      { status: 500 }
    )
  }
}
