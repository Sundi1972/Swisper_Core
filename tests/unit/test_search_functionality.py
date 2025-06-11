import pytest
from unittest.mock import patch, MagicMock
from tool_adapter.mock_google import google_shopping_search

class TestSearchFunctionality:
    @patch.dict('os.environ', {'SEARCHAPI_API_KEY': 'test-key'})
    @patch('tool_adapter.mock_google.requests.get')
    def test_google_shopping_search_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "shopping_results": [
                {"title": "RTX 4090", "price": "$1599.99", "link": "test.com"}
            ]
        }
        mock_get.return_value = mock_response
        
        results = google_shopping_search("RTX 4090")
        assert len(results) > 0
        assert "RTX 4090" in results[0].get("title", results[0].get("name", ""))

    @patch('tool_adapter.mock_google.requests.get')
    def test_google_shopping_search_api_failure(self, mock_get):
        mock_get.side_effect = Exception("API Error")
        
        results = google_shopping_search("GPU")
        assert len(results) > 0
        assert any("GPU" in str(result) for result in results)

    @patch('tool_adapter.mock_google.requests.get')
    def test_mock_google_shopping_fallback(self, mock_get):
        mock_get.side_effect = Exception("API Error")
        
        results = google_shopping_search("test_query_fallback")
        
        assert len(results) > 0
        assert isinstance(results, list)

    @patch('tool_adapter.mock_google.requests.get')
    def test_search_with_different_queries(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "shopping_results": [
                {"title": "Graphics Card", "price": "$999.99", "link": "test.com"}
            ]
        }
        mock_get.return_value = mock_response
        
        test_queries = ["graphics card", "GPU", "RTX", "gaming laptop"]
        
        for query in test_queries:
            results = google_shopping_search(query)
            assert len(results) > 0

    @patch('tool_adapter.mock_google.requests.get')
    def test_search_api_timeout(self, mock_get):
        mock_get.side_effect = TimeoutError("Request timeout")
        
        results = google_shopping_search("GPU")
        assert len(results) > 0

    @patch('tool_adapter.mock_google.requests.get')
    def test_search_invalid_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with patch('tool_adapter.mock_google.logger') as mock_logger:
            results = google_shopping_search("GPU")
            assert len(results) > 0  # Should return mock data on invalid response
            mock_logger.error.assert_called()

    def test_search_empty_query(self):
        results = google_shopping_search("")
        
        assert isinstance(results, list)

    def test_search_gpu_specific_query(self):
        results = google_shopping_search("RTX 4090 graphics card")
        
        assert len(results) > 0
        assert any("RTX" in str(result) or "GPU" in str(result) or "graphics" in str(result).lower() for result in results)

    @patch.dict('os.environ', {'SEARCHAPI_API_KEY': 'test-key'})
    @patch('tool_adapter.mock_google.requests.get')
    def test_search_result_structure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "shopping_results": [
                {
                    "title": "RTX 4090 Graphics Card",
                    "price": "$1599.99",
                    "link": "https://example.com/gpu",
                    "source": "TechStore"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        results = google_shopping_search("RTX 4090")
        assert len(results) > 0
        
        result = results[0]
        assert "title" in result or "name" in result
        assert "price" in result
        assert "link" in result

    @patch('tool_adapter.mock_google.requests.get')
    def test_search_fallback_data_quality(self, mock_get):
        mock_get.side_effect = Exception("API Error")
        
        results = google_shopping_search("nonexistent_query_that_will_use_fallback")
        
        assert len(results) > 0
        for result in results:
            assert isinstance(result, dict)
            assert "title" in result or "name" in result
