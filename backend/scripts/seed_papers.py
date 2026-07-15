"""Seed PaperTrail with real arXiv papers (metadata only — no PDF/LLM needed).

Fetches papers from the live arXiv API and stores them as Paper nodes in Neo4j
so the dashboard, Papers page, and graph show real data. Fast + reliable:
no PDF download, no embeddings, no tool-calling model required.

Usage:  python scripts/seed_papers.py
"""

import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from app.database import init_database, store_paper  # noqa: E402
from app.services.arxiv_client import arxiv_client  # noqa: E402
from app.services.pinecone_store import pinecone_store  # noqa: E402

QUERIES = [
    ("attention transformer architecture", 6),
    ("graph neural networks", 5),
    ("retrieval augmented generation", 5),
    ("knowledge graph reasoning", 4),
]


async def main() -> None:
    await init_database()
    await pinecone_store.connect()

    seen: set[str] = set()
    docs = []
    stored = 0
    for query, n in QUERIES:
        papers = arxiv_client.search_papers(query, max_results=n)
        print(f"[{query}] fetched {len(papers)}")
        for p in papers:
            aid = p.get("arxiv_id")
            if not aid or aid in seen:
                continue
            seen.add(aid)
            title = p.get("title", "").strip()
            abstract = p.get("abstract", "").strip()
            record = {
                "arxiv_id": aid,
                "title": title,
                "abstract": abstract,
                "authors": p.get("authors", []),
                "publication_date": p.get("published_date"),
                "journal": p.get("journal_ref"),
                "doi": p.get("doi"),
                "categories": p.get("categories", []),
                "pdf_url": p.get("pdf_url"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            store_paper(record)
            docs.append(
                {
                    "id": f"paper_{aid}",
                    "text": f"{title}. {abstract}",
                    "metadata": {
                        "arxiv_id": aid,
                        "title": title,
                        "abstract": abstract,
                        "authors": p.get("authors", []),
                    },
                }
            )
            stored += 1
            print(f"  + {aid}  {title[:70]}")

    # Embed into Pinecone (server-side integrated embeddings)
    if pinecone_store.is_connected and docs:
        ids = await pinecone_store.add_documents(docs)
        print(f"Embedded {len(ids)} papers into Pinecone.")
    else:
        print("Pinecone not connected — skipped embeddings.")

    print(f"\nDone. Stored {stored} unique papers.")


if __name__ == "__main__":
    asyncio.run(main())
