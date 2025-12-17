# ABOUTME: UCUM tool adapter for unit of measure code lookup.
# ABOUTME: Wraps Clinical Tables API for Unified Code for Units of Measure.

from src.tools.base import ClinicalTablesClient, CodeResult


class UCUMTool:
    """Tool for searching UCUM unit codes."""

    system = "UCUM"
    table = "ucum"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search UCUM unit codes by term.

        Args:
            term: Search term (unit name, symbol, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with UCUM codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=["cs_code", "name", "synonyms"],
            display_fields=["cs_code", "name"],
            extra_fields=["category", "loinc_property"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata=r.get("extra", {}),
                source={"tool": "ucum", "term_used": term},
            )
            for r in results
        ]
