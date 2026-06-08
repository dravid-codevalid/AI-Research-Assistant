import pytest
from unittest.mock import patch, MagicMock
from adapters.agent.dspy_agent import web_search
from config import settings

@patch("adapters.agent.dspy_agent.TavilyClient")
def test_web_search_success(mock_tavily_class):
    # Setup mock
    mock_client = MagicMock()
    mock_tavily_class.return_value = mock_client
    mock_client.search.return_value = {
        "results": [
            {"title": "Test Title 1", "content": "Test Content 1"},
            {"title": "Test Title 2", "content": "Test Content 2"}
        ]
    }
    
    # Temporarily set API key
    original_key = settings.TAVILY_API_KEY
    settings.TAVILY_API_KEY = "test_key"
    
    try:
        result = web_search("test query")
        assert "[Test Title 1] Test Content 1" in result
        assert "[Test Title 2] Test Content 2" in result
        mock_client.search.assert_called_once_with(query="test query", search_depth="basic", max_results=3)
    finally:
        settings.TAVILY_API_KEY = original_key

def test_web_search_missing_key():
    original_key = settings.TAVILY_API_KEY
    settings.TAVILY_API_KEY = None
    
    try:
        result = web_search("test query")
        assert result == "Tavily API key is not configured. Web search is unavailable."
    finally:
        settings.TAVILY_API_KEY = original_key

@patch("adapters.agent.dspy_agent.TavilyClient")
def test_web_search_exception(mock_tavily_class):
    mock_tavily_class.side_effect = Exception("API Error")
    
    original_key = settings.TAVILY_API_KEY
    settings.TAVILY_API_KEY = "test_key"
    
    try:
        result = web_search("test query")
        assert result == "Web search error: API Error"
    finally:
        settings.TAVILY_API_KEY = original_key
