import { createOpenAI } from '@ai-sdk/openai'
import { convertToModelMessages, streamText, stepCountIs, tool, UIMessage } from 'ai'
import { z } from 'zod'
import { getModel } from '@/lib/chat-models'
import { getProviderCreds } from '@/lib/server-config'

export const maxDuration = 120

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

const STYLE = `Style:
- Markdown. Lead with the answer, then support it. Use headings/tables only when they earn their place.
- Use LaTeX for math: $inline$ and $$display$$.
- Be concise and concrete. No filler preamble. Never narrate your reasoning — just give the answer.`

/** For models that speak the tool-calling protocol: they drive the harness. */
const SYSTEM_WITH_TOOLS = `You are PaperTrail, a research assistant for a personal library of indexed arXiv papers.

How to answer:
- Ground every claim about the user's library in the indexed papers. Cite them inline by title (and arXiv id when useful).
- Use the searchPapers tool whenever the question touches the library — what's indexed, what a paper says, comparing/synthesising/critiquing work, finding connections or gaps. Search before answering; don't guess what's indexed.
- If searchPapers returns nothing relevant, say so plainly, then answer from your own knowledge and label it as such. Never claim a paper is in the library when it isn't.
- Use the indexArxiv tool when the user gives an arXiv id or URL and wants it added.
- For general questions that aren't about the library (e.g. "explain attention"), just answer directly — no tool call needed.
- Never narrate your tool use.

${STYLE}`

/**
 * For models that CANNOT call tools. Deliberately says nothing about tools —
 * mentioning them makes these models emit fake tool-call syntax as plain text.
 * Relevant papers are pre-fetched and appended as context instead.
 */
const SYSTEM_NO_TOOLS = `You are PaperTrail, a research assistant for a personal library of indexed arXiv papers.

How to answer:
- Relevant papers from the user's library are provided below. Ground every claim about their library in those papers and cite them inline by title (and arXiv id when useful).
- If no papers are provided or none are relevant, say so plainly, then answer from your own knowledge and label it as such. Never claim a paper is in the library when it isn't.
- Never output tool call syntax, function calls, or XML tags. You have no tools — just answer in prose.

${STYLE}`

async function searchBackend(query: string, limit = 6) {
  const res = await fetch(`${BACKEND_URL}/api/v1/chat/search-papers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  })
  if (!res.ok) throw new Error(`search failed: ${res.status}`)
  return (await res.json()) as { papers: any[]; count: number }
}

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { messages, modelId }: { messages: UIMessage[]; modelId?: string } = body

    if (!messages || !Array.isArray(messages)) {
      return new Response(JSON.stringify({ error: 'Invalid messages format' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const model = getModel(modelId)

    // Keys come from the Settings page (~/.papertrail/config.json), falling
    // back to env. Fail with an actionable message instead of a cryptic 401.
    const creds = getProviderCreds(model.provider)
    if (!creds.apiKey) {
      return new Response(
        JSON.stringify({
          error: `No API key configured for ${model.label}. Add one in Settings.`,
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const provider = createOpenAI({ baseURL: creds.baseURL, apiKey: creds.apiKey })

    // Reasoning models on OpenRouter otherwise leak chain-of-thought into the
    // answer; ask the router to drop it.
    const providerOptions =
      model.provider === 'openrouter'
        ? { openai: { reasoning: { exclude: true } } as any }
        : undefined

    if (model.supportsTools) {
      const result = streamText({
        model: provider(model.id),
        system: SYSTEM_WITH_TOOLS,
        messages: convertToModelMessages(messages),
        stopWhen: stepCountIs(4),
        providerOptions,
        tools: {
          searchPapers: tool({
            description:
              "Semantic search over the user's indexed research papers. Use this before answering anything about the library.",
            inputSchema: z.object({
              query: z.string().describe('What to look for, in natural language'),
              limit: z.number().optional().describe('Max papers to return (default 6)'),
            }),
            execute: async ({ query, limit }) => {
              try {
                return await searchBackend(query, limit ?? 6)
              } catch (e) {
                return { papers: [], count: 0, error: (e as Error).message }
              }
            },
          }),
          indexArxiv: tool({
            description:
              'Index an arXiv paper into the library by id or URL, so it becomes searchable.',
            inputSchema: z.object({
              id_or_url: z.string().describe('arXiv id (2512.24601v3) or any arXiv URL'),
            }),
            execute: async ({ id_or_url }) => {
              try {
                const res = await fetch(`${BACKEND_URL}/api/v1/chat/index-arxiv`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ id_or_url }),
                })
                return await res.json()
              } catch (e) {
                return { ok: false, error: (e as Error).message }
              }
            },
          }),
        },
      })
      return result.toUIMessageStreamResponse()
    }

    // Model can't call tools: pre-fetch relevant papers and inject as context
    // so it still answers grounded in the library.
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    const lastText =
      (lastUser?.parts?.find((p: any) => p.type === 'text') as any)?.text ?? ''

    let context = ''
    if (lastText) {
      try {
        const { papers } = await searchBackend(lastText, 6)
        if (papers?.length) {
          context =
            '\n\nRelevant papers from the user\'s library (use these to ground your answer):\n' +
            papers
              .map(
                (p: any, i: number) =>
                  `${i + 1}. ${p.title} (${p.arxiv_id})\n   ${(p.abstract || '').slice(0, 500)}`
              )
              .join('\n')
        } else {
          context = "\n\n(No papers in the user's library matched this query.)"
        }
      } catch {
        context = '\n\n(Paper search is unavailable right now.)'
      }
    }

    const result = streamText({
      model: provider(model.id),
      system: SYSTEM_NO_TOOLS + context,
      messages: convertToModelMessages(messages),
      providerOptions,
    })
    return result.toUIMessageStreamResponse()
  } catch (error) {
    console.error('Chat error:', error)
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Chat failed' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
