import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const [papersResponse, graphResponse] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/papers/`, {
        headers: { 'Content-Type': 'application/json' },
      }),
      fetch(`${BACKEND_URL}/api/v1/graph/statistics`, {
        headers: { 'Content-Type': 'application/json' },
      }),
    ])

    if (!papersResponse.ok || !graphResponse.ok) {
      throw new Error('Backend responded with error')
    }

    const papersData = await papersResponse.json()
    const graphData = await graphResponse.json()

    const stats = {
      totalPapers: papersData.total || 0,
      activeConversations: 0,
      claimsExtracted: graphData.statistics?.node_count || 0,
      graphNodes: graphData.statistics?.node_count || 0,
      relationships: graphData.statistics?.relationship_count || 0,
    }

    return NextResponse.json(stats)
  } catch (error) {
    console.error('Error fetching dashboard stats:', error)
    return NextResponse.json(
      { error: 'Failed to fetch dashboard stats' },
      { status: 500 }
    )
  }
}
