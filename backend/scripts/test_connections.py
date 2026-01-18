#!/usr/bin/env python3
"""
Quick connection test for Neo4j and OpenRouter
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("connection_test")


def test_neo4j():
    """Test Neo4j connection"""
    logger.info("=" * 60)
    logger.info("Testing Neo4j Connection")
    logger.info("=" * 60)

    try:
        from neo4j import GraphDatabase

        logger.info(f"URI: {settings.NEO4J_URI}")
        logger.info(f"User: {settings.NEO4J_USER}")
        logger.info(f"Database: {settings.NEO4J_DATABASE}")

        driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

        driver.verify_connectivity()
        logger.info("✓ Neo4j connection successful!")

        # Test a simple query
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run("RETURN 'Hello Neo4j!' as message")
            record = result.single()
            logger.info(f"✓ Query test: {record['message']}")

        driver.close()
        logger.info("")
        return True

    except Exception as e:
        logger.error(f"✗ Neo4j connection failed: {str(e)}")
        import traceback

        traceback.print_exc()
        logger.info("")
        return False


def test_openrouter():
    """Test OpenRouter API"""
    logger.info("=" * 60)
    logger.info("Testing OpenRouter API")
    logger.info("=" * 60)

    try:
        import openai

        logger.info(f"Base URL: {settings.OPENAI_BASE_URL}")
        logger.info(f"Model: {settings.OPENAI_MODEL}")

        # Initialize client
        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL

        client = openai.OpenAI(**client_kwargs)

        # Test with a simple completion
        logger.info("Sending test request...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from OpenRouter!' in exactly those words.",
                }
            ],
            max_tokens=50,
        )

        message = response.choices[0].message.content
        logger.info(f"✓ OpenRouter response: {message}")
        logger.info("")
        return True

    except Exception as e:
        logger.error(f"✗ OpenRouter connection failed: {str(e)}")
        import traceback

        traceback.print_exc()
        logger.info("")
        return False


def main():
    """Run all connection tests"""
    logger.info("\n" + "=" * 60)
    logger.info("PAPERTRAIL CONNECTION TEST")
    logger.info("=" * 60 + "\n")

    results = {
        "Neo4j": test_neo4j(),
        "OpenRouter": test_openrouter(),
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
        logger.info("\n✓ All connections working! Ready to proceed.\n")
        return 0
    else:
        logger.error("\n✗ Some connections failed. Please check credentials.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
