# ABOUTME: Tests for Clinical Tables API tool adapters.
# ABOUTME: Validates each tool wrapper returns properly formatted CodeResult objects.

import pytest
from unittest.mock import AsyncMock, patch

from src.tools.base import CodeResult
from src.tools.icd10 import ICD10Tool
from src.tools.loinc import LOINCTool
from src.tools.rxterms import RxTermsTool
from src.tools.hcpcs import HCPCSTool
from src.tools.ucum import UCUMTool
from src.tools.hpo import HPOTool


class TestICD10Tool:
    """Tests for ICD-10-CM tool adapter."""

    @pytest.fixture
    def tool(self):
        return ICD10Tool()

    def test_system_name(self, tool):
        assert tool.system == "ICD-10-CM"

    def test_table_name(self, tool):
        assert tool.table == "icd10cm"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        """Tool should return list of CodeResult objects."""
        mock_response = [
            {"code": "E11.9", "display": "Type 2 diabetes mellitus without complications"},
            {"code": "E11.65", "display": "Type 2 DM with hyperglycemia"},
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("diabetes", max_results=5)

            assert len(results) == 2
            assert all(isinstance(r, CodeResult) for r in results)
            assert results[0].system == "ICD-10-CM"
            assert results[0].code == "E11.9"
            assert "diabetes" in results[0].display.lower()

    @pytest.mark.asyncio
    async def test_search_uses_correct_fields(self, tool):
        """Tool should use correct search and display fields."""
        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            await tool.search("test", max_results=5)

            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args[1]
            assert "code" in call_kwargs.get("search_fields", [])
            assert "name" in call_kwargs.get("search_fields", [])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("diabetes", max_results=5)
        assert len(results) > 0
        assert all(isinstance(r, CodeResult) for r in results)
        assert all(r.system == "ICD-10-CM" for r in results)


class TestLOINCTool:
    """Tests for LOINC tool adapter."""

    @pytest.fixture
    def tool(self):
        return LOINCTool()

    def test_system_name(self, tool):
        assert tool.system == "LOINC"

    def test_table_name(self, tool):
        assert tool.table == "loinc_items"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        mock_response = [
            {"code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"},
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("glucose", max_results=5)

            assert len(results) == 1
            assert results[0].system == "LOINC"
            assert results[0].code == "2345-7"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("glucose test", max_results=5)
        assert len(results) > 0
        assert all(r.system == "LOINC" for r in results)


class TestRxTermsTool:
    """Tests for RxTerms tool adapter."""

    @pytest.fixture
    def tool(self):
        return RxTermsTool()

    def test_system_name(self, tool):
        assert tool.system == "RxTerms"

    def test_table_name(self, tool):
        assert tool.table == "rxterms"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        mock_response = [
            {
                "code": "metformin (Oral Pill)",
                "display": "metformin (Oral Pill)",
                "extra": {"RXCUIS": "123456", "STRENGTHS_AND_FORMS": "500 MG Oral Tablet"},
            },
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("metformin", max_results=5)

            assert len(results) == 1
            assert results[0].system == "RxTerms"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("metformin", max_results=5)
        assert len(results) > 0
        assert all(r.system == "RxTerms" for r in results)


class TestHCPCSTool:
    """Tests for HCPCS tool adapter."""

    @pytest.fixture
    def tool(self):
        return HCPCSTool()

    def test_system_name(self, tool):
        assert tool.system == "HCPCS"

    def test_table_name(self, tool):
        assert tool.table == "hcpcs"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        mock_response = [
            {"code": "K0001", "display": "Standard wheelchair"},
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("wheelchair", max_results=5)

            assert len(results) == 1
            assert results[0].system == "HCPCS"
            assert results[0].code == "K0001"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("wheelchair", max_results=5)
        assert len(results) > 0
        assert all(r.system == "HCPCS" for r in results)


class TestUCUMTool:
    """Tests for UCUM tool adapter."""

    @pytest.fixture
    def tool(self):
        return UCUMTool()

    def test_system_name(self, tool):
        assert tool.system == "UCUM"

    def test_table_name(self, tool):
        assert tool.table == "ucum"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        mock_response = [
            {"code": "mg/dL", "display": "milligram per deciliter"},
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("mg/dL", max_results=5)

            assert len(results) == 1
            assert results[0].system == "UCUM"
            assert results[0].code == "mg/dL"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("mg", max_results=5)
        assert len(results) > 0
        assert all(r.system == "UCUM" for r in results)


class TestHPOTool:
    """Tests for HPO tool adapter."""

    @pytest.fixture
    def tool(self):
        return HPOTool()

    def test_system_name(self, tool):
        assert tool.system == "HPO"

    def test_table_name(self, tool):
        assert tool.table == "hpo"

    @pytest.mark.asyncio
    async def test_search_returns_code_results(self, tool):
        mock_response = [
            {"code": "HP:0001251", "display": "Ataxia"},
        ]

        with patch.object(tool.client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tool.search("ataxia", max_results=5)

            assert len(results) == 1
            assert results[0].system == "HPO"
            assert results[0].code == "HP:0001251"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self, tool):
        """Integration test against real API."""
        results = await tool.search("ataxia", max_results=5)
        assert len(results) > 0
        assert all(r.system == "HPO" for r in results)
        assert any("ataxia" in r.display.lower() for r in results)
