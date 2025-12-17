# ABOUTME: ICD-10-CM tool adapter for diagnosis code lookup.
# ABOUTME: Wraps Clinical Tables API for International Classification of Diseases codes.

from src.tools.base import ClinicalTablesClient, CodeResult


class ICD10Tool:
    """Tool for searching ICD-10-CM diagnosis codes."""

    system = "ICD-10-CM"
    table = "icd10cm"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search ICD-10-CM codes by term.

        Args:
            term: Search term (disease name, condition, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with diagnosis codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=["code", "name"],
            display_fields=["code", "name"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata={},
                source={"tool": "icd10", "term_used": term},
            )
            for r in results
        ]
