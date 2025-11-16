"""
Test configuration and fixtures for pytest.

This module sets up common test fixtures and mocks for the test suite.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock optional heavy dependencies if not installed (for development environments)
# In CI/CD, these should be installed via requirements.txt
optional_modules = [
    "openai",
    "langchain",
    "langchain_openai",
    "langgraph",
    "transformers",
    "torch",
    "sentence_transformers",
]

for module_name in optional_modules:
    try:
        __import__(module_name)
    except ImportError:
        sys.modules[module_name] = MagicMock()


@pytest.fixture
def mock_openai_client():
    """Fixture providing a mocked OpenAI client for testing."""
    mock_client = MagicMock()
    return mock_client
