import { NextRequest, NextResponse } from 'next/server'

// Mock scientific paper database - in production this would query Neo4j
const mockPaperDatabase = [
  {
    id: "paper_1",
    title: "Machine Learning in Scientific Research",
    authors: ["John Smith", "Jane Doe"],
    claims: [
      {
        id: "claim_1",
        text: "Machine learning techniques improve data analysis accuracy by 40%",
        confidence: 0.92,
        modality: "strong",
        section: "results",
        subject: "machine learning techniques",
        predicate: "improve",
        object: "data analysis accuracy"
      },
      {
        id: "claim_2",
        text: "Neural networks can accelerate scientific discovery",
        confidence: 0.78,
        modality: "weak",
        section: "discussion",
        subject: "neural networks",
        predicate: "accelerate",
        object: "scientific discovery"
      }
    ],
    entities: [
      { id: "entity_1", text: "machine learning", type: "method", mentions: 15 },
      { id: "entity_2", text: "neural networks", type: "method", mentions: 8 },
      { id: "entity_3", text: "data analysis", type: "process", mentions: 12 },
      { id: "entity_4", text: "scientific discovery", type: "concept", mentions: 5 }
    ],
    topics: ["artificial intelligence", "machine learning", "data science", "research methods"]
  },
  {
    id: "paper_2", 
    title: "Deep Learning Applications in Biology",
    authors: ["Dr. Research", "Prof. Science"],
    claims: [
      {
        id: "claim_3",
        text: "Deep learning models achieve 95% accuracy in protein structure prediction",
        confidence: 0.95,
        modality: "strong",
        section: "results",
        subject: "deep learning models",
        predicate: "achieve",
        object: "95% accuracy in protein structure prediction"
      },
      {
        id: "claim_4",
        text: "Traditional methods show limitations in complex biological systems",
        confidence: 0.83,
        modality: "strong", 
        section: "discussion",
        subject: "traditional methods",
        predicate: "show limitations in",
        object: "complex biological systems"
      }
    ],
    entities: [
      { id: "entity_5", text: "deep learning", type: "method", mentions: 20 },
      { id: "entity_6", text: "protein structure", type: "biological_concept", mentions: 18 },
      { id: "entity_7", text: "biological systems", type: "biological_concept", mentions: 10 }
    ],
    topics: ["deep learning", "biology", "protein structure", "computational biology"]
  }
]

export async function POST(request: NextRequest) {
  try {
    const { query, type = "papers", limit = 5 } = await request.json()

    if (!query) {
      return NextResponse.json(
        { error: "Query is required" },
        { status: 400 }
      )
    }

    console.log(`🔍 Scientific search: "${query}" (type: ${type})`)

    const queryLower = query.toLowerCase()
    let results: any[] = []

    switch (type) {
      case "papers":
        results = mockPaperDatabase.filter(paper =>
          paper.title.toLowerCase().includes(queryLower) ||
          paper.authors.some(author => author.toLowerCase().includes(queryLower)) ||
          paper.topics.some(topic => topic.toLowerCase().includes(queryLower))
        ).slice(0, limit)
        break

      case "claims":
        results = mockPaperDatabase.flatMap(paper =>
          paper.claims.filter(claim =>
            claim.text.toLowerCase().includes(queryLower) ||
            claim.subject.toLowerCase().includes(queryLower) ||
            claim.object.toLowerCase().includes(queryLower)
          ).map(claim => ({
            ...claim,
            paperTitle: paper.title,
            paperId: paper.id
          }))
        ).slice(0, limit)
        break

      case "entities":
        results = mockPaperDatabase.flatMap(paper =>
          paper.entities.filter(entity =>
            entity.text.toLowerCase().includes(queryLower) ||
            entity.type.toLowerCase().includes(queryLower)
          ).map(entity => ({
            ...entity,
            paperTitle: paper.title,
            paperId: paper.id
          }))
        ).slice(0, limit)
        break

      case "topics":
        results = mockPaperDatabase.flatMap(paper =>
          paper.topics.filter(topic =>
            topic.toLowerCase().includes(queryLower)
          ).map(topic => ({
            topic,
            paperTitle: paper.title,
            paperId: paper.id,
            relevantClaims: paper.claims.length
          }))
        ).slice(0, limit)
        break

      default:
        // Comprehensive search across all types
        const paperResults = mockPaperDatabase.filter(paper =>
          paper.title.toLowerCase().includes(queryLower) ||
          paper.topics.some(topic => topic.toLowerCase().includes(queryLower))
        )

        const claimResults = mockPaperDatabase.flatMap(paper =>
          paper.claims.filter(claim =>
            claim.text.toLowerCase().includes(queryLower)
          ).map(claim => ({ ...claim, paperTitle: paper.title, type: 'claim' }))
        )

        const entityResults = mockPaperDatabase.flatMap(paper =>
          paper.entities.filter(entity =>
            entity.text.toLowerCase().includes(queryLower)
          ).map(entity => ({ ...entity, paperTitle: paper.title, type: 'entity' }))
        )

        results = [
          ...paperResults.map(p => ({ ...p, type: 'paper' })),
          ...claimResults.slice(0, 3),
          ...entityResults.slice(0, 3)
        ].slice(0, limit)
    }

    const searchSummary = {
      query,
      type,
      totalResults: results.length,
      searchedPapers: mockPaperDatabase.length,
      totalClaims: mockPaperDatabase.reduce((sum, paper) => sum + paper.claims.length, 0),
      totalEntities: mockPaperDatabase.reduce((sum, paper) => sum + paper.entities.length, 0)
    }

    return NextResponse.json({
      results,
      summary: searchSummary,
      message: results.length > 0 
        ? `Found ${results.length} ${type} matching "${query}"`
        : `No ${type} found matching "${query}"`
    })

  } catch (error) {
    console.error('Scientific search error:', error)
    return NextResponse.json(
      { error: 'Failed to search scientific knowledge' },
      { status: 500 }
    )
  }
}