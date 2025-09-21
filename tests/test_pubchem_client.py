# tests/test_pubchem_client.py
from unittest.mock import patch

import httpx
import pytest

from src.clients.pubchem import (
    PubChemAPIError,
    PubChemClient,
    get_synonyms,
)

# Mock responses
SYNONYMS_RESPONSE = {
    "InformationList": {
        "Information": [
            {
                "Synonym": [
                    "aspirin",
                    "acetylsalicylic acid",
                    "2-acetoxybenzoic acid",
                    "Aspirin [USAN:USP:INN:BAN:JAN]",
                    "salicylic acid acetate",
                ]
            }
        ]
    }
}

FAULT_RESPONSE = {
    "Fault": {
        "Code": "PUGREST.BadRequest",
        "Message": "No records found",
        "Details": ["No CID found that matches the given name"],
    }
}

EMPTY_RESPONSE = {"InformationList": {"Information": []}}


@pytest.fixture
async def pubchem_client(mock_http_session):
    """Create a test client using the shared mock session."""
    client = PubChemClient()
    client.session = mock_http_session
    yield client


class TestPubChemClient:
    """Test the PubChemClient methods with mocked HTTP responses."""

    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_get_synonyms_success(self, mock_request, pubchem_client):
        """Test successful synonym retrieval."""
        mock_request.return_value = SYNONYMS_RESPONSE

        result = await pubchem_client.get_synonyms("aspirin")

        assert len(result) <= 3  # Returns first 3 synonyms
        assert "aspirin" in result
        assert "acetylsalicylic acid" in result
        mock_request.assert_called_once()

    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_get_synonyms_fault_response(self, mock_request, pubchem_client):
        """Test PubChem fault response handling."""
        mock_request.return_value = FAULT_RESPONSE

        result = await pubchem_client.get_synonyms("invaliddrugname123")

        assert result == []
        mock_request.assert_called_once()

    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_get_synonyms_empty_response(self, mock_request, pubchem_client):
        """Test empty response handling."""
        mock_request.return_value = EMPTY_RESPONSE

        result = await pubchem_client.get_synonyms("test")

        assert result == []
        mock_request.assert_called_once()

    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_get_synonyms_api_error(self, mock_request, pubchem_client):
        """Test API error handling."""
        mock_request.side_effect = PubChemAPIError("API failed")

        result = await pubchem_client.get_synonyms("test")

        assert result == []

    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_get_synonyms_unexpected_error(self, mock_request, pubchem_client):
        """Test unexpected error handling."""
        mock_request.side_effect = Exception("Unexpected error")

        result = await pubchem_client.get_synonyms("test")

        assert result == []

    async def test_make_request_success(self, pubchem_client):
        """Test successful HTTP request."""
        with patch.object(pubchem_client.session, "get") as mock_get:
            mock_response = type(
                "MockResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"test": "data"},
                },
            )()
            mock_get.return_value = mock_response

            result = await pubchem_client._make_request("test/endpoint")

            assert result == {"test": "data"}
            mock_get.assert_called_once()

    async def test_make_request_http_error(self, pubchem_client):
        """Test HTTP error handling."""
        with patch.object(pubchem_client.session, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "404", request=None, response=None
            )

            with pytest.raises(PubChemAPIError) as exc_info:
                await pubchem_client._make_request("test/endpoint")

            assert "PubChem API error" in str(exc_info.value)

    async def test_url_encoding(self, pubchem_client):
        """Test that drug names with spaces are properly URL encoded."""
        with patch.object(pubchem_client, "_make_request") as mock_request:
            mock_request.return_value = SYNONYMS_RESPONSE

            await pubchem_client.get_synonyms("drug name with spaces")

            # Verify the endpoint has URL-encoded spaces
            called_endpoint = mock_request.call_args[0][0]
            assert "drug%20name%20with%20spaces" in called_endpoint

    @patch("src.clients.pubchem.clean_drug_name")
    @patch("src.clients.pubchem.PubChemClient._make_request")
    async def test_synonym_cleaning(self, mock_request, mock_clean, pubchem_client):
        """Test that synonyms are cleaned properly."""
        # Mock response with unclean synonyms
        dirty_response = {
            "InformationList": {
                "Information": [
                    {
                        "Synonym": [
                            "aspirin",
                            "dirty-name-123",
                            "clean name",
                            "",  # Empty string
                            "another dirty name!@#",
                        ]
                    }
                ]
            }
        }
        mock_request.return_value = dirty_response

        # Mock cleaning function to return predictable results
        def mock_clean_side_effect(name):
            if name == "aspirin":
                return "aspirin"
            elif name == "dirty-name-123":
                return "dirty name"
            elif name == "clean name":
                return "clean name"
            elif name == "":
                return ""  # Empty string
            elif name == "another dirty name!@#":
                return "another dirty name"
            return name

        mock_clean.side_effect = mock_clean_side_effect

        result = await pubchem_client.get_synonyms("test")

        # Should return first 3 non-empty cleaned synonyms
        assert len(result) == 3
        assert "aspirin" in result
        assert "dirty name" in result
        assert "clean name" in result
        assert "" not in result  # Empty strings should be filtered out


class TestConvenienceFunctions:
    """Test the module-level convenience functions."""

    @patch("src.clients.pubchem.PubChemClient.get_synonyms")
    async def test_get_synonyms_convenience(self, mock_get_synonyms):
        """Test the convenience function."""
        mock_get_synonyms.return_value = ["aspirin", "acetylsalicylic acid"]

        result = await get_synonyms("aspirin")

        assert result == ["aspirin", "acetylsalicylic acid"]
        mock_get_synonyms.assert_called_once_with("aspirin")

    @patch("src.clients.pubchem.PubChemClient.get_synonyms")
    async def test_get_synonyms_convenience_empty(self, mock_get_synonyms):
        """Test convenience function with empty result."""
        mock_get_synonyms.return_value = []

        result = await get_synonyms("invaliddrugname123")

        assert result == []


class TestErrorHandling:
    """Test custom error classes and error scenarios."""

    async def test_pubchem_api_error_creation(self):
        """Test PubChemAPIError creation."""
        error = PubChemAPIError("API failed")
        assert "API failed" in str(error)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    async def test_common_drug_lookup(self, pubchem_client):
        """Test looking up a common drug like aspirin."""
        with patch.object(pubchem_client, "_make_request") as mock_request:
            mock_request.return_value = SYNONYMS_RESPONSE

            result = await pubchem_client.get_synonyms("aspirin")

            assert len(result) <= 3
            assert any("aspirin" in syn.lower() for syn in result)

    async def test_limit_to_three_synonyms(self, pubchem_client):
        """Test that only first 3 synonyms are returned."""
        large_response = {
            "InformationList": {
                "Information": [
                    {
                        "Synonym": [f"synonym_{i}" for i in range(10)]  # 10 synonyms
                    }
                ]
            }
        }

        with patch.object(pubchem_client, "_make_request") as mock_request:
            mock_request.return_value = large_response

            with patch("src.clients.pubchem.clean_drug_name") as mock_clean:
                mock_clean.side_effect = lambda x: x  # Return as-is

                result = await pubchem_client.get_synonyms("test")

                assert len(result) == 3  # Should limit to 3
                assert result == ["synonym_0", "synonym_1", "synonym_2"]

    async def test_context_manager_usage(self):
        """Test using the client as a context manager."""
        with patch("src.clients.pubchem.PubChemClient.get_synonyms") as mock_method:
            mock_method.return_value = ["test"]

            result = await get_synonyms("aspirin")

            assert result == ["test"]
