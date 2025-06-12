from haystack.pipelines import Pipeline
from haystack.nodes import PreProcessor
from transformers import pipeline as transformers_pipeline
from typing import List, Dict, Any
import os
from swisper_core import get_logger

logger = get_logger(__name__)

def create_rolling_summariser_pipeline() -> Pipeline:
    """Create T5-based map-reduce summarization pipeline for Switzerland hosting"""
    pipeline = Pipeline()
    
    preprocessor = PreProcessor(
        split_by='word',
        split_length=100,
        split_overlap=20,
        split_respect_sentence_boundary=True
    )
    
    use_gpu = os.getenv("USE_GPU", "false").lower() == "true"
    
    t5_pipeline = transformers_pipeline(
        "summarization",
        model="t5-small", 
        device=-1 if not use_gpu else 0,  # CPU or GPU
        max_length=150,
        min_length=30,
        do_sample=False,
        num_beams=2,
        early_stopping=True
    )
    
    from haystack.nodes.base import BaseComponent
    
    class DirectT5Summarizer(BaseComponent):
        outgoing_edges = 1
        
        def __init__(self, t5_pipeline):
            super().__init__()
            self.t5_pipeline = t5_pipeline
            
        def run(self, documents):
            if not documents:
                return {"documents": []}, "output_1"
            
            combined_text = "\n\n".join([doc.content for doc in documents if doc.content])
            
            if not combined_text.strip():
                return {"documents": []}, "output_1"
            
            summary_result = self.t5_pipeline(
                combined_text,
                max_length=150,
                min_length=30,
                do_sample=False,
                num_beams=2,
                early_stopping=True
            )
            
            if summary_result and len(summary_result) > 0:
                from haystack.schema import Document
                summary_doc = Document(content=summary_result[0]['summary_text'])
                return {"documents": [summary_doc]}, "output_1"
            else:
                return {"documents": []}, "output_1"
        
        def run_batch(self, documents_batch):
            """Process batch of document lists"""
            results = []
            for documents in documents_batch:
                result, _ = self.run(documents)
                results.append(result)
            return {"documents_batch": results}, "output_1"
    
    summarizer = DirectT5Summarizer(t5_pipeline)
    
    pipeline.add_node(component=preprocessor, name="TextSplitter", inputs=["Query"])
    pipeline.add_node(component=summarizer, name="Summarizer", inputs=["TextSplitter"])
    
    logger.info(f"RollingSummariser Pipeline created successfully (GPU: {use_gpu})")
    return pipeline

def summarize_messages(messages: List[Dict[str, Any]]) -> str:
    """Summarize list of messages using T5-based pipeline with PII protection"""
    try:
        if not messages:
            return ""
        
        content_parts = []
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content_parts.append(str(msg["content"]))
        
        combined_content = " ".join(content_parts)
        
        from contract_engine.privacy.pii_redactor import pii_redactor
        redacted_content = pii_redactor.redact(combined_content, redaction_method="placeholder")
        
        logger.info(f"Applied PII redaction before T5 summarization")
        
        pipeline = create_rolling_summariser_pipeline()
        from haystack.schema import Document
        documents = [Document(content=redacted_content)]
        result = pipeline.run(documents=documents)
        
        if "Summarizer" in result and result["Summarizer"]:
            summary_output = result["Summarizer"][0]
            if isinstance(summary_output, dict) and "summary" in summary_output:
                return summary_output["summary"]
            elif isinstance(summary_output, str):
                return summary_output
        
        return redacted_content[:200] + "..." if len(redacted_content) > 200 else redacted_content
        
    except Exception as e:
        logger.error(f"T5 summarization failed: {e}")
        combined_content = " ".join([str(msg.get("content", "")) for msg in messages])
        fallback_summary = combined_content[:200] + "..." if len(combined_content) > 200 else combined_content
        return f"[T5 Fallback] {fallback_summary}"
