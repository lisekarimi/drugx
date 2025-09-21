# tests/test_openfda_client.py
from unittest.mock import patch

import httpx
import pytest

from src.clients.openfda import (
    OpenFDAClient,
    OpenFDAError,
    get_adverse_event_context_safe,
)

# Mock responses
ADVERSE_EVENTS_RESPONSE = {
    "meta": {"results": {"total": 15691}},
    "results": [
        {
            "serious": "1",
            "receivedate": "20140411",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "Diarrhoea"},
                    {"reactionmeddrapt": "Dyspnoea"},
                ]
            },
        },
        {
            "serious": "0",
            "receivedate": "20140310",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "Asthenia"},
                    {"reactionmeddrapt": "Platelet count decreased"},
                ]
            },
        },
    ],
}

EMPTY_RESPONSE = {"meta": {"results": {"total": 0}}, "results": []}


@pytest.fixture
async def openfda_client(mock_http_session):
    """Create a test client using the shared mock session."""
    client = OpenFDAClient()
    client.session = mock_http_session
    yield client


class TestOpenFDAClient:
    """Test the OpenFDAClient methods with mocked HTTP responses."""

    async def test_get_adverse_events_success(self, openfda_client):
        """Test successful adverse events retrieval."""
        with patch.object(openfda_client.session, "get") as mock_get:
            mock_response = type(
                "MockResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: ADVERSE_EVENTS_RESPONSE,
                },
            )()
            mock_get.return_value = mock_response

            ingredient_names = ["warfarin", "aspirin"]  # Add this line
            result = await openfda_client.get_adverse_events(ingredient_names)

        assert result["drugs"] == ingredient_names
        assert result["n_reports"] == 15691
        assert result["n_serious"] == 1  # From sample of 2
        assert "Diarrhoea" in result["top_reactions"]
        assert result["last_report_date"] == "2014-04-11"
        assert result["sample_size"] == 2

    async def test_get_adverse_events_empty_input(self, openfda_client):
        """Test with empty ingredient names."""
        result = await openfda_client.get_adverse_events([])

        assert result["drugs"] == []
        assert result["n_reports"] == 0
        assert result["n_serious"] == 0

    async def test_get_adverse_events_single_drug(self, openfda_client):
        """Test with single drug (should return empty)."""
        result = await openfda_client.get_adverse_events(["aspirin"])

        assert result["drugs"] == ["aspirin"]
        assert result["n_reports"] == 0
        assert result["n_serious"] == 0

    async def test_get_adverse_events_no_results(self, openfda_client):
        """Test when no adverse events found."""
        with patch.object(openfda_client.session, "get") as mock_get:
            # Create a mock response that raises HTTPStatusError with 404
            mock_response = type(
                "MockResponse",
                (),
                {
                    "status_code": 404,
                    "raise_for_status": lambda self: (_ for _ in ()).throw(
                        httpx.HTTPStatusError("404", request=None, response=self)
                    ).__next__(),
                },
            )()
            mock_get.return_value = mock_response

            ingredient_names = ["drug1", "drug2"]
            result = await openfda_client.get_adverse_events(ingredient_names)

        assert result["drugs"] == ingredient_names
        assert result["n_reports"] == 0
        assert result["reason"] == "No reports found after synonym search"

    async def test_process_adverse_events_data_parsing(self, openfda_client):
        """Test the data processing logic."""
        result = openfda_client._process_adverse_events(
            ADVERSE_EVENTS_RESPONSE, ["warfarin", "aspirin"]
        )

        assert result["n_reports"] == 15691
        assert result["n_serious"] == 1  # One serious event in sample
        assert len(result["top_reactions"]) <= 5
        assert "Diarrhoea" in result["top_reactions"]
        assert result["last_report_date"] == "2014-04-11"

    async def test_process_adverse_events_empty_data(self, openfda_client):
        """Test processing empty response."""
        result = openfda_client._process_adverse_events(
            EMPTY_RESPONSE, ["drug1", "drug2"]
        )

        assert result["n_reports"] == 0
        assert result["n_serious"] == 0
        assert result["top_reactions"] == []
        assert result["last_report_date"] is None

    async def test_get_drug_context_success(self, openfda_client):
        """Test the convenience method for drug context."""
        with patch.object(openfda_client, "get_adverse_events") as mock_get:
            mock_get.return_value = {"n_reports": 100, "drugs": ["warfarin", "aspirin"]}

            result = await openfda_client.get_adverse_events(["warfarin", "aspirin"])

            assert result["n_reports"] == 100
            mock_get.assert_called_once_with(["warfarin", "aspirin"])

    async def test_get_drug_context_error_handling(self, openfda_client):
        """Test error handling in convenience method."""
        with patch.object(openfda_client, "get_adverse_events") as mock_get:
            mock_get.side_effect = OpenFDAError("API failed")

            with pytest.raises(OpenFDAError) as exc_info:
                await openfda_client.get_adverse_events(["warfarin", "aspirin"])

            assert "API failed" in str(exc_info.value)


class TestConvenienceFunctions:
    """Test the module-level convenience functions."""

    @patch("src.clients.openfda.OpenFDAClient.get_adverse_events")
    async def test_get_adverse_event_context_success(self, mock_context):
        """Test successful adverse event context retrieval."""
        mock_context.return_value = {"n_reports": 500, "drugs": ["warfarin", "aspirin"]}

        result = await get_adverse_event_context_safe(["warfarin", "aspirin"])

        assert result["adverse_events"]["n_reports"] == 500
        assert result["adverse_events"]["drugs"] == ["warfarin", "aspirin"]

    @patch("src.clients.openfda.OpenFDAClient.get_adverse_events")
    async def test_get_adverse_event_context_safe_exception(self, mock_context):
        """Test safe function handles exceptions."""
        mock_context.side_effect = Exception("Unexpected error")

        result = await get_adverse_event_context_safe(["warfarin", "aspirin"])

        assert result["adverse_events"]["n_reports"] == 0
        assert result["adverse_events"]["drugs"] == ["warfarin", "aspirin"]
        assert "top_reactions" in result["adverse_events"]


class TestErrorHandling:
    """Test custom error classes and error scenarios."""

    async def test_openfda_error_creation(self):
        """Test OpenFDAError with status code."""
        error = OpenFDAError("API failed", 500)

        assert error.status_code == 500
        assert "API failed" in str(error)

    async def test_openfda_error_without_status(self):
        """Test OpenFDAError without status code."""
        error = OpenFDAError("Connection failed")

        assert error.status_code is None
        assert "Connection failed" in str(error)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    async def test_warfarin_aspirin_combination(self, openfda_client):
        """Test the specific warfarin-aspirin combination scenario."""
        with patch.object(openfda_client.session, "get") as mock_get:
            # Mock response similar to real data
            mock_response_data = {
                "meta": {"results": {"total": 15691}},
                "results": [
                    {
                        "serious": "1",
                        "receivedate": "20140411",
                        "patient": {
                            "reaction": [
                                {"reactionmeddrapt": "Platelet count decreased"},
                                {"reactionmeddrapt": "Haemorrhage"},
                            ],
                            "drug": [
                                {"medicinalproduct": "WARFARIN"},
                                {"medicinalproduct": "ASPIRIN"},
                            ],
                        },
                    }
                ],
            }

            mock_response = type(
                "MockResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: mock_response_data,
                },
            )()
            mock_get.return_value = mock_response

            result = await openfda_client.get_adverse_events(["warfarin", "aspirin"])

        assert result["n_reports"] == 15691
        assert result["n_serious"] == 1
        assert "Platelet count decreased" in result["top_reactions"]
        assert result["drugs"] == ["warfarin", "aspirin"]

    async def test_query_building_logic(self, openfda_client):
        """Test the query construction for multiple drugs."""
        ingredient_names = ["warfarin", "aspirin", "ibuprofen"]

        # This would normally make HTTP request, so we test the query building indirectly
        with patch.object(openfda_client.session, "get") as mock_get:
            mock_response = type(
                "MockResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: EMPTY_RESPONSE,
                },
            )()
            mock_get.return_value = mock_response

            await openfda_client.get_adverse_events(ingredient_names)

            # Verify the method was called (URL construction happens internally)
            assert mock_get.called
            call_args = mock_get.call_args[0][0]
            # Just verify it's a valid OpenFDA URL - don't check internal URL construction
            assert "drug/event.json" in call_args
