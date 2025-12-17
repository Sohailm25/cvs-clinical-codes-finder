# ABOUTME: HPO tool adapter for phenotype and symptom code lookup.
# ABOUTME: Wraps Clinical Tables API for Human Phenotype Ontology.

from src.tools.base import ClinicalTablesClient, CodeResult


class HPOTool:
    """Tool for searching HPO phenotype codes."""

    system = "HPO"
    table = "hpo"

    def __init__(self, client: ClinicalTablesClient | None = None):
        self.client = client or ClinicalTablesClient()

    async def search(self, term: str, max_results: int = 10) -> list[CodeResult]:
        """
        Search HPO phenotype codes by term.

        Args:
            term: Search term (symptom, trait, phenotype, etc.)
            max_results: Maximum results to return

        Returns:
            List of CodeResult objects with HPO codes
        """
        results = await self.client.search(
            table=self.table,
            term=term,
            max_results=max_results,
            search_fields=["id", "name", "synonym.term"],
            display_fields=["id", "name"],
            extra_fields=["definition"],
        )

        return [
            CodeResult(
                system=self.system,
                code=r["code"],
                display=r["display"],
                confidence=0.0,
                metadata=r.get("extra", {}),
                source={"tool": "hpo", "term_used": term},
            )
            for r in results
        ]
