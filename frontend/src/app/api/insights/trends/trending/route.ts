import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const recentMonths = searchParams.get('recent_months') || '6'
    const topN = searchParams.get('top_n') || '10'

    const url = new URL(`${BACKEND_URL}/api/v1/insights/trends/trending`)
    url.searchParams.set('recent_months', recentMonths)
    url.searchParams.set('top_n', topN)

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || 'Failed to get trending topics' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching trending topics:', error)
    return NextResponse.json(
      { error: 'Failed to fetch trending topics' },
      { status: 500 }
    )
  }
}
