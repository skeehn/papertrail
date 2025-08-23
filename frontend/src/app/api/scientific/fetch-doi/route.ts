import { NextRequest, NextResponse } from 'next/server'

// Mock DOI resolution - in production would use CrossRef API
const mockDoiFetch = async (doi: string) => {
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 2000))
  
  // Mock response based on DOI
  return {
    success: true,
    metadata: {
      title: `Paper retrieved from DOI: ${doi}`,
      authors: ["Dr. Research", "Prof. Science"],
      abstract: "This paper was fetched using its DOI identifier...",
      doi: doi,
      url: `https://doi.org/${doi}`,
      publishedDate: "2024-01-01",
      venue: "Journal of Mock Research"
    },
    pdfUrl: null // Most DOIs don't provide direct PDF access
  }
}

export async function POST(request: NextRequest) {
  try {
    const { doi } = await request.json()

    if (!doi) {
      return NextResponse.json(
        { error: 'DOI is required' },
        { status: 400 }
      )
    }

    // Validate DOI format (basic)
    if (!doi.match(/^10\.\d+\/.+/)) {
      return NextResponse.json(
        { error: 'Invalid DOI format. Should start with 10.' },
        { status: 400 }
      )
    }

    console.log('🔗 Fetching paper by DOI:', doi)
    const fetchResult = await mockDoiFetch(doi)

    if (!fetchResult.success) {
      return NextResponse.json(
        { error: 'DOI not found or inaccessible' },
        { status: 404 }
      )
    }

    // TODO: If PDF is available, download and process it
    // For now, we'll work with metadata only
    
    return NextResponse.json({
      ...fetchResult,
      success: true,
      doi,
      message: 'Paper metadata fetched successfully',
      note: 'PDF processing not available - metadata only'
    })

  } catch (error) {
    console.error('DOI fetch error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch paper by DOI' },
      { status: 500 }
    )
  }
}