import { NextRequest, NextResponse } from 'next/server'

// Mock claim extraction - in production would use fine-tuned NLP models
const mockClaimExtraction = async (paperContent: any) => {
  // Simulate NLP processing time
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  return {
    claims: [
      {
        id: "claim_1",
        text: "Machine learning techniques improve data analysis accuracy by 40%",
        section: "results",
        evidence_span: "Our experiments show a 40% improvement in accuracy over traditional methods",
        confidence: 0.92,
        modality: "strong", // strong, weak, speculative
        subject: "machine learning techniques",
        predicate: "improve",
        object: "data analysis accuracy",
        supporting_citations: ["ref1", "ref2"]
      },
      {
        id: "claim_2", 
        text: "Neural networks can accelerate scientific discovery",
        section: "discussion",
        evidence_span: "These results suggest that AI can accelerate scientific discovery",
        confidence: 0.78,
        modality: "weak",
        subject: "neural networks",
        predicate: "accelerate", 
        object: "scientific discovery",
        supporting_citations: ["ref1"]
      },
      {
        id: "claim_3",
        text: "Traditional methods are less accurate than AI approaches",
        section: "results", 
        evidence_span: "40% improvement in accuracy over traditional methods",
        confidence: 0.85,
        modality: "strong",
        subject: "traditional methods",
        predicate: "less accurate than",
        object: "AI approaches", 
        supporting_citations: []
      }
    ],
    entities: [
      {
        id: "entity_1",
        text: "machine learning",
        type: "method",
        mentions: 15,
        linked_to: "http://purl.obolibrary.org/obo/NCIT_C17622"
      },
      {
        id: "entity_2",
        text: "neural networks", 
        type: "method",
        mentions: 8,
        linked_to: "http://purl.obolibrary.org/obo/NCIT_C48876"
      },
      {
        id: "entity_3",
        text: "scientific discovery",
        type: "concept",
        mentions: 5,
        linked_to: null
      },
      {
        id: "entity_4",
        text: "data analysis",
        type: "process", 
        mentions: 12,
        linked_to: "http://edamontology.org/operation_2945"
      }
    ],
    relationships: [
      {
        source: "claim_1",
        target: "entity_1", 
        type: "MENTIONS",
        confidence: 0.98
      },
      {
        source: "claim_1",
        target: "entity_4",
        type: "MENTIONS", 
        confidence: 0.95
      },
      {
        source: "claim_2",
        target: "entity_2",
        type: "MENTIONS",
        confidence: 0.92
      },
      {
        source: "claim_2", 
        target: "entity_3",
        type: "MENTIONS",
        confidence: 0.88
      }
    ]
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

    // TODO: Get parsed paper content from database
    // For now, we'll use mock data
    const mockPaperContent = {
      title: "Example Paper",
      sections: {}
    }

    console.log('🧠 Extracting claims and entities:', paperId)
    const extractedData = await mockClaimExtraction(mockPaperContent)

    // TODO: Store extracted claims and entities in Neo4j knowledge graph
    
    return NextResponse.json({
      success: true,
      paperId,
      ...extractedData,
      statistics: {
        claims_extracted: extractedData.claims.length,
        entities_found: extractedData.entities.length,
        relationships_created: extractedData.relationships.length
      },
      message: 'Claims and entities extracted successfully'
    })

  } catch (error) {
    console.error('Claim extraction error:', error)
    return NextResponse.json(
      { error: 'Failed to extract claims' },
      { status: 500 }
    )
  }
}