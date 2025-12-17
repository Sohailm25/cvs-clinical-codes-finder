# ABOUTME: RxTerms tool adapter for drug name and code lookup.
# ABOUTME: Wraps Clinical Tables API for RxNorm-derived drug terminology.

from src.tools.base import ClinicalTablesClient, CodeResult


class RxTermsTool:
    """Tool for searching RxTerms drug codes."""

    system = "RxTerms"
    table = "rxterms"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search RxTerms drug codes by term.

        Args:
            term: Search term (drug name, strength, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with drug codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=["DISPLAY_NAME", "DISPLAY_NAME_SYNONYM"],
            display_fields=["DISPLAY_NAME"],
            extra_fields=["RXCUIS", "STRENGTHS_AND_FORMS", "SXDG_RXCUI"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata=r.get("extra", {}),
                source={"tool": "rxterms", "term_used": term},
            )
            for r in results
        ]
