import { openai } from "@ai-sdk/openai"
import { convertToModelMessages, streamText, tool } from "ai"
import { z } from "zod"
import type { UIMessage } from "ai"

export const maxDuration = 30

export async function POST(req: Request) {
  try {
    const body = await req.json()
    console.log('Received body:', JSON.stringify(body, null, 2))
    const { messages }: { messages: UIMessage[] } = body

    if (!messages || !Array.isArray(messages)) {
      console.error('Invalid messages:', messages)
      return new Response(JSON.stringify({ error: "Invalid messages format" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      })
    }

    const result = streamText({
      model: openai("gpt-4o-mini"),
      system: `You are PaperTrail, an intelligent research assistant specialized in scientific literature analysis and argument mapping.

CORE CAPABILITIES:
- Search through uploaded scientific papers and their extracted claims
- Analyze research topics, entities, and scientific arguments  
- Find connections and contradictions between papers
- Provide research insights based on evidence from papers
- Help users explore their scientific knowledge collection

IMPORTANT: Always use the searchPapers tool when users ask about:
- Specific research topics or concepts
- Claims or findings in papers
- Authors or papers they've uploaded
- Connections between different studies
- Any scientific questions that could be answered from their collection

Use the memory tools to remember what users have asked before and build on previous conversations.

Be scientific, evidence-based, and always cite your sources from the user's paper collection.`,
      messages: convertToModelMessages(messages),
      tools: {
        searchPapers: tool({
          description: "Search through the user's uploaded papers for specific topics, claims, or concepts",
          inputSchema: z.object({
            query: z.string().describe("Search query for papers, topics, claims, or concepts"),
            type: z.enum(["papers", "claims", "entities", "topics"]).optional().describe("Type of search to perform"),
            limit: z.number().optional().default(5).describe("Number of results to return")
          }),
          execute: async ({ query, type, limit }) => {
            try {
              // Search through scientific knowledge
              const response = await fetch(`${req.url?.includes('localhost') ? 'http://localhost:3000' : new URL(req.url || '').origin}/api/scientific/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, type, limit })
              })
              
              if (!response.ok) {
                return { results: [], message: "No papers found in your collection" }
              }
              
              return await response.json()
            } catch (error) {
              console.error('Paper search error:', error)
              return { results: [], message: "Error searching papers" }
            }
          }
        }),
        
        getResearchInsights: tool({
          description: "Get high-level insights about the user's research collection",
          inputSchema: z.object({
            focus: z.enum(["topics", "contradictions", "claims", "overview"]).describe("Type of insight to generate")
          }),
          execute: async ({ focus }) => {
            try {
              const response = await fetch(`${req.url?.includes('localhost') ? 'http://localhost:3000' : new URL(req.url || '').origin}/api/scientific/insights`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ focus })
              })
              
              if (!response.ok) {
                return { insights: [], message: "No insights available" }
              }
              
              return await response.json()
            } catch (error) {
              console.error('Research insights error:', error)
              return { insights: [], message: "Error generating insights" }
            }
          }
        }),

        searchMemories: tool({
          description: "Search through conversation memories to recall previous information about the user or topics discussed",
          inputSchema: z.object({
            query: z.string().describe("Search query to find relevant memories"),
            limit: z.number().optional().default(5).describe("Number of memories to return")
          }),
          execute: async ({ query, limit }) => {
            try {
              const baseUrl = req.url?.includes('localhost') ? 'http://localhost:3000' : new URL(req.url || '').origin
              const response = await fetch(`${baseUrl}/api/memories`)
              
              if (!response.ok) {
                return { memories: [], message: "No previous memories found" }
              }
              
              const memories = await response.json()
              
              if (!memories || memories.length === 0) {
                return { memories: [], message: "No previous memories found" }
              }
              
              // Simple search through memories
              const searchTerms = query.toLowerCase().split(' ')
              const relevantMemories = memories
                .filter((memory: any) => {
                  const content = memory.content?.toLowerCase() || ''
                  const entities = memory.metadata?.entities?.join(' ').toLowerCase() || ''
                  const topics = memory.metadata?.topics?.join(' ').toLowerCase() || ''
                  const searchText = `${content} ${entities} ${topics}`
                  
                  return searchTerms.some(term => searchText.includes(term))
                })
                .slice(0, limit)
                .map((memory: any) => ({
                  content: memory.content,
                  type: memory.metadata?.type,
                  timestamp: memory.created_at,
                  entities: memory.metadata?.entities || [],
                  topics: memory.metadata?.topics || []
                }))
              
              return {
                memories: relevantMemories,
                message: relevantMemories.length > 0 
                  ? `Found ${relevantMemories.length} relevant memories`
                  : "No matching memories found for that query"
              }
            } catch (error) {
              console.error('Memory search error:', error)
              return { memories: [], message: "Error searching memories" }
            }
          }
        })
      }
    })

    return result.toUIMessageStreamResponse()
  } catch (error) {
    console.error("Intelligent chat API error:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
}