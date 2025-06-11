from haystack.nodes import BaseComponent
from typing import List, Dict, Any, Optional, Tuple
import logging
import requests
import os
from urllib.parse import urlparse
from collections import defaultdict

logger = logging.getLogger(__name__)


class SearchAPIComponent(BaseComponent):
    """Component that calls SearchAPI.io for web search results"""
    outgoing_edges = 1

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv("SearchAPI_API_Key")
        if not self.api_key:
            logger.warning("SearchAPI_API_Key not found. WebSearch will use mock data.")

    def run(self, query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"SearchAPIComponent received query: {query}")
        
        if not self.api_key:
            logger.warning("No API key available, returning mock results")
            return self._get_mock_results(query), "output_1"
        
        try:
            response = requests.get(
                "https://www.searchapi.io/api/v1/search",
                params={
                    "q": query,
                    "engine": "google",
                    "num": 10,
                    "gl": "us",
                    "hl": "en"
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get("organic_results", [])
            filtered_results = [
                r for r in organic_results 
                if not r.get("is_ad", False) and not r.get("sponsored", False)
            ]
            
            logger.info(f"SearchAPI returned {len(filtered_results)} organic results")
            return {"search_results": filtered_results}, "output_1"
            
        except Exception as e:
            logger.error(f"SearchAPI error for query '{query}': {e}")
            return {"search_results": [], "error": str(e)}, "output_1"

    def _get_mock_results(self, query: str) -> Dict[str, Any]:
        """Return mock search results for development/testing"""
        mock_results = [
            {
                "title": f"Mock Result 1 for {query}",
                "link": "https://example.com/result1",
                "snippet": f"This is a mock search result snippet for the query: {query}. It contains relevant information about the topic.",
                "position": 1
            },
            {
                "title": f"Mock Result 2 for {query}",
                "link": "https://example.org/result2", 
                "snippet": f"Another mock result providing additional context about {query} with different information.",
                "position": 2
            },
            {
                "title": f"Mock Result 3 for {query}",
                "link": "https://test.com/result3",
                "snippet": f"Third mock result with more details about {query} from a different perspective.",
                "position": 3
            }
        ]
        return {"search_results": mock_results}

    def run_batch(self, queries: List[str]) -> Tuple[Dict[str, Any], str]:
        results = []
        for query in queries:
            result, _ = self.run(query=query)
            results.append(result)
        return {"results_batch": results}, "output_1"


class DeduplicateComponent(BaseComponent):
    """Component that removes duplicate results by hostname"""
    outgoing_edges = 1

    def __init__(self):
        super().__init__()

    def run(self, search_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
        logger.info(f"DeduplicateComponent received {len(search_results)} results")
        
        if not search_results or not isinstance(search_results, list):
            logger.warning("No search results provided or input is not a list")
            return {"deduplicated_results": []}, "output_1"
        
        try:
            hostname_map = {}
            
            for result in search_results:
                if not isinstance(result, dict) or "link" not in result:
                    continue
                    
                try:
                    hostname = urlparse(result["link"]).netloc.lower()
                    if hostname.startswith("www."):
                        hostname = hostname[4:]
                    
                    if hostname not in hostname_map:
                        hostname_map[hostname] = result
                        
                except Exception as e:
                    logger.warning(f"Error parsing URL {result.get('link', '')}: {e}")
                    continue
            
            deduplicated_results = list(hostname_map.values())
            logger.info(f"Deduplicated to {len(deduplicated_results)} unique domains")
            
            return {"deduplicated_results": deduplicated_results}, "output_1"
            
        except Exception as e:
            logger.error(f"Error in DeduplicateComponent: {e}")
            return {"deduplicated_results": [], "error": str(e)}, "output_1"

    def run_batch(self, search_results_batch: List[List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], str]:
        results = []
        for search_results_list in search_results_batch:
            result, _ = self.run(search_results=search_results_list)
            results.append(result)
        return {"deduplicated_results_batch": results}, "output_1"


class SnippetFetcherComponent(BaseComponent):
    """Component that enriches results with additional snippet information"""
    outgoing_edges = 1

    def __init__(self):
        super().__init__()

    def run(self, deduplicated_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
        logger.info(f"SnippetFetcherComponent received {len(deduplicated_results)} results")
        
        if not deduplicated_results or not isinstance(deduplicated_results, list):
            logger.warning("No deduplicated results provided or input is not a list")
            return {"enriched_results": []}, "output_1"
        
        try:
            enriched_results = []
            
            for result in deduplicated_results:
                if not isinstance(result, dict):
                    continue
                
                enriched_result = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", result.get("description", "")),
                    "position": result.get("position", 0),
                    "domain": self._extract_domain(result.get("link", "")),
                    "relevance_score": 0.0  # Will be set by SimilarityRankerComponent
                }
                
                if not enriched_result["snippet"] and enriched_result["title"]:
                    enriched_result["snippet"] = enriched_result["title"]
                
                enriched_results.append(enriched_result)
            
            logger.info(f"Enriched {len(enriched_results)} results")
            return {"enriched_results": enriched_results}, "output_1"
            
        except Exception as e:
            logger.error(f"Error in SnippetFetcherComponent: {e}")
            return {"enriched_results": [], "error": str(e)}, "output_1"

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain name from URL"""
        try:
            hostname = urlparse(url).netloc.lower()
            if hostname.startswith("www."):
                hostname = hostname[4:]
            return hostname
        except:
            return ""

    def run_batch(self, deduplicated_results_batch: List[List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], str]:
        results = []
        for deduplicated_results_list in deduplicated_results_batch:
            result, _ = self.run(deduplicated_results=deduplicated_results_list)
            results.append(result)
        return {"enriched_results_batch": results}, "output_1"


class SimilarityRankerComponent(BaseComponent):
    """Component that ranks results by similarity to the original query"""
    outgoing_edges = 1

    def __init__(self, max_results: int = 6):
        super().__init__()
        self.max_results = max_results

    def run(self, enriched_results: List[Dict[str, Any]], query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"SimilarityRankerComponent received {len(enriched_results)} results for query: {query}")
        
        if not enriched_results or not isinstance(enriched_results, list):
            logger.warning("No enriched results provided or input is not a list")
            return {"ranked_results": []}, "output_1"
        
        try:
            query_words = set(query.lower().split())
            
            for result in enriched_results:
                if not isinstance(result, dict):
                    continue
                
                title_words = set(result.get("title", "").lower().split())
                snippet_words = set(result.get("snippet", "").lower().split())
                
                title_overlap = len(query_words.intersection(title_words))
                snippet_overlap = len(query_words.intersection(snippet_words))
                
                relevance_score = (title_overlap * 2.0) + (snippet_overlap * 1.0)
                
                position_boost = max(0, 10 - result.get("position", 10)) * 0.1
                
                result["relevance_score"] = relevance_score + position_boost
            
            ranked_results = sorted(
                [r for r in enriched_results if isinstance(r, dict)],
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )[:self.max_results]
            
            logger.info(f"Ranked and selected top {len(ranked_results)} results")
            return {"ranked_results": ranked_results}, "output_1"
            
        except Exception as e:
            logger.error(f"Error in SimilarityRankerComponent: {e}")
            return {"ranked_results": [], "error": str(e)}, "output_1"

    def run_batch(self, enriched_results_batch: List[List[Dict[str, Any]]], queries: List[str]) -> Tuple[Dict[str, Any], str]:
        results = []
        for enriched_results_list, query in zip(enriched_results_batch, queries):
            result, _ = self.run(enriched_results=enriched_results_list, query=query)
            results.append(result)
        return {"ranked_results_batch": results}, "output_1"


class LLMSummarizerComponent(BaseComponent):
    """Component that summarizes ranked results using T5 model"""
    outgoing_edges = 1

    def __init__(self):
        super().__init__()
        self.summarizer = None
        self._initialize_summarizer()

    def _initialize_summarizer(self):
        """Initialize T5 summarizer for Switzerland hosting compliance"""
        try:
            from haystack.nodes import TransformersSummarizer
            
            use_gpu = os.getenv("USE_GPU", "false").lower() == "true"
            
            self.summarizer = TransformersSummarizer(
                model_name_or_path="t5-small",
                use_gpu=use_gpu,
                max_length=400,
                min_length=100
            )
            logger.info(f"T5 summarizer initialized successfully (GPU: {use_gpu})")
            
        except ImportError:
            logger.warning("TransformersSummarizer not available, falling back to simple concatenation")
            self.summarizer = None
        except Exception as e:
            logger.error(f"Error initializing T5 summarizer: {e}")
            self.summarizer = None

    def run(self, content_enriched_results: List[Dict[str, Any]], query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"LLMSummarizerComponent received {len(content_enriched_results)} results for query: {query}")
        
        if not content_enriched_results or not isinstance(content_enriched_results, list):
            logger.warning("No content enriched results provided")
            return {"summary": "No results found.", "sources": []}, "output_1"
        
        try:
            sources = [
                result.get("link", "") 
                for result in content_enriched_results[:3] 
                if result.get("link")
            ]
            
            if self.summarizer:
                summary = self._generate_t5_summary(content_enriched_results, query)
            else:
                summary = self._generate_simple_summary(content_enriched_results, query)
            
            result_data = {
                "summary": summary,
                "sources": sources
            }
            logger.info(f"🔍 DEBUG: LLMSummarizerComponent returning: {result_data}")
            return result_data, "output_1"
            
        except Exception as e:
            logger.error(f"Error in LLMSummarizerComponent: {e}")
            return {
                "summary": "Error generating summary.",
                "sources": []
            }, "output_1"

    def _generate_t5_summary(self, content_enriched_results: List[Dict[str, Any]], query: str) -> str:
        """Generate summary using T5 model"""
        try:
            if not self.summarizer:
                logger.warning("T5 summarizer not available, falling back to simple summary")
                return self._generate_simple_summary(content_enriched_results, query)
            
            combined_text = ""
            
            for result in content_enriched_results[:3]:
                full_content = result.get("full_content", "")
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                
                content = full_content if full_content else snippet
                combined_text += f"{title}: {content} "
            
            if len(combined_text) > 4000:
                combined_text = combined_text[:4000]
            
            if not combined_text.strip():
                return "No content available for summarization."
            
            from haystack.schema import Document
            summary_result = self.summarizer.predict(
                documents=[Document(content=combined_text)]
            )
            
            if summary_result and len(summary_result) > 0:
                return summary_result[0].answer
            else:
                return self._generate_simple_summary(content_enriched_results, query)
                
        except Exception as e:
            logger.error(f"T5 summarization error: {e}")
            return self._generate_simple_summary(content_enriched_results, query)

    def _generate_simple_summary(self, content_enriched_results: List[Dict[str, Any]], query: str) -> str:
        """Generate simple summary by concatenating top content or snippets"""
        try:
            logger.info(f"🔍 DEBUG: _generate_simple_summary received {len(content_enriched_results)} content_enriched_results")
            for i, result in enumerate(content_enriched_results[:3]):
                logger.info(f"🔍 DEBUG: Result {i}: title='{result.get('title', '')}', snippet='{result.get('snippet', '')}', has_full_content={bool(result.get('full_content'))}")
            
            content_pieces = []
            for result in content_enriched_results[:3]:
                full_content = result.get("full_content", "")
                snippet = result.get("snippet", "")
                content = full_content if full_content else snippet
                if content:
                    content_pieces.append(content)
            
            logger.info(f"🔍 DEBUG: Extracted {len(content_pieces)} content pieces")
            
            if not content_pieces:
                logger.warning("🔍 DEBUG: No content found, returning fallback message")
                return "No relevant information found."
            
            summary = f"Based on current web search results for '{query}': "
            summary += " ".join(content_pieces)
            
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            logger.info(f"🔍 DEBUG: Generated summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating simple summary: {e}")
            return "Unable to generate summary from search results."

    def run_batch(self, ranked_results_batch: List[List[Dict[str, Any]]], queries: List[str]) -> Tuple[Dict[str, Any], str]:
        results = []
        for ranked_results_list, query in zip(ranked_results_batch, queries):
            result, _ = self.run(ranked_results=ranked_results_list, query=query)
            results.append(result)
        return {"summary_batch": results}, "output_1"


class ContentFetcherComponent(BaseComponent):
    """Component that fetches full webpage content from top ranked results"""
    outgoing_edges = 1

    def __init__(self, max_content_length: int = 3000, timeout: int = 10):
        super().__init__()
        self.max_content_length = max_content_length
        self.timeout = timeout

    def run(self, ranked_results: List[Dict[str, Any]], query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"ContentFetcherComponent received {len(ranked_results)} results for query: {query}")
        
        if not ranked_results or not isinstance(ranked_results, list):
            logger.warning("No ranked results provided")
            return {"content_enriched_results": []}, "output_1"
        
        try:
            content_enriched_results = []
            
            for i, result in enumerate(ranked_results[:3]):
                if not isinstance(result, dict) or not result.get("link"):
                    content_enriched_results.append(result)
                    continue
                
                enriched_result = result.copy()
                
                try:
                    full_content = self._fetch_webpage_content(result["link"])
                    if full_content:
                        enriched_result["full_content"] = full_content
                        logger.info(f"Successfully fetched content from {result['link']} ({len(full_content)} chars)")
                    else:
                        enriched_result["full_content"] = result.get("snippet", "")
                        logger.warning(f"No content extracted from {result['link']}, using snippet fallback")
                        
                except Exception as e:
                    logger.warning(f"Error fetching content from {result['link']}: {e}")
                    enriched_result["full_content"] = result.get("snippet", "")
                
                content_enriched_results.append(enriched_result)
            
            content_enriched_results.extend(ranked_results[3:])
            
            logger.info(f"Content enrichment completed for {len(content_enriched_results)} results")
            return {"content_enriched_results": content_enriched_results}, "output_1"
            
        except Exception as e:
            logger.error(f"Error in ContentFetcherComponent: {e}")
            return {"content_enriched_results": ranked_results, "error": str(e)}, "output_1"

    def _fetch_webpage_content(self, url: str) -> str:
        """Fetch and extract main content from webpage using BeautifulSoup"""
        try:
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            main_content = None
            for selector in ['main', 'article', '.content', '#content', '.post', '.entry']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body') or soup
            
            text_content = main_content.get_text(separator=' ', strip=True)
            
            text_content = ' '.join(text_content.split())
            
            if len(text_content) > self.max_content_length:
                text_content = text_content[:self.max_content_length]
            
            return text_content
            
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {e}")
            return ""

    def run_batch(self, ranked_results_batch: List[List[Dict[str, Any]]], queries: List[str]) -> Tuple[Dict[str, Any], str]:
        results = []
        for ranked_results_list, query in zip(ranked_results_batch, queries):
            result, _ = self.run(ranked_results=ranked_results_list, query=query)
            results.append(result)
        return {"content_enriched_results_batch": results}, "output_1"
