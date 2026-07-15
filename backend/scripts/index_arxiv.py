"""Index one or more arXiv papers by ID (metadata + abstract).

Fetches each paper from arXiv, stores it in Neo4j, embeds it into Pinecone
(server-side integrated embeddings), and extracts entities into the graph.
Works from an ID or a full arXiv URL.

Usage:
    python scripts/index_arxiv.py 2512.24601v3
    python scripts/index_arxiv.py https://arxiv.org/html/2512.24601v3 2402.01234
"""

import asyncio
import re
import sys

sys.path.insert(0, ".")

from app.database import (  # noqa: E402
    init_database,
    store_entities,
    store_paper,
    store_relationships,
)
from app.services.arxiv_client import arxiv_client  # noqa: E402
from app.services.entity_extractor import EntityExtractor  # noqa: E402
from app.services.pinecone_store import pinecone_store  # noqa: E402


def parse_id(token: str) -> str:
    """Accept a bare id or any arxiv URL form and return the arXiv id."""
    m = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", token)
    if m:
        return m.group(1)
    return token.rstrip("/").split("/")[-1]


async def main() -> None:
    ids = [parse_id(a) for a in sys.argv[1:]]
    if not ids:
        print("usage: python scripts/index_arxiv.py <arxiv_id_or_url> [...]")
        return

    await init_database()
    await pinecone_store.connect()
    ex = EntityExtractor()

    for raw in ids:
        p = arxiv_client.get_paper_by_id(raw)
        if not p:
            print(f"✗ {raw}: not found on arXiv")
            continue
        aid = p.get("arxiv_id", raw)
        title = (p.get("title") or "").strip()
        abstract = (p.get("abstract") or "").strip()

        # 1) Neo4j paper node
        store_paper(
            {
                "arxiv_id": aid,
                "title": title,
                "abstract": abstract,
                "authors": p.get("authors", []),
                "publication_date": p.get("published_date"),
                "doi": p.get("doi"),
                "categories": p.get("categories", []),
                "pdf_url": p.get("pdf_url"),
            }
        )

        # 2) Pinecone embedding (integrated model)
        if pinecone_store.is_connected:
            await pinecone_store.add_documents(
                [
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
                ]
            )

        # 3) Graph entities + relationships
        n_e = n_r = 0
        try:
            ents, rels = await ex.extract_entities_and_relationships(
                f"{title}. {abstract}"
            )
            store_entities(
                aid,
                [
                    {"name": e.name, "type": e.type.value, "confidence": e.confidence}
                    for e in ents
                ],
            )
            store_relationships(
                aid,
                [
                    {
                        "source": r.source,
                        "target": r.target,
                        "type": (
                            r.type.value if hasattr(r.type, "value") else str(r.type)
                        ),
                        "confidence": r.confidence,
                    }
                    for r in rels
                ],
            )
            n_e, n_r = len(ents), len(rels)
        except Exception as e:  # noqa: BLE001
            print(f"  (entity extraction skipped: {e})")

        print(f"✓ {aid}  {title[:60]}  — {n_e} entities, {n_r} rels")


if __name__ == "__main__":
    asyncio.run(main())
