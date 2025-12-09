"""Global test configuration and fixtures."""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import yaml


@pytest.fixture(autouse=True)
def mock_config_file(monkeypatch):
    """
    Mock the config file loading to use the repository's test config
    instead of the user's home directory config.
    
    This prevents personal config settings from affecting test results.
    """
    # Path to the test config in the repository
    test_config_path = Path(__file__).parent.parent / ".description_harvester" / "config.yml"
    
    # Read the test config
    if test_config_path.exists():
        with open(test_config_path, 'r', encoding='utf-8') as f:
            test_config_data = f.read()
    else:
        # Fallback minimal config if test config doesn't exist
        test_config_data = """
solr_url: http://127.0.0.1:8983/solr
solr_core: blacklight-core
last_query: 0
cache_expiration: 3600
online_content_label: "Online access"
metadata: []
"""
    
    # Mock Path.home() to return a temp directory
    original_home = Path.home
    
    def mock_home():
        # Return the repository's .description_harvester directory as "home"
        return Path(__file__).parent.parent
    
    monkeypatch.setattr(Path, "home", mock_home)


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
