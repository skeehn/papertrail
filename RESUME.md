# Resume-ready material for PaperTrail

Resume bullets (impact + decision, two lines each), an interview-prep block,
and talking points. The live-project rule from every current playbook: lead
with the outcome, name a decision, give the link.

## Resume bullets (pick two)

- Built a grounded arXiv research assistant (Next.js + FastAPI + HydraDB, @ai-sdk
  streaming) where a model calls its own search tool before answering; shipped an
  18-case eval harness that surfaced and fixed a contradiction-scoring defect;
  chat history, tool-use UI, and PDF indexing live: github.com/skeehn/papertrail
- Migrated the retrieval stack from Pinecone + Neo4j to the HydraDB cloud API by
  reverse-engineering an undocumented ingest schema (attributes field, async
  202-queued indexing with status polling), replacing two services and their
  vendor costs with one. github.com/skeehn/papertrail
- Diagnosed and fixed a full-stack "Event loop is closed" failure class by
  redesigning session lifecycle around per-event-loop ownership and
  asyncio.run-in-thread sync wrappers; converted four Cypher aggregations into
  O(n) in-memory analytics with zero extra infrastructure.

## Interview prep — 3-minute architecture answer

1. Problem: researchers lose the thread across PDFs; chatbots that "know" papers
   invent them. Goal grounded answers only.
2. Flow: Next.js chat (streaming UI, tool chips, sidebar history) → Next API
   route as a model+tools harness → FastAPI services → HydraDB (ingest + hybrid
   query) → entity/relationship extraction → trend analytics.
3. Decisions: one shared retrieval path for all models (tool-capable models call
   tools; others get pre-fetched context); Python-side aggregation over a
   document store; per-loop HTTP sessions; localStorage-first chat persistence.
4. Measured: eval harness result 18/18; build/test/typecheck gates 27 pages,
   10 tests; latency/cost dominated by the LLM, retrieval is a single HTTP query.

## Star stories

- "Hardest bug": eval harness flagged direct-negation contradictions scoring 0.0
  — root-caused to whitespace left after stripping a negation phrase; normalized
  both sides and locked it with the failing case as a permanent test.
- "Rebuild differently": would seed eval-first (the harness came late) and pick a
  synchronous vector store for instant search; the 202-queued cloud indexer costs
  demo seconds.

