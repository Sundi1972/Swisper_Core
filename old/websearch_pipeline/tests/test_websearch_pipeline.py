import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websearch_pipeline.websearch_pipeline import create_websearch_pipeline


class TestWebSearchPipeline(unittest.TestCase):
    
    def test_create_websearch_pipeline(self):
        """Test that the pipeline is created successfully"""
        pipeline = create_websearch_pipeline()
        
        self.assertIsNotNone(pipeline)
        
        expected_nodes = ["SearchAPI", "Deduplicate", "SnippetFetcher", "SimilarityRanker", "LLMSummarizer"]
        
        for node_name in expected_nodes:
            self.assertIn(node_name, pipeline.graph.nodes)
    
    @patch.dict(os.environ, {'SearchAPI_API_Key': 'test_key'})
    def test_pipeline_with_api_key(self):
        """Test pipeline creation with API key"""
        pipeline = create_websearch_pipeline()
        self.assertIsNotNone(pipeline)
    
    def test_pipeline_without_api_key(self):
        """Test pipeline creation without API key (should use mock)"""
        if 'SearchAPI_API_Key' in os.environ:
            del os.environ['SearchAPI_API_Key']
        
        pipeline = create_websearch_pipeline()
        self.assertIsNotNone(pipeline)
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_pipeline_end_to_end_mock(self, mock_get):
        """Test the complete pipeline with mocked API response"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "organic_results": [
                {
                    "title": "German Government Ministers 2025",
                    "link": "https://example.com/ministers",
                    "snippet": "The new German government ministers for 2025 include...",
                    "position": 1
                },
                {
                    "title": "Latest German Cabinet Changes",
                    "link": "https://news.example.org/cabinet",
                    "snippet": "Recent changes in the German cabinet show...",
                    "position": 2
                }
            ]
        }
        mock_get.return_value = mock_response
        
        pipeline = create_websearch_pipeline()
        test_query = "Who are the new German ministers 2025"
        
        result = pipeline.run(query=test_query)
        
        self.assertIn("summary", result)
        self.assertIn("sources", result)
        self.assertIsInstance(result["summary"], str)
        self.assertIsInstance(result["sources"], list)
        self.assertGreater(len(result["summary"]), 0)
    
    def test_pipeline_with_no_api_key_uses_mock(self):
        """Test that pipeline works with mock data when no API key is available"""
        if 'SearchAPI_API_Key' in os.environ:
            del os.environ['SearchAPI_API_Key']
        
        pipeline = create_websearch_pipeline()
        test_query = "Who are the new German ministers 2025"
        
        result = pipeline.run(query=test_query)
        
        self.assertIn("summary", result)
        self.assertIsInstance(result["summary"], str)
        self.assertGreater(len(result["summary"]), 0)


if __name__ == '__main__':
    unittest.main()
