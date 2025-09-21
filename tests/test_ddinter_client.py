# tests/test_ddinter_client.py
from unittest.mock import AsyncMock, patch

import pytest

from src.clients.ddinter import (
    DDInterClient,
    InteractionNotFoundError,
)
from src.clients.ddinter import (
    check_drug_interactions_consolidated as check_drug_interactions,
)


class TestDDInterClient:
    """Tests for DDInter module - both high-level wrapper function and direct client methods."""

    # =====================================================================
    # HIGH-LEVEL WRAPPER FUNCTION TESTS
    # These test check_drug_interactions_consolidated() by mocking the entire DDInterClient class
    # =====================================================================

    @pytest.mark.asyncio
    async def test_check_drug_interactions_success(self):
        """Test successful drug interaction checking."""
        # Define the mock response
        mock_interaction = {
            "severity": "Moderate",
            "categories": ["B"],
            "ddinter_ids": ["DDInter14", "DDInter1951"],
            "drugs": ["Acetaminophen", "Warfarin"],
            "category_explanations": {"B": "Blood and blood-forming organs"},
        }

        # Mock the DDInterClient class and its context manager behavior
        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            # Create a mock instance
            mock_instance = AsyncMock()

            # Set up the async context manager to return our mock instance
            MockClient.return_value.__aenter__.return_value = mock_instance

            # Mock the get_interaction_summary method to return our test data
            mock_instance.get_interaction_summary.return_value = mock_interaction

            # Call the function we're testing
            results = await check_drug_interactions(["acetaminophen", "warfarin"])

            # Extract the interactions list from the returned dictionary
            interactions = results["Drug-Drug interactions"]

            # Verify the results
            assert len(interactions) == 1
            assert interactions[0]["severity"] == "Moderate"
            assert interactions[0]["categories"] == ["B"]
            assert interactions[0]["ddinter_ids"] == ["DDInter14", "DDInter1951"]
            assert interactions[0]["drugs"] == ["Acetaminophen", "Warfarin"]
            assert (
                interactions[0]["category_explanations"]["B"]
                == "Blood and blood-forming organs"
            )

            # Verify the method was called once with correct arguments
            mock_instance.get_interaction_summary.assert_called_once_with(
                "acetaminophen", "warfarin"
            )

    @pytest.mark.asyncio
    async def test_check_drug_interactions_no_interaction(self):
        """Test when no interaction is found."""
        mock_no_interaction = {
            "drugs": ["aspirin", "acetaminophen"],
            "severity": None,
            "note": "The DDInter database doesn't list any known, clinically significant pharmacokinetic or pharmacodynamic interaction between these drugs.",
        }

        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            mock_instance.get_interaction_summary.return_value = mock_no_interaction

            results = await check_drug_interactions(["aspirin", "acetaminophen"])
            interactions = results["Drug-Drug interactions"]

            assert len(interactions) == 1
            assert interactions[0]["severity"] is None
            assert "note" in interactions[0]
            assert "DDInter database doesn't list" in interactions[0]["note"]

    @pytest.mark.asyncio
    async def test_check_drug_interactions_multiple_pairs(self):
        """Test checking interactions for multiple drugs generates all pairs."""
        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance

            # Mock responses for 3 pairs: aspirin-warfarin, aspirin-acetaminophen, warfarin-acetaminophen
            mock_instance.get_interaction_summary.side_effect = [
                {"drugs": ["aspirin", "warfarin"], "severity": "Major"},
                {"drugs": ["aspirin", "acetaminophen"], "severity": None},
                {"drugs": ["warfarin", "acetaminophen"], "severity": "Moderate"},
            ]

            results = await check_drug_interactions(
                ["aspirin", "warfarin", "acetaminophen"]
            )

            # Extract the interactions list from the returned dictionary
            interactions = results["Drug-Drug interactions"]

            assert len(interactions) == 3  # 3 pairs for 3 drugs
            assert mock_instance.get_interaction_summary.call_count == 3

            # Verify all expected pairs were checked
            call_args = [
                call[0] for call in mock_instance.get_interaction_summary.call_args_list
            ]
            expected_calls = [
                ("aspirin", "warfarin"),
                ("aspirin", "acetaminophen"),
                ("warfarin", "acetaminophen"),
            ]
            assert call_args == expected_calls

    @pytest.mark.asyncio
    async def test_check_drug_interactions_multiple_categories(self):
        """Test interaction with multiple categories."""
        mock_interaction = {
            "severity": "Major",
            "categories": ["A", "B", "D"],
            "ddinter_ids": ["DDInter1", "DDInter2"],
            "drugs": ["DrugA", "DrugB"],
            "category_explanations": {
                "A": "Alimentary tract and metabolism",
                "B": "Blood and blood-forming organs",
                "D": "Dermatologicals",
            },
        }

        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            mock_instance.get_interaction_summary.return_value = mock_interaction

            results = await check_drug_interactions(["druga", "drugb"])
            interactions = results["Drug-Drug interactions"]

            assert len(interactions) == 1
            assert interactions[0]["categories"] == ["A", "B", "D"]
            assert len(interactions[0]["category_explanations"]) == 3

    @pytest.mark.asyncio
    async def test_check_drug_interactions_case_preservation(self):
        """Test that drug names are passed as-is (case handling in database)."""
        mock_interaction = {"drugs": ["ASPIRIN", "warfarin"], "severity": None}

        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            mock_instance.get_interaction_summary.return_value = mock_interaction

            await check_drug_interactions(["ASPIRIN", "warfarin"])

            # Verify original case is preserved
            mock_instance.get_interaction_summary.assert_called_once_with(
                "ASPIRIN", "warfarin"
            )

    @pytest.mark.asyncio
    async def test_check_drug_interactions_two_drugs_minimum(self):
        """Test that function works with exactly 2 drugs."""
        mock_interaction = {
            "drugs": ["aspirin", "warfarin"],
            "severity": "Major",
            "categories": ["B"],
        }

        with patch("src.clients.ddinter.DDInterClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            mock_instance.get_interaction_summary.return_value = mock_interaction

            results = await check_drug_interactions(["aspirin", "warfarin"])
            interactions = results["Drug-Drug interactions"]

            assert len(interactions) == 1  # Only 1 pair for 2 drugs
            assert interactions[0]["severity"] == "Major"
            mock_instance.get_interaction_summary.assert_called_once()

    # =====================================================================
    # DIRECT CLIENT METHODS TESTS
    # These test DDInterClient class methods directly by mocking internal methods
    # =====================================================================

    async def test_client_initialization(self):
        """Test DDInterClient initialization."""
        client = DDInterClient()
        assert client.pool is None

    @patch("src.clients.ddinter.ATC_CATEGORIES", {"B": "Blood", "C": "Cardiovascular"})
    async def test_get_interaction_summary_success(self):
        """Test get_interaction_summary with successful interaction."""
        client = DDInterClient()

        with patch.object(client, "check_interaction") as mock_check:
            mock_check.return_value = {
                "severity": "Major",
                "drugs": ["aspirin", "warfarin"],
                "_categories": ["B", "C"],
            }

            result = await client.get_interaction_summary("aspirin", "warfarin")

            assert result["severity"] == "Major"
            assert result["category_explanations"] == {
                "B": "Blood",
                "C": "Cardiovascular",
            }
            assert "_categories" not in result  # Should be removed

    async def test_get_interaction_summary_not_found(self):
        """Test get_interaction_summary when interaction not found."""
        client = DDInterClient()

        with patch.object(client, "check_interaction") as mock_check:
            mock_check.side_effect = InteractionNotFoundError("drug1", "drug2")

            result = await client.get_interaction_summary("drug1", "drug2")

            assert result["drugs"] == ["drug1", "drug2"]
            assert "note" in result
            assert "DDInter reports no known" in result["note"]

    async def test_context_manager(self):
        """Test DDInterClient as context manager."""
        with patch.object(DDInterClient, "_ensure_database_ready"):
            client = DDInterClient()
            client.pool = AsyncMock()

            async with client as c:
                assert c == client

            client.pool.close.assert_called_once()

    # =====================================================================
    # ERROR CLASSES TESTS
    # These test custom exception classes
    # =====================================================================

    async def test_interaction_not_found_error(self):
        """Test InteractionNotFoundError exception class."""
        error = InteractionNotFoundError("drug1", "drug2")

        assert error.ingredient_a == "drug1"
        assert error.ingredient_b == "drug2"
        assert "No interaction found between 'drug1' and 'drug2'" in str(error)
