# ABOUTME: LOINC tool adapter for lab test and measurement code lookup.
# ABOUTME: Wraps Clinical Tables API for Logical Observation Identifiers Names and Codes.

from src.tools.base import ClinicalTablesClient, CodeResult


class LOINCTool:
    """Tool for searching LOINC lab test codes."""

    system = "LOINC"
    table = "loinc_items"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search LOINC codes by term.

        Args:
            term: Search term (lab test name, measurement, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with LOINC codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=[
                "text",
                "COMPONENT",
                "LONG_COMMON_NAME",
                "SHORTNAME",
                "RELATEDNAMES2",
            ],
            display_fields=["LOINC_NUM", "LONG_COMMON_NAME"],
            extra_fields=["COMPONENT", "PROPERTY", "METHOD_TYP"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata=r.get("extra", {}),
                source={"tool": "loinc", "term_used": term},
            )
            for r in results
        ]
