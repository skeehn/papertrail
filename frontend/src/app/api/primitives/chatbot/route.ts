import { openai } from "@ai-sdk/openai"
import { convertToModelMessages, streamText, tool, UIMessage } from "ai"
import { z } from "zod"

export const maxDuration = 30

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { messages }: { messages: UIMessage[] } = body

    if (!messages || !Array.isArray(messages)) {
      return new Response(JSON.stringify({ error: "Invalid messages format" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      })
    }

    // Use messages directly as convertToModelMessages handles the format
    const formattedMessages = messages

    const result = streamText({
    model: openai("gpt-4o-mini"),
    system:
      "You are PaperTrail, an AI research assistant with access to a knowledge graph and conversation memory system. You help users explore research topics, synthesize information, and discover connections between concepts.\n\nIMPORTANT: You have access to conversation memories through the searchMemories tool. When users ask about information from previous conversations (like their name, preferences, or things they've told you before), ALWAYS use the searchMemories tool first to recall relevant information before responding.\n\nUse the available tools to:\n- searchMemories: Find information from previous conversations with the user\n- queryGraph: Search your knowledge base for research topics, papers, and entities\n- getGraphStatistics: Get information about your knowledge graph\n\nAlways try to personalize responses based on what you remember about the user from previous conversations.",
    messages: convertToModelMessages(formattedMessages),
    tools: {
      getTime: tool({
        description: "Get the current time in a specific timezone",
        inputSchema: z.object({
          timezone: z
            .string()
            .describe("A valid IANA timezone, e.g. 'Europe/Paris'"),
        }),
        execute: async ({ timezone }) => {
          try {
            const now = new Date()
            const time = now.toLocaleString("en-US", {
              timeZone: timezone,
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false,
            })

            return { time, timezone }
          } catch {
            return { error: "Invalid timezone format." }
          }
        },
      }),
      getCurrentDate: tool({
        description: "Get the current date and time with timezone information",
        inputSchema: z.object({}),
        execute: async () => {
          const now = new Date()
          return {
            timestamp: now.getTime(),
            iso: now.toISOString(),
            local: now.toLocaleString("en-US", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              timeZoneName: "short",
            }),
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            utc: now.toUTCString(),
          }
        },
      }),
      queryGraph: tool({
        description: "Query the knowledge graph for information about entities, papers, or concepts",
        inputSchema: z.object({
          entity_name: z.string().optional().describe("Name of entity to query"),
          paper_id: z.string().optional().describe("ID of paper to query"), 
          depth: z.number().optional().default(2).describe("Depth of graph traversal"),
        }),
        execute: async ({ entity_name, paper_id, depth }) => {
          try {
            const response = await fetch(`${BACKEND_URL}/api/v1/search/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ query: entity_name || paper_id, limit: 10 }),
            })
            return await response.json()
          } catch (error) {
            return { error: "Failed to query graph" }
          }
        },
      }),
      getGraphStatistics: tool({
        description: "Get statistics about the knowledge graph",
        inputSchema: z.object({}),
        execute: async () => {
          try {
            const response = await fetch(`${BACKEND_URL}/api/v1/temporal-graph/stats`)
            return await response.json()
          } catch (error) {
            return { error: "Failed to get graph statistics" }
          }
        },
      }),
      searchMemories: tool({
        description: "Search through conversation memories to recall previous information about the user or topics discussed",
        inputSchema: z.object({
          query: z.string().describe("Search query to find relevant memories (e.g., 'user name', 'favorite food', 'preferences')"),
          limit: z.number().optional().default(5).describe("Number of memories to return")
        }),
        execute: async ({ query, limit }) => {
          try {
            // Get memories from our API
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
        },
      }),
    },
  })

  return result.toUIMessageStreamResponse()
  } catch (error) {
    console.error("API Error:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
}
