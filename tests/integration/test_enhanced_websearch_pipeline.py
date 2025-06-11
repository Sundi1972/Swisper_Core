import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websearch_pipeline.websearch_pipeline import create_websearch_pipeline


class TestEnhancedWebsearchPipeline(unittest.TestCase):
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_enhanced_pipeline_end_to_end(self, mock_get):
        """Test the complete enhanced pipeline with content fetching"""
        
        search_response = MagicMock()
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {
            "organic_results": [
                {"title": "German Finance Minister News", "link": "https://news.com/finance", "snippet": "Latest news about German finance minister"},
                {"title": "Government Officials", "link": "https://gov.de/officials", "snippet": "Current government officials list"},
                {"title": "Political Updates", "link": "https://politics.com/updates", "snippet": "Recent political developments"}
            ]
        }
        
        content_response = MagicMock()
        content_response.raise_for_status.return_value = None
        content_response.content = b'<html><body><main>Detailed article content about German finance minister with comprehensive information</main></body></html>'
        
        mock_get.side_effect = [search_response] + [content_response] * 3
        
        pipeline = create_websearch_pipeline()
        result = pipeline.run(query="current German finance minister")
        
        self.assertIn("summary", result)
        self.assertIn("sources", result)
        self.assertIsInstance(result["summary"], str)
        self.assertIsInstance(result["sources"], list)
        
        self.assertEqual(mock_get.call_count, 4)
        
        sources = result["sources"]
        self.assertGreater(len(sources), 0)
        self.assertLessEqual(len(sources), 3)
        
        self.assertGreater(len(result["summary"]), 50)
    
    def test_enhanced_pipeline_performance(self):
        """Test that enhanced pipeline completes within reasonable time"""
        import time
        
        pipeline = create_websearch_pipeline()
        
        start_time = time.time()
        result = pipeline.run(query="test query")
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 30.0)
        
        self.assertIn("summary", result)
        self.assertIn("sources", result)


if __name__ == '__main__':
    unittest.main()
