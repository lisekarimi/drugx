# tests/conftest.py
from unittest.mock import AsyncMock

import httpx
import pytest

# Enable asyncio mode for all tests
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_http_session():
    """Mock httpx.AsyncClient for all API clients."""
    session = AsyncMock(spec=httpx.AsyncClient)
    return session
