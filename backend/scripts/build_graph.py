"""Extract entities + relationships for stored papers and build the Neo4j graph.

Runs the LLM entity extractor (OpenRouter, tool-calling) over each paper's
title + abstract and writes Entity nodes + relationships. Populates the Graph
page, dashboard graph counts, and gives the Connector agent real data.

Usage:  python scripts/build_graph.py [max_papers]
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.database import (  # noqa: E402
    get_paper_by_id,
    init_database,
    list_papers,
    store_entities,
    store_relationships,
)
from app.services.entity_extractor import EntityExtractor  # noqa: E402


async def main() -> None:
    max_papers = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    await init_database()
    ex = EntityExtractor()

    papers = list_papers(limit=max_papers)
    print(f"Building graph for {len(papers)} papers...\n")

    total_e = total_r = 0
    for i, p in enumerate(papers, 1):
        pid = p.get("id") or p.get("arxiv_id")
        full = get_paper_by_id(pid) or p
        text = f"{full.get('title','')}. {full.get('abstract','')}".strip()
        if len(text) < 20:
            continue
        try:
            ents, rels = await ex.extract_entities_and_relationships(text)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(papers)}] {pid}: extraction failed ({e})")
            continue

        store_entities(
            pid,
            [
                {"name": e.name, "type": e.type.value, "confidence": e.confidence}
                for e in ents
            ],
        )
        store_relationships(
            pid,
            [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.type.value if hasattr(r.type, "value") else str(r.type),
                    "confidence": r.confidence,
                }
                for r in rels
            ],
        )
        total_e += len(ents)
        total_r += len(rels)
        print(
            f"[{i}/{len(papers)}] {pid}: {len(ents)} entities, {len(rels)} rels"
            f"  — {full.get('title','')[:50]}"
        )

    print(
        f"\nDone. {total_e} entities, {total_r} relationships across {len(papers)} papers."
    )


if __name__ == "__main__":
    asyncio.run(main())
