# ABOUTME: Base HTTP client for Clinical Tables API.
# ABOUTME: Provides async request handling with timeouts, retries, and response parsing.

from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlencode

import httpx


class APIError(Exception):
    """Raised when Clinical Tables API request fails."""

    pass


@dataclass
class CodeResult:
    """Normalized result from any Clinical Tables API endpoint."""

    system: str
    code: str
    display: str
    confidence: float
    metadata: dict[str, Any]
    source: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


class ClinicalTablesClient:
    """Async HTTP client for Clinical Tables API."""

    def __init__(self, timeout: float = 5.0, max_retries: int = 2):
        self.base_url = "https://clinicaltables.nlm.nih.gov/api"
        self.timeout = timeout
        self.max_retries = max_retries

    def build_url(self, table: str, params: dict[str, Any]) -> str:
        """Build full API URL with query parameters."""
        base = f"{self.base_url}/{table}/v3/search"
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    async def _fetch(self, url: str) -> list[Any]:
        """Execute HTTP GET request and return JSON response."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def search(
        self,
        table: str,
        term: str,
        max_results: int = 10,
        search_fields: list[str] | None = None,
        display_fields: list[str] | None = None,
        extra_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search a Clinical Tables endpoint.

        Args:
            table: API table name (e.g., 'icd10cm', 'loinc_items', 'hpo')
            term: Search term
            max_results: Maximum results to return (default 10, max 500)
            search_fields: Fields to search (sf parameter)
            display_fields: Fields to display (df parameter)
            extra_fields: Additional fields to return (ef parameter)

        Returns:
            List of result dictionaries with code, display, and optional extra fields.

        Raises:
            APIError: On timeout, HTTP error, or invalid response.
        """
        params: dict[str, Any] = {
            "terms": term,
            "maxList": min(max_results, 500),
        }

        if search_fields:
            params["sf"] = ",".join(search_fields)
        if display_fields:
            params["df"] = ",".join(display_fields)
        if extra_fields:
            params["ef"] = ",".join(extra_fields)

        url = self.build_url(table, params)

        try:
            response = await self._fetch(url)
        except httpx.TimeoutException as e:
            raise APIError(f"Request timeout for {table}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"HTTP error {e.response.status_code} for {table}: {e}") from e
        except Exception as e:
            raise APIError(f"Request failed for {table}: {e}") from e

        return self._parse_response(response, extra_fields)

    def _parse_response(
        self,
        response: list[Any],
        extra_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parse the 5-element array response from Clinical Tables API.

        Response format:
        [0] total_count: int
        [1] codes: list[str]
        [2] extra_data: dict[str, list]
        [3] display_strings: list[list[str]]
        [4] code_systems: list | None
        """
        if not response or len(response) < 4:
            return []

        total_count = response[0]
        codes = response[1] or []
        extra_data = response[2] or {}
        display_strings = response[3] or []

        if not codes:
            return []

        results = []
        for i, code in enumerate(codes):
            display = ""
            if i < len(display_strings) and display_strings[i]:
                ds = display_strings[i]
                if isinstance(ds, list):
                    # Multi-field display: skip the code field, join remaining
                    # If first element matches code, skip it; otherwise join all
                    if len(ds) > 1 and ds[0] == code:
                        display = " - ".join(str(x) for x in ds[1:] if x)
                    else:
                        display = " - ".join(str(x) for x in ds if x)
                else:
                    display = str(ds)

            result: dict[str, Any] = {
                "code": code,
                "display": display,
            }

            if extra_fields and extra_data:
                result["extra"] = {}
                for field in extra_fields:
                    if field in extra_data and i < len(extra_data[field]):
                        result["extra"][field] = extra_data[field][i]

            results.append(result)

        return results
