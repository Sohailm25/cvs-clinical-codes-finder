# ABOUTME: HCPCS tool adapter for medical supply and service code lookup.
# ABOUTME: Wraps Clinical Tables API for Healthcare Common Procedure Coding System.

from src.tools.base import ClinicalTablesClient, CodeResult


class HCPCSTool:
    """Tool for searching HCPCS codes."""

    system = "HCPCS"
    table = "hcpcs"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search HCPCS codes by term.

        Args:
            term: Search term (supply name, service, equipment, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with HCPCS codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=["code", "short_desc", "long_desc"],
            display_fields=["code", "long_desc"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata={},
                source={"tool": "hcpcs", "term_used": term},
            )
            for r in results
        ]
