import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure the backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Ensure required environment variables are present before importing settings-dependent modules
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.services.entity_extractor import EntityExtractor, EntityType  # noqa: E402


@pytest.fixture()
def extractor():
    return EntityExtractor()


def test_entity_name_matching_variations(extractor):
    text = "The Transformer architecture leverages attention mechanisms for language modeling."

    assert extractor._entity_appears_in_text("Transformer architecture", text)
    assert extractor._entity_appears_in_text("attention mechanism", text)
    assert extractor._entity_appears_in_text("LANGUAGE MODEL", text)
    assert not extractor._entity_appears_in_text("Hallucinated Concept", text)


@pytest.mark.asyncio
async def test_chunk_extraction_filters_missing_entities(extractor):
    chunk_text = (
        "The Transformer architecture leverages attention mechanisms for language modeling "
        "and builds upon previous neural network innovations."
    )

    async def fake_create(*args, **kwargs):
        payload = {
            "entities": [
                {
                    "name": "Transformer architecture",
                    "type": EntityType.METHOD.value,
                    "description": "A neural network architecture leveraging attention.",
                    "confidence": 0.9,
                    "context": chunk_text,
                },
                {
                    "name": "attention mechanism",
                    "type": EntityType.METHOD.value,
                    "description": "Focuses on relevant parts of the input sequence.",
                    "confidence": 0.8,
                    "context": chunk_text,
                },
                {
                    "name": "Hallucinated Dataset",
                    "type": EntityType.DATASET.value,
                    "description": "An invented dataset not present in the text.",
                    "confidence": 0.6,
                    "context": chunk_text,
                },
            ]
        }

        # Updated to use new tool_calls format
        tool_call = SimpleNamespace(
            function=SimpleNamespace(
                name="extract_entities", arguments=json.dumps(payload)
            )
        )
        message = SimpleNamespace(tool_calls=[tool_call])
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])

    extractor.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    entities = await extractor._extract_entities_from_chunk(chunk_text)

    names = {entity.name for entity in entities}

    assert names == {"Transformer architecture", "attention mechanism"}
