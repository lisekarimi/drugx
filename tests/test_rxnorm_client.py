# tests/test_rxnorm_client.py
from unittest.mock import patch

import pytest

from src.clients.rxnorm import (
    DrugNotFoundError,
    RxNormAPIError,
    RxNormClient,
    normalize_drug_safe,
)

# Mock responses - keep these simple with hardcoded values
ASPIRIN_RXCUI_RESPONSE = {"idGroup": {"rxnormId": ["1191"]}}

ASPIRIN_RELATED_RESPONSE = {
    "relatedGroup": {
        "conceptGroup": [{"tty": "IN", "conceptProperties": [{"name": "aspirin"}]}]
    }
}

ASPIRIN_CLASSES_RESPONSE = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "rxclassMinConceptItem": {
                    "classType": "EPC",
                    "className": "Platelet Aggregation Inhibitor",
                },
                "relaSource": "FDASPL",
            }
        ]
    }
}

EMPTY_RXCUI_RESPONSE = {"idGroup": {}}

APPROXIMATE_RESPONSE = {
    "approximateGroup": {
        "candidate": [{"rxcui": "1191", "name": "aspirin", "score": "100", "rank": "1"}]
    }
}


@pytest.fixture
async def rxnorm_client(mock_http_session):
    """Create a test client using the shared mock session."""
    client = RxNormClient()
    client.session = mock_http_session
    yield client
    # No need to close since it's a mock


@pytest.fixture
def sample_drug_data():
    """Provide common test drug data for all modules."""
    return {
        "aspirin": {"rxcui": "1191", "in": "aspirin"},
        "warfarin": {"rxcui": "11289", "in": "warfarin"},
        "invalid_drug": "invaliddrugname123",
    }


class TestRxNormClient:
    """Test the RxNormClient methods with mocked HTTP responses."""

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_get_rxcui_exact_match(
        self, mock_request, rxnorm_client, sample_drug_data
    ):
        """Test finding exact RxCUI match."""
        mock_request.return_value = ASPIRIN_RXCUI_RESPONSE

        rxcui = await rxnorm_client.get_rxcui(sample_drug_data["aspirin"]["in"])

        assert rxcui == sample_drug_data["aspirin"]["rxcui"]
        mock_request.assert_called_once_with(
            "rxcui.json",
            params={"name": sample_drug_data["aspirin"]["in"], "search": "2"},
        )

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_get_rxcui_approximate_match(self, mock_request, rxnorm_client):
        """Test fallback to approximate search."""
        mock_request.side_effect = [
            EMPTY_RXCUI_RESPONSE,  # No exact match
            APPROXIMATE_RESPONSE,  # Approximate match found
        ]

        rxcui = await rxnorm_client.get_rxcui("aspirine")

        assert rxcui == "1191"
        assert mock_request.call_count == 2

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_get_rxcui_not_found(
        self, mock_request, rxnorm_client, sample_drug_data
    ):
        """Test drug not found."""
        mock_request.side_effect = [
            EMPTY_RXCUI_RESPONSE,  # No exact match
            {"approximateGroup": {}},  # No approximate match
            {"suggestionGroup": {}},  # No spelling suggestions
        ]

        with pytest.raises(DrugNotFoundError) as exc_info:
            await rxnorm_client.get_rxcui(sample_drug_data["invalid_drug"])

        assert sample_drug_data["invalid_drug"] in str(exc_info.value)

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_get_drug_info_success(
        self, mock_request, rxnorm_client, sample_drug_data
    ):
        """Test getting drug info."""
        mock_request.side_effect = [
            ASPIRIN_RELATED_RESPONSE,  # Ingredient name
            ASPIRIN_CLASSES_RESPONSE,  # Classifications
        ]

        result = await rxnorm_client.get_drug_info(sample_drug_data["aspirin"]["rxcui"])

        assert result["ingredient_name"] == sample_drug_data["aspirin"]["in"]
        assert "epc" in result["classes"]
        assert len(result["classes"]["epc"]) > 0

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_get_drug_info_no_ingredient(
        self, mock_request, rxnorm_client, sample_drug_data
    ):
        """Test error when no ingredient found."""
        mock_request.side_effect = [
            {"relatedGroup": {}},  # No ingredient
            ASPIRIN_CLASSES_RESPONSE,  # Classifications
        ]

        with pytest.raises(RxNormAPIError) as exc_info:
            await rxnorm_client.get_drug_info(sample_drug_data["aspirin"]["rxcui"])

        assert "No ingredient name found" in str(exc_info.value)

    @patch("src.clients.rxnorm.RxNormClient._make_request")
    async def test_normalize_drug_success(
        self, mock_request, rxnorm_client, sample_drug_data
    ):
        """Test full drug normalization."""
        mock_request.side_effect = [
            ASPIRIN_RXCUI_RESPONSE,  # Get RxCUI
            ASPIRIN_RELATED_RESPONSE,  # Get ingredient
            ASPIRIN_CLASSES_RESPONSE,  # Get classes
        ]

        result = await rxnorm_client.normalize_drug(sample_drug_data["aspirin"]["in"])

        assert result["rxcui"] == sample_drug_data["aspirin"]["rxcui"]
        assert result["in"] == sample_drug_data["aspirin"]["in"]
        assert "classes" in result


class TestNormalizeDrugSafe:
    """Test the safe normalization wrapper function."""

    @patch("src.clients.rxnorm.RxNormClient.normalize_drug")
    async def test_normalize_drug_safe_success(self, mock_normalize, sample_drug_data):
        """Test safe normalization success."""
        mock_normalize.return_value = {
            "rxcui": sample_drug_data["aspirin"]["rxcui"],
            "in": sample_drug_data["aspirin"]["in"],
            "classes": {},
        }

        result = await normalize_drug_safe(sample_drug_data["aspirin"]["in"])

        assert result["rxcui"] == sample_drug_data["aspirin"]["rxcui"]
        assert "error" not in result

    @patch("src.clients.rxnorm.RxNormClient.normalize_drug")
    async def test_normalize_drug_safe_with_candidates(
        self, mock_normalize, sample_drug_data
    ):
        """Test safe normalization with candidates."""
        mock_normalize.side_effect = DrugNotFoundError(
            "aspirine", [sample_drug_data["aspirin"]["in"], "asparagine"]
        )

        result = await normalize_drug_safe("aspirine")

        assert "candidates" in result
        assert sample_drug_data["aspirin"]["in"] in result["candidates"]

    @patch("src.clients.rxnorm.RxNormClient.normalize_drug")
    async def test_normalize_drug_safe_error(self, mock_normalize, sample_drug_data):
        """Test safe normalization with API error."""
        mock_normalize.side_effect = RxNormAPIError("API failed")

        result = await normalize_drug_safe(sample_drug_data["aspirin"]["in"])

        assert "error" in result
        assert "API failed" in result["error"]


class TestErrorHandling:
    """Test custom error classes for proper attributes and messages."""

    async def test_drug_not_found_error_with_candidates(self):
        """Test DrugNotFoundError with candidates."""
        error = DrugNotFoundError("test", ["candidate1", "candidate2"])

        assert error.drug_name == "test"
        assert len(error.candidates) == 2
        assert "Candidates" in str(error)

    async def test_drug_not_found_error_without_candidates(self):
        """Test DrugNotFoundError without candidates."""
        error = DrugNotFoundError("test")

        assert error.drug_name == "test"
        assert len(error.candidates) == 0
        assert "Candidates" not in str(error)
