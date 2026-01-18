#!/usr/bin/env python3
"""
Script to pre-index a diverse set of AI/CS research papers for Papertrail demo.

This script will:
1. Search arXiv for papers across various AI/ML topics
2. Download and process PDFs
3. Extract entities and build knowledge graph
4. Index in vector store (Pinecone)

Usage:
    python scripts/preindex_demo_papers.py --max-papers 100
    python scripts/preindex_demo_papers.py --topics "transformers" "graph neural networks"
    python scripts/preindex_demo_papers.py --quick  # Index 20 papers quickly
"""

import argparse
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.arxiv_indexer import batch_indexer
from app.database.pinecone_store import init_pinecone
from app.core.logging import get_logger

logger = get_logger("preindex_script")


# Curated list of research topics for diverse coverage
DEFAULT_TOPICS = [
    "large language models transformers",
    "graph neural networks",
    "retrieval augmented generation RAG",
    "few-shot learning meta-learning",
    "reinforcement learning deep RL",
    "computer vision object detection",
    "natural language processing NLP",
    "multimodal learning vision language",
    "neural architecture search AutoML",
    "explainable AI interpretability",
    "contrastive learning self-supervised",
    "attention mechanism",
]

# Specific influential papers (by arXiv ID)
INFLUENTIAL_PAPERS = [
    "1706.03762",  # Attention is All You Need (Transformers)
    "1810.04805",  # BERT
    "2005.14165",  # GPT-3
    "1312.6114",   # Adam Optimizer
    "1412.6980",   # Distilling the Knowledge in a Neural Network
    "2103.00020",  # CLIP
    "1409.1556",   # Neural Machine Translation
    "1512.03385",  # ResNet
    "1903.12261",  # XLNet
    "2010.11929",  # ViT (Vision Transformer)
]


async def index_demo_papers(
    max_papers: int = 100,
    topics: list = None,
    include_influential: bool = True,
    categories: list = None
):
    """
    Index demo papers for Papertrail

    Args:
        max_papers: Maximum total papers to index
        topics: List of research topics to search for
        include_influential: Whether to include influential papers
        categories: arXiv categories to filter by
    """
    logger.info("Starting demo paper indexing", max_papers=max_papers)

    # Initialize Pinecone
    try:
        logger.info("Initializing Pinecone vector store...")
        init_pinecone()
    except Exception as e:
        logger.warning("Failed to initialize Pinecone", error=str(e))
        logger.info("Continuing with Neo4j graph only...")

    all_arxiv_ids = set()

    # Add influential papers first
    if include_influential:
        logger.info(f"Adding {len(INFLUENTIAL_PAPERS)} influential papers")
        all_arxiv_ids.update(INFLUENTIAL_PAPERS)

    # Use provided topics or defaults
    search_topics = topics if topics else DEFAULT_TOPICS

    # Default categories for AI/ML/CS
    if not categories:
        categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"]

    # Calculate papers per topic
    remaining_slots = max_papers - len(all_arxiv_ids)
    if remaining_slots > 0:
        papers_per_topic = max(3, remaining_slots // len(search_topics))

        logger.info(
            f"Searching for papers",
            topics=len(search_topics),
            papers_per_topic=papers_per_topic
        )

        # Search for papers on each topic
        from app.services.arxiv_client import arxiv_client

        for topic in search_topics:
            try:
                logger.info(f"Searching for: {topic}")
                papers = arxiv_client.search_papers(
                    query=topic,
                    max_results=papers_per_topic,
                    categories=categories,
                    sort_by="relevance"
                )

                for paper in papers:
                    all_arxiv_ids.add(paper["arxiv_id"])

                logger.info(f"Found {len(papers)} papers for topic: {topic}")

            except Exception as e:
                logger.error(f"Failed to search for topic: {topic}", error=str(e))
                continue

    # Limit to max_papers
    arxiv_ids = list(all_arxiv_ids)[:max_papers]

    logger.info(f"Total unique papers to index: {len(arxiv_ids)}")

    # Index papers
    result = await batch_indexer.index_papers_by_ids(arxiv_ids)

    # Print summary
    logger.info("=" * 60)
    logger.info("INDEXING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total papers: {result['total_papers']}")
    logger.info(f"Successful: {result['successful']}")
    logger.info(f"Failed: {result['failed']}")

    if result['errors']:
        logger.info(f"Errors: {len(result['errors'])}")
        for error in result['errors'][:5]:  # Show first 5 errors
            logger.error(f"  - {error['arxiv_id']}: {error['error']}")

    logger.info("=" * 60)

    return result


async def quick_demo(max_papers: int = 20):
    """Quick demo with popular papers"""
    logger.info("Running quick demo indexing...")

    quick_topics = [
        "transformers attention mechanism",
        "graph neural networks GNN",
        "retrieval augmented generation",
    ]

    return await index_demo_papers(
        max_papers=max_papers,
        topics=quick_topics,
        include_influential=True
    )


def main():
    parser = argparse.ArgumentParser(
        description="Pre-index research papers for Papertrail demo"
    )

    parser.add_argument(
        "--max-papers",
        type=int,
        default=100,
        help="Maximum number of papers to index (default: 100)"
    )

    parser.add_argument(
        "--topics",
        nargs="+",
        help="Specific topics to search for (default: diverse AI topics)"
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="arXiv categories to filter by (default: cs.AI, cs.LG, cs.CL, cs.CV, stat.ML)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: index only 20 papers on popular topics"
    )

    parser.add_argument(
        "--no-influential",
        action="store_true",
        help="Don't include influential papers"
    )

    args = parser.parse_args()

    # Run indexing
    try:
        if args.quick:
            result = asyncio.run(quick_demo(max_papers=20))
        else:
            result = asyncio.run(index_demo_papers(
                max_papers=args.max_papers,
                topics=args.topics,
                include_influential=not args.no_influential,
                categories=args.categories
            ))

        # Exit with status code based on results
        if result['successful'] > 0:
            logger.info("✓ Indexing completed successfully!")
            sys.exit(0)
        else:
            logger.error("✗ No papers were indexed successfully")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Indexing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Indexing failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
