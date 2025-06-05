from haystack.pipelines import Pipeline
import logging
import os

try:
    from .websearch_components import (
        SearchAPIComponent,
        DeduplicateComponent,
        SnippetFetcherComponent,
        SimilarityRankerComponent,
        LLMSummarizerComponent
    )
except ImportError:
    from websearch_pipeline.websearch_components import (
        SearchAPIComponent,
        DeduplicateComponent,
        SnippetFetcherComponent,
        SimilarityRankerComponent,
        LLMSummarizerComponent
    )

logger = logging.getLogger(__name__)


def create_websearch_pipeline() -> Pipeline:
    """Create and configure the WebSearch pipeline
    
    Pipeline flow:
    Query -> SearchAPI -> Deduplicate -> SnippetFetcher -> SimilarityRanker -> LLMSummarizer
    
    Returns:
        Pipeline: Configured Haystack pipeline for web search
    """
    pipeline = Pipeline()
    
    search_node = SearchAPIComponent(api_key=os.getenv("SearchAPI_API_Key"))
    dedupe_node = DeduplicateComponent()
    snippet_node = SnippetFetcherComponent()
    rank_node = SimilarityRankerComponent(max_results=6)
    summarize_node = LLMSummarizerComponent()
    
    pipeline.add_node(component=search_node, name="SearchAPI", inputs=["Query"])
    
    pipeline.add_node(component=dedupe_node, name="Deduplicate", inputs=["SearchAPI"])
    
    pipeline.add_node(component=snippet_node, name="SnippetFetcher", inputs=["Deduplicate"])
    
    pipeline.add_node(component=rank_node, name="SimilarityRanker", inputs=["SnippetFetcher"])
    
    pipeline.add_node(component=summarize_node, name="LLMSummarizer", inputs=["SimilarityRanker"])
    
    logger.info("WebSearch Pipeline created successfully")
    return pipeline


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    logger.info("Testing WebSearch pipeline creation and execution...")
    
    try:
        websearch_pipeline = create_websearch_pipeline()
        test_query = "Who are the new German ministers 2025"
        logger.info(f"Running pipeline with query: '{test_query}'")
        
        pipeline_result = websearch_pipeline.run(query=test_query)
        
        logger.info("Pipeline execution finished")
        
        summarizer_output = pipeline_result.get("LLMSummarizer")
        if summarizer_output and isinstance(summarizer_output, tuple):
            summary_data = summarizer_output[0]
            summary = summary_data.get("summary", "No summary generated")
            sources = summary_data.get("sources", [])
            
            logger.info(f"Summary: {summary}")
            logger.info(f"Sources: {sources}")
        else:
            logger.warning(f"LLMSummarizer output was not in expected format: {summarizer_output}")
        
        for node_name, output_tuple in pipeline_result.items():
            if isinstance(output_tuple, tuple):
                output_data = output_tuple[0]
                logger.debug(f"Output from {node_name}: {list(output_data.keys()) if isinstance(output_data, dict) else type(output_data)}")
    
    except Exception as e:
        logger.error(f"Error running WebSearch pipeline test: {e}", exc_info=True)
        logger.error("Ensure SearchAPI_API_Key environment variable is set if you want to test with real API calls")
