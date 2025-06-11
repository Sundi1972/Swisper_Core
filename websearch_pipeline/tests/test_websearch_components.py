import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websearch_pipeline.websearch_components import (
    SearchAPIComponent,
    DeduplicateComponent,
    SnippetFetcherComponent,
    SimilarityRankerComponent,
    ContentFetcherComponent,
    LLMSummarizerComponent
)


class TestSearchAPIComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = SearchAPIComponent(api_key="test_key")
    
    def test_init_with_api_key(self):
        component = SearchAPIComponent(api_key="test_key")
        self.assertEqual(component.api_key, "test_key")
    
    def test_init_without_api_key_uses_mock(self):
        component = SearchAPIComponent(api_key=None)
        self.assertIsNotNone(component)
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_run_with_api_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "organic_results": [
                {"title": "Test Result", "link": "https://test.com", "snippet": "Test snippet", "is_ad": False},
                {"title": "Ad Result", "link": "https://ad.com", "snippet": "Ad snippet", "is_ad": True}
            ]
        }
        mock_get.return_value = mock_response
        
        result, edge = self.component.run("test query")
        
        self.assertEqual(edge, "output_1")
        self.assertIn("search_results", result)
        self.assertEqual(len(result["search_results"]), 1)  # Ad should be filtered out
        self.assertEqual(result["search_results"][0]["title"], "Test Result")
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_run_with_api_error(self, mock_get):
        mock_get.side_effect = Exception("API Error")
        
        result, edge = self.component.run("test query")
        
        self.assertEqual(edge, "output_1")
        self.assertIn("search_results", result)
        self.assertEqual(len(result["search_results"]), 0)
        self.assertIn("error", result)
    
    def test_run_without_api_key_returns_mock(self):
        component = SearchAPIComponent(api_key=None)
        result, edge = component.run("test query")
        
        self.assertEqual(edge, "output_1")
        self.assertIn("search_results", result)
        self.assertGreater(len(result["search_results"]), 0)
        self.assertIn("test query", result["search_results"][0]["title"].lower())


class TestDeduplicateComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = DeduplicateComponent()
    
    def test_run_with_duplicates(self):
        search_results = [
            {"title": "Result 1", "link": "https://example.com/page1"},
            {"title": "Result 2", "link": "https://www.example.com/page2"},  # Same domain
            {"title": "Result 3", "link": "https://different.com/page1"},
            {"title": "Result 4", "link": "https://example.com/page3"}  # Same domain as first
        ]
        
        result, edge = self.component.run(search_results)
        
        self.assertEqual(edge, "output_1")
        self.assertIn("deduplicated_results", result)
        self.assertEqual(len(result["deduplicated_results"]), 2)
    
    def test_run_with_empty_list(self):
        result, edge = self.component.run([])
        
        self.assertEqual(edge, "output_1")
        self.assertIn("deduplicated_results", result)
        self.assertEqual(len(result["deduplicated_results"]), 0)
    
    def test_run_with_invalid_input(self):
        result, edge = self.component.run([])
        
        self.assertEqual(edge, "output_1")
        self.assertIn("deduplicated_results", result)
        self.assertEqual(len(result["deduplicated_results"]), 0)


class TestSnippetFetcherComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = SnippetFetcherComponent()
    
    def test_run_enriches_results(self):
        deduplicated_results = [
            {"title": "Test Title", "link": "https://example.com", "snippet": "Test snippet"},
            {"title": "Another Title", "link": "https://test.org", "description": "Test description"}
        ]
        
        result, edge = self.component.run(deduplicated_results)
        
        self.assertEqual(edge, "output_1")
        self.assertIn("enriched_results", result)
        self.assertEqual(len(result["enriched_results"]), 2)
        
        enriched = result["enriched_results"][0]
        self.assertIn("domain", enriched)
        self.assertIn("relevance_score", enriched)
        self.assertEqual(enriched["domain"], "example.com")
    
    def test_run_handles_missing_snippet(self):
        deduplicated_results = [
            {"title": "Test Title", "link": "https://example.com"}  # No snippet
        ]
        
        result, edge = self.component.run(deduplicated_results)
        
        enriched = result["enriched_results"][0]
        self.assertEqual(enriched["snippet"], "Test Title")


class TestSimilarityRankerComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = SimilarityRankerComponent(max_results=3)
    
    def test_run_ranks_by_relevance(self):
        enriched_results = [
            {"title": "Unrelated Title", "snippet": "Nothing relevant", "position": 1, "relevance_score": 0.0},
            {"title": "German Ministers News", "snippet": "Latest German government ministers", "position": 2, "relevance_score": 0.0},
            {"title": "Random Article", "snippet": "Random content", "position": 3, "relevance_score": 0.0}
        ]
        query = "German ministers"
        
        result, edge = self.component.run(enriched_results, query)
        
        self.assertEqual(edge, "output_1")
        self.assertIn("ranked_results", result)
        
        ranked = result["ranked_results"]
        self.assertGreater(ranked[0]["relevance_score"], ranked[1]["relevance_score"])
        self.assertIn("German", ranked[0]["title"])
    
    def test_run_limits_results(self):
        enriched_results = [
            {"title": f"Result {i}", "snippet": f"Snippet {i}", "position": i, "relevance_score": 0.0}
            for i in range(10)
        ]
        query = "test"
        
        result, edge = self.component.run(enriched_results, query)
        
        self.assertLessEqual(len(result["ranked_results"]), 3)


class TestLLMSummarizerComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = LLMSummarizerComponent()
    
    def test_run_generates_summary(self):
        ranked_results = [
            {"title": "Test Result 1", "link": "https://example.com", "snippet": "First test snippet"},
            {"title": "Test Result 2", "link": "https://test.org", "snippet": "Second test snippet"}
        ]
        query = "test query"
        
        result, edge = self.component.run(ranked_results, query)
        
        self.assertEqual(edge, "output_1")
        self.assertIn("summary", result)
        self.assertIn("sources", result)
        self.assertIsInstance(result["summary"], str)
        self.assertIsInstance(result["sources"], list)
        self.assertGreater(len(result["summary"]), 0)
    
    def test_run_with_empty_results(self):
        result, edge = self.component.run([], "test query")
        
        self.assertEqual(edge, "output_1")
        self.assertIn("summary", result)
        self.assertEqual(result["summary"], "No results found.")
        self.assertEqual(result["sources"], [])
    
    def test_run_extracts_sources(self):
        ranked_results = [
            {"title": "Test Result 1", "link": "https://example.com", "snippet": "Test snippet"},
            {"title": "Test Result 2", "link": "https://test.org", "snippet": "Another snippet"},
            {"title": "Test Result 3", "link": "https://third.com", "snippet": "Third snippet"},
            {"title": "Test Result 4", "link": "https://fourth.com", "snippet": "Fourth snippet"}
        ]
        query = "test"
        
        result, edge = self.component.run(ranked_results, query)
        
        sources = result["sources"]
        self.assertLessEqual(len(sources), 3)
        self.assertIn("https://example.com", sources)


class TestContentFetcherComponent(unittest.TestCase):
    
    def setUp(self):
        self.component = ContentFetcherComponent(max_content_length=1000, timeout=5)
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_run_fetches_content_successfully(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'<html><body><main>Test webpage content</main></body></html>'
        mock_get.return_value = mock_response
        
        ranked_results = [
            {"title": "Test Result", "link": "https://example.com", "snippet": "Test snippet"},
            {"title": "Another Result", "link": "https://test.org", "snippet": "Another snippet"}
        ]
        
        result, edge = self.component.run(ranked_results, "test query")
        
        self.assertEqual(edge, "output_1")
        self.assertIn("content_enriched_results", result)
        enriched = result["content_enriched_results"][0]
        self.assertIn("full_content", enriched)
        self.assertIn("Test webpage content", enriched["full_content"])
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_run_handles_fetch_error_gracefully(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        
        ranked_results = [
            {"title": "Test Result", "link": "https://example.com", "snippet": "Test snippet"}
        ]
        
        result, edge = self.component.run(ranked_results, "test query")
        
        self.assertEqual(edge, "output_1")
        enriched = result["content_enriched_results"][0]
        self.assertEqual(enriched["full_content"], "Test snippet")
    
    def test_run_with_empty_results(self):
        result, edge = self.component.run([], "test query")
        
        self.assertEqual(edge, "output_1")
        self.assertEqual(result["content_enriched_results"], [])
    
    @patch('websearch_pipeline.websearch_components.requests.get')
    def test_run_processes_only_top_3_results(self, mock_get):
        ranked_results = [
            {"title": f"Result {i}", "link": f"https://example{i}.com", "snippet": f"Snippet {i}"}
            for i in range(5)
        ]
        
        mock_response = MagicMock()
        mock_response.content = b'<html><body>Content</body></html>'
        mock_get.return_value = mock_response
        
        result, edge = self.component.run(ranked_results, "test query")
        
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(len(result["content_enriched_results"]), 5)


if __name__ == '__main__':
    unittest.main()
