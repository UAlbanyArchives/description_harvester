"""Global test configuration and fixtures."""
import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture(autouse=True)
def mock_requests_get(monkeypatch):
    """
    Automatically mock requests.get for all tests to prevent actual HTTP calls.
    
    This is needed because the manifests plugin attempts to fetch IIIF manifests
    and other web resources during plugin initialization, which would fail in CI
    environments without network access or when URLs don't exist.
    """
    mock_response = Mock()
    mock_response.status_code = 404  # Return 404 so plugin logic falls back gracefully
    mock_response.text = ""
    mock_response.json.return_value = {}
    
    def mock_get(*args, **kwargs):
        return mock_response
    
    # Mock requests.get if requests module is available
    try:
        import requests
        monkeypatch.setattr(requests, "get", mock_get)
    except ImportError:
        pass  # requests not installed, skip mocking
