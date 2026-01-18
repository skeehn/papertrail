#!/usr/bin/env python3
"""
Test script to verify Papertrail services are working correctly.

This tests:
1. ArXiv API client
2. Pinecone vector store
3. Firecrawl service
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.logging import get_logger

logger = get_logger("test_services")


def test_arxiv_client():
    """Test ArXiv client"""
    logger.info("=" * 60)
    logger.info("Testing ArXiv Client")
    logger.info("=" * 60)

    try:
        from app.services.arxiv_client import arxiv_client

        # Test search
        logger.info("1. Testing arXiv search...")
        papers = arxiv_client.search_papers("transformers attention", max_results=3)

        if papers:
            logger.info(f"✓ Found {len(papers)} papers")
            logger.info(f"  First paper: {papers[0]['title'][:60]}...")
        else:
            logger.error("✗ No papers found")
            return False

        # Test get by ID
        logger.info("2. Testing get paper by ID...")
        paper = arxiv_client.get_paper_by_id("1706.03762")  # Attention is All You Need

        if paper:
            logger.info(f"✓ Fetched paper: {paper['title'][:60]}...")
        else:
            logger.error("✗ Failed to fetch paper")
            return False

        # Test categories
        logger.info("3. Testing categories...")
        categories = arxiv_client.get_available_categories()

        if categories:
            logger.info(f"✓ Got {len(categories)} category groups")
        else:
            logger.error("✗ No categories found")
            return False

        logger.info("✓ ArXiv client working correctly!\n")
        return True

    except Exception as e:
        logger.error(f"✗ ArXiv client test failed: {str(e)}\n")
        return False


def test_pinecone_store():
    """Test Pinecone vector store"""
    logger.info("=" * 60)
    logger.info("Testing Pinecone Vector Store")
    logger.info("=" * 60)

    try:
        from app.database.pinecone_store import pinecone_store

        # Test initialization
        logger.info("1. Testing Pinecone initialization...")
        pinecone_store.init_client()
        pinecone_store.init_embedding_model()
        pinecone_store.connect_to_index()

        logger.info("✓ Pinecone initialized successfully")

        # Test add document
        logger.info("2. Testing document add...")
        test_docs = [
            {
                "id": "test_doc_1",
                "text": "This is a test document about transformers and attention mechanisms in deep learning.",
                "metadata": {"type": "test", "topic": "transformers"},
            }
        ]

        pinecone_store.add_documents(test_docs)
        logger.info("✓ Document added successfully")

        # Test search
        logger.info("3. Testing vector search...")
        results = pinecone_store.search("transformers deep learning", k=5)

        if results:
            logger.info(f"✓ Found {len(results)} results")
            logger.info(f"  Top result score: {results[0].get('score', 0):.3f}")
        else:
            logger.warning("⚠ No search results (index might be empty)")

        # Test stats
        logger.info("4. Testing statistics...")
        stats = pinecone_store.get_statistics()

        logger.info(f"✓ Index stats: {stats.get('total_vectors', 0)} vectors")

        logger.info("✓ Pinecone store working correctly!\n")
        return True

    except Exception as e:
        logger.error(f"✗ Pinecone test failed: {str(e)}\n")
        import traceback

        traceback.print_exc()
        return False


def test_firecrawl_service():
    """Test Firecrawl service"""
    logger.info("=" * 60)
    logger.info("Testing Firecrawl Service")
    logger.info("=" * 60)

    try:
        from app.services.firecrawl_service import firecrawl_service

        if not firecrawl_service.app:
            logger.warning("⚠ Firecrawl not initialized (API key may be missing)")
            logger.info("  Skipping Firecrawl tests\n")
            return True

        # Test scrape
        logger.info("1. Testing URL scraping...")
        result = firecrawl_service.scrape_url("https://www.example.com")

        if result:
            logger.info("✓ URL scraped successfully")
        else:
            logger.warning("⚠ Scraping failed or returned no content")

        logger.info("✓ Firecrawl service available!\n")
        return True

    except Exception as e:
        logger.error(f"✗ Firecrawl test failed: {str(e)}\n")
        logger.info("  Firecrawl is optional, continuing...\n")
        return True  # Don't fail on Firecrawl errors


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("PAPERTRAIL SERVICES TEST")
    logger.info("=" * 60 + "\n")

    results = {
        "ArXiv Client": test_arxiv_client(),
        "Pinecone Store": test_pinecone_store(),
        "Firecrawl Service": test_firecrawl_service(),
    }

    # Print summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for service, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{service:.<30} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("\n✓ All tests passed! Ready to index papers.\n")
        return 0
    else:
        logger.error("\n✗ Some tests failed. Please check configuration.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
