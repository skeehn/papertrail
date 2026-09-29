"""Seed the demo library with landmark AI research papers.

Usage: .venv/bin/python scripts/seed_demo.py

Ingests each paper through the store, then polls HydraDB's /context/status
until indexing completes (the cloud pipeline is async and can take minutes).
Safe to re-run: ingestion is keyed by arxiv id.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.hydradb_store import hydradb_store
from app.services.arxiv_client import arxiv_client

LANDMARK_PAPERS = [
    "1706.03762",  # Attention Is All You Need
    "1810.04805",  # BERT
    "2010.11929",  # Vision Transformer (ViT)
    "2005.14165",  # GPT-3 / Scaling
    "2103.00020",  # CLIP
    "2201.11903",  # Chain-of-Thought Prompting
    "2203.02155",  # LLaMA
    "2005.11401",  # RAG
    "2205.14135",  # FlashAttention
    "2105.05233",  # Diffusion Models Beat GANs
]


async def main(only_ids: list[str] | None = None) -> None:
    ids = only_ids or LANDMARK_PAPERS
    print(f"Seeding {len(ids)} papers into HydraDB ({hydradb_store._database}/{hydradb_store._collection})")
    tracked: list[tuple[str, str]] = []

    for arxiv_id in ids:
        paper = arxiv_client.get_paper_by_id(arxiv_id)
        if not paper:
            print(f"  ✗ {arxiv_id}: not found on arXiv")
            continue
        try:
            await hydradb_store.store_paper(
                {
                    "arxiv_id": paper["arxiv_id"],
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "authors": paper["authors"],
                    "publication_date": paper.get("published_date"),
                    "categories": paper.get("categories", []),
                }
            )
            source_ids = list(hydradb_store.last_source_ids)
            print(f"  ✓ {arxiv_id} accepted → source {source_ids[0][:8]}…" if source_ids else f"  ✓ {arxiv_id} ingested")
            tracked.append((arxiv_id, paper["arxiv_id"], source_ids[0] if source_ids else ""))
        except Exception as e:
            print(f"  ✗ {arxiv_id}: {e}")

    if not any(src for (_, _, src) in tracked):
        print("Nothing queued — done.")
        return

    print("\nPolling indexing status (this can take several minutes)…")
    pending = {src: arx for arx, _, src in tracked if src}
    while pending:
        for sid in list(pending):
            try:
                status = await hydradb_store.wait_until_indexed(sid, timeout=15, poll=5)
            except Exception as e:
                print(f"  … {pending[sid]}: poll error {e}")
                continue
            state = status.get("indexing_status", "?")
            if state == "completed":
                print(f"  ✓ {pending[sid]} indexed")
                del pending[sid]
            elif state in ("errored", "failed"):
                print(f"  ✗ {pending[sid]} errored: {status.get('error_code')}")
                del pending[sid]
            else:
                print(f"  … {pending[sid]}: {state}")
        if pending:
            await asyncio.sleep(15)
    print("Done.")


if __name__ == "__main__":
    only = sys.argv[1:] or None
    asyncio.run(main(only))
