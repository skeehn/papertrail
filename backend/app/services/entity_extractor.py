import asyncio
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import openai
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger


class EntityType(str, Enum):
    """Types of entities that can be extracted"""

    CONCEPT = "concept"
    METHOD = "method"
    DATASET = "dataset"
    METRIC = "metric"
    TOOL = "tool"
    ALGORITHM = "algorithm"
    THEORY = "theory"
    CLAIM = "claim"
    ASSUMPTION = "assumption"
    FINDING = "finding"


class RelationshipType(str, Enum):
    """Types of relationships between entities"""

    USES = "uses"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    MENTIONS = "mentions"
    COMPARES = "compares"
    EVALUATES = "evaluates"
    CITES = "cites"
    RELATED_TO = "related_to"


@dataclass
class ExtractedEntity:
    """Extracted entity with confidence score"""

    name: str
    type: EntityType
    description: str
    confidence: float
    context: str
    start_position: Optional[int] = None
    end_position: Optional[int] = None


@dataclass
class ExtractedRelationship:
    """Extracted relationship between entities"""

    source: str
    target: str
    type: RelationshipType
    description: str
    confidence: float
    context: str


class EntityExtractor:
    """OpenAI-powered entity and relationship extraction service"""

    def __init__(self):
        self.logger = get_logger("entity_extractor")
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Entity extraction function schema
        self.entity_extraction_function = {
            "name": "extract_entities",
            "description": "Extract scientific entities from academic paper text",
            "parameters": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "description": "List of extracted entities",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The name of the entity",
                                },
                                "type": {
                                    "type": "string",
                                    "enum": [e.value for e in EntityType],
                                    "description": "The type of entity",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "A brief description of the entity",
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                    "description": "Confidence score for the extraction",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "The context in which the entity appears",
                                },
                            },
                            "required": [
                                "name",
                                "type",
                                "description",
                                "confidence",
                                "context",
                            ],
                        },
                    }
                },
                "required": ["entities"],
            },
        }

        # Relationship extraction function schema
        self.relationship_extraction_function = {
            "name": "extract_relationships",
            "description": "Extract relationships between entities in academic text",
            "parameters": {
                "type": "object",
                "properties": {
                    "relationships": {
                        "type": "array",
                        "description": "List of extracted relationships",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
                                    "description": "The source entity name",
                                },
                                "target": {
                                    "type": "string",
                                    "description": "The target entity name",
                                },
                                "type": {
                                    "type": "string",
                                    "enum": [r.value for r in RelationshipType],
                                    "description": "The type of relationship",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of the relationship",
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                    "description": "Confidence score for the relationship",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "The context supporting this relationship",
                                },
                            },
                            "required": [
                                "source",
                                "target",
                                "type",
                                "description",
                                "confidence",
                                "context",
                            ],
                        },
                    }
                },
                "required": ["relationships"],
            },
        }

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_entities(
        self, text: str, chunk_size: int = 4000
    ) -> List[ExtractedEntity]:
        """Extract entities from text using OpenAI function calling"""
        try:
            self.logger.info("Starting entity extraction", text_length=len(text))

            # Split text into chunks if it's too long
            text_chunks = self._split_text(text, chunk_size)
            all_entities = []

            for i, chunk in enumerate(text_chunks):
                self.logger.debug(
                    "Processing chunk", chunk_index=i, total_chunks=len(text_chunks)
                )

                chunk_entities = await self._extract_entities_from_chunk(chunk)
                all_entities.extend(chunk_entities)

                # Add delay between API calls to avoid rate limits
                if i < len(text_chunks) - 1:
                    await asyncio.sleep(0.5)

            # Deduplicate entities
            deduplicated_entities = self._deduplicate_entities(all_entities)

            self.logger.info(
                "Entity extraction completed",
                total_entities=len(deduplicated_entities),
                chunks_processed=len(text_chunks),
            )

            return deduplicated_entities

        except Exception as e:
            self.logger.error("Entity extraction failed", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_relationships(
        self, text: str, entities: List[ExtractedEntity], chunk_size: int = 4000
    ) -> List[ExtractedRelationship]:
        """Extract relationships between entities"""
        try:
            self.logger.info(
                "Starting relationship extraction",
                text_length=len(text),
                entity_count=len(entities),
            )

            # Create entity context for the model
            entity_names = [e.name for e in entities]
            entity_context = "Entities mentioned in the text: " + ", ".join(
                entity_names[:50]
            )  # Limit context

            # Split text into chunks
            text_chunks = self._split_text(text, chunk_size)
            all_relationships = []

            for i, chunk in enumerate(text_chunks):
                self.logger.debug("Processing relationships in chunk", chunk_index=i)

                chunk_relationships = await self._extract_relationships_from_chunk(
                    chunk, entity_context
                )
                all_relationships.extend(chunk_relationships)

                # Add delay between API calls
                if i < len(text_chunks) - 1:
                    await asyncio.sleep(0.5)

            # Filter relationships to only include entities we know about
            valid_relationships = self._filter_valid_relationships(
                all_relationships, entity_names
            )

            # Deduplicate relationships
            deduplicated_relationships = self._deduplicate_relationships(
                valid_relationships
            )

            self.logger.info(
                "Relationship extraction completed",
                total_relationships=len(deduplicated_relationships),
                chunks_processed=len(text_chunks),
            )

            return deduplicated_relationships

        except Exception as e:
            self.logger.error("Relationship extraction failed", error=str(e))
            raise

    async def extract_entities_and_relationships(
        self, text: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """Extract both entities and relationships in one operation"""
        try:
            # First extract entities
            entities = await self.extract_entities(text)

            # Then extract relationships using the entities as context
            relationships = await self.extract_relationships(text, entities)

            return entities, relationships

        except Exception as e:
            self.logger.error("Combined extraction failed", error=str(e))
            raise

    async def _extract_entities_from_chunk(
        self, text_chunk: str
    ) -> List[ExtractedEntity]:
        """Extract entities from a single text chunk"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at extracting scientific entities from academic papers. 
                        Extract key concepts, methods, datasets, algorithms, theories, claims, and other important 
                        scientific entities. Be precise and avoid extracting common words or overly general terms.
                        Focus on domain-specific technical terms and proper nouns.""",
                    },
                    {
                        "role": "user",
                        "content": f"Extract entities from this academic text:\n\n{text_chunk}",
                    },
                ],
                functions=[self.entity_extraction_function],
                function_call={"name": "extract_entities"},
                temperature=0.1,
                max_tokens=2000,
            )

            # Parse function call response
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "extract_entities":
                entities_data = json.loads(function_call.arguments)
                entities = []

                for entity_dict in entities_data.get("entities", []):
                    try:
                        entity = ExtractedEntity(
                            name=entity_dict["name"],
                            type=EntityType(entity_dict["type"]),
                            description=entity_dict["description"],
                            confidence=entity_dict["confidence"],
                            context=entity_dict["context"],
                        )
                        if self._entity_appears_in_text(entity.name, text_chunk):
                            entities.append(entity)
                        else:
                            self.logger.debug(
                                "Discarding entity not found in text",
                                entity=entity.name,
                            )
                    except (KeyError, ValueError) as e:
                        self.logger.warning(
                            "Invalid entity data", entity=entity_dict, error=str(e)
                        )

                return entities

            return []

        except Exception as e:
            self.logger.error("Failed to extract entities from chunk", error=str(e))
            return []

    def _entity_appears_in_text(self, entity_name: str, text: str) -> bool:
        """Return True if the entity name appears in the provided text."""
        if not entity_name or not text:
            return False

        normalized_name = " ".join(entity_name.strip().split())
        if not normalized_name:
            return False

        tokens = re.split(r"\s+", normalized_name)
        pattern_tokens = []

        for index, token in enumerate(tokens):
            escaped_token = re.escape(token)
            if index == len(tokens) - 1:
                variants = {token}
                lower_token = token.lower()

                if len(token) > 1:
                    if lower_token.endswith("y") and lower_token[-2] not in "aeiou":
                        variants.add(token[:-1] + "ies")
                    elif lower_token.endswith(("s", "x", "z", "ch", "sh")):
                        variants.add(token + "es")
                    else:
                        variants.update({token + "s", token + "es"})
                else:
                    variants.add(token + "s")

                escaped_variants = [re.escape(variant) for variant in variants]
                pattern_tokens.append(f"(?:{'|'.join(escaped_variants)})")
            else:
                pattern_tokens.append(escaped_token)

        pattern = r"\b" + r"\s+".join(pattern_tokens) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

        return normalized_name.lower() in text.lower()

    async def _extract_relationships_from_chunk(
        self, text_chunk: str, entity_context: str
    ) -> List[ExtractedRelationship]:
        """Extract relationships from a single text chunk"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at identifying relationships between scientific entities. 
                        Extract relationships that show how concepts, methods, algorithms, and theories interact, 
                        support each other, contradict each other, or are otherwise connected. Focus on meaningful 
                        scientific relationships, not trivial mentions.""",
                    },
                    {
                        "role": "user",
                        "content": f"{entity_context}\n\nExtract relationships from this text:\n\n{text_chunk}",
                    },
                ],
                functions=[self.relationship_extraction_function],
                function_call={"name": "extract_relationships"},
                temperature=0.1,
                max_tokens=2000,
            )

            # Parse function call response
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "extract_relationships":
                relationships_data = json.loads(function_call.arguments)
                relationships = []

                for rel_dict in relationships_data.get("relationships", []):
                    try:
                        relationship = ExtractedRelationship(
                            source=rel_dict["source"],
                            target=rel_dict["target"],
                            type=RelationshipType(rel_dict["type"]),
                            description=rel_dict["description"],
                            confidence=rel_dict["confidence"],
                            context=rel_dict["context"],
                        )
                        relationships.append(relationship)
                    except (KeyError, ValueError) as e:
                        self.logger.warning(
                            "Invalid relationship data",
                            relationship=rel_dict,
                            error=str(e),
                        )

                return relationships

            return []

        except Exception as e:
            self.logger.error(
                "Failed to extract relationships from chunk", error=str(e)
            )
            return []

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks while preserving sentence boundaries"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        sentences = text.split(". ")
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _deduplicate_entities(
        self, entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """Remove duplicate entities based on name and type"""
        seen = set()
        deduplicated = []

        for entity in entities:
            key = (entity.name.lower(), entity.type)
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
            else:
                # Update confidence if this instance has higher confidence
                for existing in deduplicated:
                    if (existing.name.lower(), existing.type) == key:
                        if entity.confidence > existing.confidence:
                            existing.confidence = entity.confidence
                            existing.description = entity.description
                            existing.context = entity.context
                        break

        return deduplicated

    def _deduplicate_relationships(
        self, relationships: List[ExtractedRelationship]
    ) -> List[ExtractedRelationship]:
        """Remove duplicate relationships"""
        seen = set()
        deduplicated = []

        for rel in relationships:
            key = (rel.source.lower(), rel.target.lower(), rel.type)
            if key not in seen:
                seen.add(key)
                deduplicated.append(rel)
            else:
                # Update confidence if this instance has higher confidence
                for existing in deduplicated:
                    if (
                        existing.source.lower(),
                        existing.target.lower(),
                        existing.type,
                    ) == key:
                        if rel.confidence > existing.confidence:
                            existing.confidence = rel.confidence
                            existing.description = rel.description
                            existing.context = rel.context
                        break

        return deduplicated

    def _filter_valid_relationships(
        self, relationships: List[ExtractedRelationship], valid_entity_names: List[str]
    ) -> List[ExtractedRelationship]:
        """Filter relationships to only include known entities"""
        valid_names_lower = [name.lower() for name in valid_entity_names]

        filtered = []
        for rel in relationships:
            if (
                rel.source.lower() in valid_names_lower
                and rel.target.lower() in valid_names_lower
                and rel.source.lower() != rel.target.lower()
            ):  # Avoid self-references
                filtered.append(rel)

        return filtered

    def get_extraction_stats(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship],
    ) -> Dict[str, Any]:
        """Get statistics about extracted entities and relationships"""
        entity_type_counts = {}
        relationship_type_counts = {}

        for entity in entities:
            entity_type_counts[entity.type.value] = (
                entity_type_counts.get(entity.type.value, 0) + 1
            )

        for rel in relationships:
            relationship_type_counts[rel.type.value] = (
                relationship_type_counts.get(rel.type.value, 0) + 1
            )

        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_types": entity_type_counts,
            "relationship_types": relationship_type_counts,
            "avg_entity_confidence": (
                sum(e.confidence for e in entities) / len(entities) if entities else 0
            ),
            "avg_relationship_confidence": (
                sum(r.confidence for r in relationships) / len(relationships)
                if relationships
                else 0
            ),
        }
