import { NextRequest, NextResponse } from 'next/server'
import { readFile } from 'fs/promises'
import path from 'path'

const UPLOAD_DIR = path.join(process.cwd(), 'uploads', 'papers')

// Mock Grobid response - in production this would call actual Grobid service
const mockGrobidParse = async (_pdfPath: string) => {
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  return {
    title: "Example Paper: Machine Learning in Scientific Research",
    authors: [
      "John Smith",
      "Jane Doe", 
      "Robert Johnson"
    ],
    abstract: "This paper explores the application of machine learning techniques in scientific research, demonstrating significant improvements in data analysis and hypothesis generation.",
    sections: {
      introduction: "Machine learning has revolutionized many fields of scientific inquiry...",
      methods: "We applied a novel neural network architecture to analyze complex datasets...",
      results: "Our experiments show a 40% improvement in accuracy over traditional methods...",
      discussion: "These results suggest that AI can accelerate scientific discovery...",
      conclusion: "We conclude that machine learning is a powerful tool for scientific research..."
    },
    citations: [
      {
        id: "ref1",
        title: "Deep Learning for Scientific Computing",
        authors: ["A. Smith", "B. Jones"],
        year: 2023,
        venue: "Nature Machine Intelligence"
      },
      {
        id: "ref2", 
        title: "Neural Networks in Biology",
        authors: ["C. Wilson", "D. Brown"],
        year: 2022,
        venue: "Cell"
      }
    ],
    metadata: {
      pages: 12,
      doi: "10.1000/example.doi",
      publishedDate: "2024-01-15",
      venue: "Journal of AI Research"
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const { paperId } = await request.json()

    if (!paperId) {
      return NextResponse.json(
        { error: 'paperId is required' },
        { status: 400 }
      )
    }

    const pdfPath = path.join(UPLOAD_DIR, `${paperId}.pdf`)
    
    // Check if file exists
    try {
      await readFile(pdfPath)
    } catch (error) {
      return NextResponse.json(
        { error: 'Paper file not found' },
        { status: 404 }
      )
    }

    // Parse with Grobid (mocked for now)
    console.log('🔬 Parsing paper with Grobid:', paperId)
    const parsedData = await mockGrobidParse(pdfPath)

    // TODO: Store parsed data in Neo4j database
    // For now, we'll return the parsed data directly
    
    return NextResponse.json({
      success: true,
      paperId,
      ...parsedData,
      message: 'Paper parsed successfully'
    })

  } catch (error) {
    console.error('Paper parsing error:', error)
    return NextResponse.json(
      { error: 'Failed to parse paper' },
      { status: 500 }
    )
  }
}