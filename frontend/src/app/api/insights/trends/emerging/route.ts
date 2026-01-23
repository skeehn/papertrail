import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const lookbackMonths = searchParams.get('lookback_months') || '12'
    const minGrowthRate = searchParams.get('min_growth_rate') || '50.0'

    const url = new URL(`${BACKEND_URL}/api/v1/insights/trends/emerging`)
    url.searchParams.set('lookback_months', lookbackMonths)
    url.searchParams.set('min_growth_rate', minGrowthRate)

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || 'Failed to get emerging topics' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching emerging topics:', error)
    return NextResponse.json(
      { error: 'Failed to fetch emerging topics' },
      { status: 500 }
    )
  }
}
