# ABOUTME: LLM-driven clinical query expansion service.
# ABOUTME: Suggests semantically related clinical concepts with static fallback.

import asyncio
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.config import config

logger = logging.getLogger(__name__)


EXPANSION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical terminology expert. Given a medical query and target coding systems, suggest semantically related clinical concepts.

For each query, identify:
1. Related diagnoses/conditions (for ICD-10-CM, HPO)
2. Related diagnostic tests/lab values (for LOINC, UCUM)
3. Related medications/treatments (for RxTerms)

Return ONLY valid JSON in this exact format:
{{"diagnoses": ["term1", "term2"], "labs": ["term1", "term2"], "medications": ["term1", "term2"]}}

Rules:
- Include 3-5 terms per category (only categories relevant to the target systems)
- Use standard medical terminology
- Prioritize commonly used clinical terms
- Do not include the original query term
- Return empty arrays [] for irrelevant categories"""),
    ("human", """Query: {query}
Target systems: {systems}

Suggest related clinical terms:"""),
])


class ClinicalExpansionService:
    """LLM-driven clinical query expansion with caching and fallback."""

    def __init__(self, model: str | None = None, cache_ttl: int | None = None):
        self._model = model or config.EXPANSION_MODEL
        self._cache_ttl = cache_ttl if cache_ttl is not None else config.EXPANSION_CACHE_TTL
        self._cache: dict[str, tuple[float, dict[str, list[str]]]] = {}
        self._lock = asyncio.Lock()

    def _make_cache_key(self, query: str, systems: list[str]) -> str:
        """Generate cache key from query and systems."""
        return f"{query.lower()}:{','.join(sorted(systems))}"

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached entry is still valid."""
        import time
        if key not in self._cache:
            return False
        timestamp, _ = self._cache[key]
        return time.time() - timestamp < self._cache_ttl

    async def expand(
        self,
        query: str,
        selected_systems: list[str],
        max_per_category: int = 5,
    ) -> dict[str, list[str]]:
        """
        Expand query with clinically related terms.

        Args:
            query: Original search query
            selected_systems: Target coding systems
            max_per_category: Max terms per category

        Returns:
            Dict with keys: diagnoses, labs, medications
        """
        if not config.EXPANSION_ENABLED:
            return await self._static_fallback(query, selected_systems, max_per_category)

        cache_key = self._make_cache_key(query, selected_systems)

        # Check cache
        if self._is_cache_valid(cache_key):
            _, cached_result = self._cache[cache_key]
            logger.debug(f"Cache hit for expansion: {query}")
            return cached_result

        # Try LLM expansion
        try:
            result = await self._llm_expand(query, selected_systems, max_per_category)

            # Cache result
            import time
            async with self._lock:
                self._cache[cache_key] = (time.time(), result)

            return result

        except Exception as e:
            logger.warning(f"LLM expansion failed, using fallback: {e}")
            return await self._static_fallback(query, selected_systems, max_per_category)

    async def _llm_expand(
        self,
        query: str,
        systems: list[str],
        max_per_category: int,
    ) -> dict[str, list[str]]:
        """Use LLM to expand query."""
        llm = ChatOpenAI(
            model=self._model,
            temperature=0.3,
            api_key=config.OPENAI_API_KEY,
        )

        chain = EXPANSION_PROMPT | llm

        response = await chain.ainvoke({
            "query": query,
            "systems": ", ".join(systems),
        })

        # Parse JSON response
        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Validate and limit
        validated: dict[str, list[str]] = {
            "diagnoses": [],
            "labs": [],
            "medications": [],
        }

        for key in validated:
            if key in result and isinstance(result[key], list):
                validated[key] = [
                    str(term) for term in result[key][:max_per_category]
                    if term and str(term).lower() != query.lower()
                ]

        logger.debug(f"LLM expanded '{query}' to {sum(len(v) for v in validated.values())} terms")
        return validated

    async def _static_fallback(
        self,
        query: str,
        selected_systems: list[str],
        max_per_category: int,
    ) -> dict[str, list[str]]:
        """Fallback to static CLINICAL_RELATIONSHIPS dict."""
        from src.agent.multi_hop import CLINICAL_RELATIONSHIPS

        result: dict[str, list[str]] = {
            "diagnoses": [],
            "labs": [],
            "medications": [],
        }

        query_lower = query.lower()

        for condition, relations in CLINICAL_RELATIONSHIPS.items():
            if condition in query_lower:
                # Map to appropriate categories based on selected systems
                if "ICD-10-CM" in selected_systems or "HPO" in selected_systems:
                    result["diagnoses"].extend(relations.get("related_diagnoses", []))
                if "LOINC" in selected_systems or "UCUM" in selected_systems:
                    result["labs"].extend(relations.get("related_labs", []))
                if "RxTerms" in selected_systems:
                    result["medications"].extend(relations.get("related_medications", []))

        # Dedupe and limit
        for key in result:
            seen = set()
            unique = []
            for term in result[key]:
                if term.lower() not in seen and term.lower() != query_lower:
                    seen.add(term.lower())
                    unique.append(term)
            result[key] = unique[:max_per_category]

        return result

    def clear_cache(self) -> None:
        """Clear the expansion cache."""
        self._cache.clear()


# Singleton instance
_expansion_service: ClinicalExpansionService | None = None


async def get_expansion_service() -> ClinicalExpansionService:
    """Get or create the expansion service singleton."""
    global _expansion_service
    if _expansion_service is None:
        _expansion_service = ClinicalExpansionService()
    return _expansion_service


def reset_expansion_service() -> None:
    """Reset the singleton (for testing)."""
    global _expansion_service
    if _expansion_service:
        _expansion_service.clear_cache()
    _expansion_service = None
