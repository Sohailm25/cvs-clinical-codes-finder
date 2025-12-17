# ABOUTME: Tests for the base Clinical Tables HTTP client.
# ABOUTME: Validates response parsing, error handling, and timeout behavior.

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from src.tools.base import ClinicalTablesClient, CodeResult, APIError


class TestCodeResult:
    """Tests for the CodeResult dataclass."""

    def test_code_result_creation(self):
        """CodeResult should store all required fields."""
        result = CodeResult(
            system="ICD-10-CM",
            code="E11.9",
            display="Type 2 diabetes mellitus without complications",
            confidence=0.0,
            metadata={},
            source={"tool": "icd10", "term_used": "diabetes"},
        )
        assert result.system == "ICD-10-CM"
        assert result.code == "E11.9"
        assert result.display == "Type 2 diabetes mellitus without complications"
        assert result.confidence == 0.0
        assert result.source["tool"] == "icd10"

    def test_code_result_to_dict(self):
        """CodeResult should serialize to dict."""
        result = CodeResult(
            system="LOINC",
            code="2345-7",
            display="Glucose [Mass/volume] in Serum or Plasma",
            confidence=0.85,
            metadata={"component": "Glucose"},
            source={"tool": "loinc", "term_used": "glucose"},
        )
        d = result.to_dict()
        assert d["system"] == "LOINC"
        assert d["code"] == "2345-7"
        assert d["confidence"] == 0.85
        assert d["metadata"]["component"] == "Glucose"


class TestClinicalTablesClient:
    """Tests for the HTTP client wrapper."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return ClinicalTablesClient(timeout=5.0)

    def test_client_base_url(self, client):
        """Client should have correct base URL."""
        assert client.base_url == "https://clinicaltables.nlm.nih.gov/api"

    def test_build_url(self, client):
        """Client should build correct API URLs."""
        url = client.build_url("icd10cm", {"terms": "diabetes", "maxList": 10})
        assert "icd10cm/v3/search" in url
        assert "terms=diabetes" in url
        assert "maxList=10" in url

    @pytest.mark.asyncio
    async def test_search_parses_response(self, client):
        """Client should parse the 5-element array response format."""
        mock_response = [
            42,  # total count
            ["E11.9", "E11.65"],  # codes
            {},  # extra fields
            [["Type 2 diabetes mellitus without complications"], ["Type 2 DM with hyperglycemia"]],
            None,  # code systems
        ]

        with patch.object(client, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            results = await client.search("icd10cm", "diabetes", max_results=10)

            assert len(results) == 2
            assert results[0]["code"] == "E11.9"
            assert results[0]["display"] == "Type 2 diabetes mellitus without complications"
            assert results[1]["code"] == "E11.65"

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self, client):
        """Client should handle empty results gracefully."""
        mock_response = [0, [], {}, [], None]

        with patch.object(client, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            results = await client.search("icd10cm", "xyznonexistent", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_includes_extra_fields(self, client):
        """Client should include extra fields when requested."""
        mock_response = [
            1,
            ["2345-7"],
            {"COMPONENT": ["Glucose"]},
            [["Glucose [Mass/volume] in Serum or Plasma"]],
            None,
        ]

        with patch.object(client, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            results = await client.search(
                "loinc_items",
                "glucose",
                max_results=10,
                extra_fields=["COMPONENT"],
            )

            assert results[0]["extra"]["COMPONENT"] == "Glucose"

    @pytest.mark.asyncio
    async def test_search_raises_on_timeout(self, client):
        """Client should raise APIError on timeout."""
        with patch.object(client, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(APIError) as exc_info:
                await client.search("icd10cm", "diabetes", max_results=10)

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_raises_on_http_error(self, client):
        """Client should raise APIError on HTTP errors."""
        with patch.object(client, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(500),
            )

            with pytest.raises(APIError) as exc_info:
                await client.search("icd10cm", "diabetes", max_results=10)

            assert "500" in str(exc_info.value) or "error" in str(exc_info.value).lower()


class TestClinicalTablesClientIntegration:
    """Integration tests that hit the real API (marked for selective running)."""

    @pytest.fixture
    def client(self):
        return ClinicalTablesClient(timeout=10.0)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_icd10_search(self, client):
        """Test real ICD-10 API search for 'diabetes'."""
        results = await client.search(
            "icd10cm",
            "diabetes",
            max_results=5,
            search_fields=["code", "name"],
        )

        assert len(results) > 0
        assert any("diabetes" in r["display"].lower() for r in results)
        assert all(r["code"] for r in results)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_hpo_search(self, client):
        """Test real HPO API search for 'ataxia'."""
        results = await client.search(
            "hpo",
            "ataxia",
            max_results=5,
            search_fields=["id", "name", "synonym.term"],
        )

        assert len(results) > 0
        assert any("ataxia" in r["display"].lower() for r in results)
