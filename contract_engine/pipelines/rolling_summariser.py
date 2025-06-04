from haystack.pipelines import Pipeline
from haystack.nodes import TransformersSummarizer, PreProcessor
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def create_rolling_summariser_pipeline() -> Pipeline:
    """Create T5-based map-reduce summarization pipeline for Switzerland hosting"""
    pipeline = Pipeline()
    
    preprocessor = PreProcessor(
        split_by='sentence',
        split_length=10,
        split_overlap=2,
        max_seq_len=512,
        split_respect_sentence_boundary=True
    )
    
    summarizer = TransformersSummarizer(
        model_name_or_path='t5-small',
        use_gpu=False,
        max_length=150,
        min_length=30,
        do_sample=False,
        num_beams=2,
        early_stopping=True
    )
    
    pipeline.add_node(component=preprocessor, name="TextSplitter", inputs=["Query"])
    pipeline.add_node(component=summarizer, name="Summarizer", inputs=["TextSplitter"])
    
    logger.info("RollingSummariser Pipeline created successfully")
    return pipeline

def summarize_messages(messages: List[Dict[str, Any]]) -> str:
    """Summarize list of messages using T5-based pipeline"""
    try:
        if not messages:
            return ""
        
        content_parts = []
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content_parts.append(str(msg["content"]))
        
        combined_content = " ".join(content_parts)
        
        pipeline = create_rolling_summariser_pipeline()
        result = pipeline.run(query=combined_content)
        
        if "Summarizer" in result and result["Summarizer"]:
            summary_output = result["Summarizer"][0]
            if isinstance(summary_output, dict) and "summary" in summary_output:
                return summary_output["summary"]
            elif isinstance(summary_output, str):
                return summary_output
        
        return combined_content[:200] + "..." if len(combined_content) > 200 else combined_content
        
    except Exception as e:
        logger.error(f"T5 summarization failed: {e}")
        combined_content = " ".join([str(msg.get("content", "")) for msg in messages])
        return combined_content[:200] + "..." if len(combined_content) > 200 else combined_content
