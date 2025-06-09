# T5 Model Usage Guide for Swisper_Core

## Overview

Swisper_Core uses T5 (Text-to-Text Transfer Transformer) models for local text summarization to meet Switzerland hosting requirements. This guide covers implementation details, configuration options, testing procedures, and fallback mechanisms.

## Architecture

### T5 Components

1. **WebSearch Summarizer** (`websearch_pipeline/websearch_components.py`)
   - Summarizes web search results for user queries
   - Uses `LLMSummarizerComponent` with T5-small model
   - Provides fallback to simple text concatenation

2. **Rolling Summarizer** (`contract_engine/pipelines/rolling_summariser.py`)
   - Summarizes chat message history for memory management
   - Uses map-reduce approach with Haystack pipeline
   - Maintains conversation context within token limits

### Model Specifications

- **Model**: `t5-small` (60M parameters)
- **Performance**: <200ms inference time (Switzerland SLA compliance)
- **Memory**: ~240MB model size
- **Tokenizer**: SentencePiece-based T5 tokenizer

## Configuration

### GPU Usage

T5 components support configurable GPU usage via environment variables:

```bash
# Enable GPU acceleration (requires CUDA)
export USE_GPU=true

# Use CPU inference (default, recommended for production)
export USE_GPU=false
```

**Default Configuration:**
- CPU inference (`USE_GPU=false`) for consistency and compliance
- Suitable for Switzerland hosting requirements
- Ensures predictable performance across environments

### Dependencies

Required packages (automatically installed via Poetry):
```toml
transformers = ">=4.46,<5.0"
sentencepiece = "*"
torch = "*"
haystack-ai = "*"
```

## Implementation Details

### WebSearch Summarizer

```python
from websearch_pipeline.websearch_components import LLMSummarizerComponent

# Initialize component (reads USE_GPU from environment)
summarizer = LLMSummarizerComponent()

# Summarize search results
result, _ = summarizer.run(
    ranked_results=[
        {"title": "Title", "snippet": "Content", "link": "URL"}
    ],
    query="user query"
)
```

**Features:**
- Automatic T5 model initialization with fallback
- Content length validation and truncation
- Error handling with graceful degradation
- Source tracking for generated summaries

### Rolling Summarizer

```python
from contract_engine.pipelines.rolling_summariser import summarize_messages

# Summarize message history
messages = [
    {"content": "User message 1"},
    {"content": "Assistant response 1"},
    {"content": "User message 2"}
]

summary = summarize_messages(messages)
```

**Features:**
- Map-reduce summarization for long conversations
- Configurable token limits (150 max, 30 min)
- Preprocessing with sentence boundary respect
- Beam search for quality improvement

## Fallback Mechanisms

### Import-Level Fallbacks

When T5 dependencies are unavailable:

```python
try:
    from haystack.nodes import TransformersSummarizer
    # Initialize T5 model
except ImportError:
    logger.warning("TransformersSummarizer not available, falling back to simple concatenation")
    self.summarizer = None
```

### Runtime Fallbacks

When T5 inference fails:

1. **WebSearch**: Falls back to simple text concatenation of top snippets
2. **Memory**: Falls back to truncated message concatenation
3. **Error Logging**: Comprehensive error tracking for debugging

### Fallback Quality

- **Simple Concatenation**: Combines top 3 search results (500 char limit)
- **Message Truncation**: First 200 characters of combined messages
- **Source Preservation**: Maintains original source links and metadata

## Testing

### Runtime Testing via GUI

The frontend provides test buttons for both T5 components:

1. **T5 WebSearch Test Button** (🔍 icon)
   - Tests websearch summarization functionality
   - Shows T5 availability, GPU status, fallback usage
   - Displays generated summary and sources

2. **T5 Memory Test Button** (💡 icon)
   - Tests rolling summarizer for memory management
   - Shows message processing count and summary length
   - Displays generated conversation summary

### API Testing

Test endpoints are available for programmatic testing:

```bash
# Test websearch summarization
curl -X POST http://localhost:8000/api/test/t5-websearch

# Test memory summarization
curl -X POST http://localhost:8000/api/test/t5-memory
```

**Response Format:**
```json
{
  "test_type": "t5_websearch",
  "success": true,
  "t5_available": true,
  "gpu_enabled": false,
  "summary": "Generated summary text...",
  "sources": ["url1", "url2"],
  "fallback_used": false
}
```

### Unit Testing

Run T5-specific tests:

```bash
# Test rolling summarizer
poetry run pytest tests/test_rolling_summariser.py -v

# Test websearch components
poetry run pytest websearch_pipeline/tests/test_websearch_components.py -v

# Test with GPU disabled
USE_GPU=false poetry run pytest tests/test_rolling_summariser.py -v
```

## Performance Considerations

### Switzerland Hosting Compliance

- **SLA Requirement**: <200ms summarization time
- **Model Choice**: T5-small meets performance requirements
- **CPU Inference**: Ensures consistent performance
- **Local Processing**: No external API dependencies

### Memory Usage

- **Model Loading**: ~240MB RAM for T5-small
- **Inference**: Additional ~100-200MB during processing
- **Caching**: Models cached after first load
- **Cleanup**: Automatic garbage collection after inference

### Optimization Tips

1. **Batch Processing**: Process multiple texts together when possible
2. **Content Truncation**: Limit input length to 512 tokens
3. **Caching**: Reuse loaded models across requests
4. **Monitoring**: Track inference times and memory usage

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   ImportError: No module named 'transformers'
   ```
   **Solution**: Install dependencies via `poetry install`

2. **CUDA Errors** (when USE_GPU=true)
   ```
   RuntimeError: CUDA out of memory
   ```
   **Solution**: Set `USE_GPU=false` or reduce batch size

3. **Model Download Failures**
   ```
   OSError: Can't load tokenizer for 't5-small'
   ```
   **Solution**: Check internet connection, clear Hugging Face cache

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("websearch_pipeline").setLevel(logging.DEBUG)
logging.getLogger("contract_engine").setLevel(logging.DEBUG)
```

Check component status:

```python
from websearch_pipeline.websearch_components import LLMSummarizerComponent

component = LLMSummarizerComponent()
print(f"T5 Available: {component.summarizer is not None}")
print(f"GPU Enabled: {os.getenv('USE_GPU', 'false').lower() == 'true'}")
```

## Security Considerations

### Data Privacy

- **Local Processing**: All summarization happens locally
- **No External APIs**: No data sent to third-party services
- **Memory Cleanup**: Sensitive data cleared after processing
- **Audit Logging**: All operations logged for compliance

### Model Security

- **Verified Models**: Only use official Hugging Face T5 models
- **Checksum Validation**: Automatic model integrity verification
- **Sandboxing**: Models run in isolated Python environments
- **Resource Limits**: Memory and CPU usage monitoring

## Migration Guide

### From External APIs

If migrating from OpenAI or other external summarization APIs:

1. **Replace API Calls**: Use T5 components instead of external APIs
2. **Update Configuration**: Set `USE_GPU=false` for production
3. **Test Fallbacks**: Verify graceful degradation when T5 unavailable
4. **Monitor Performance**: Ensure <200ms SLA compliance

### Upgrading T5 Models

To upgrade from t5-small to t5-base (if performance allows):

1. **Update Model Name**: Change `model_name_or_path="t5-base"`
2. **Increase Limits**: Adjust `max_length` and `min_length` parameters
3. **Test Performance**: Verify <200ms SLA still met
4. **Update Documentation**: Reflect new model specifications

## Best Practices

### Development

1. **Test Locally**: Always test T5 functionality before deployment
2. **Use Fallbacks**: Implement comprehensive fallback mechanisms
3. **Monitor Performance**: Track inference times and memory usage
4. **Error Handling**: Log errors for debugging and monitoring

### Production

1. **CPU Inference**: Use `USE_GPU=false` for consistency
2. **Resource Monitoring**: Monitor memory and CPU usage
3. **Health Checks**: Use test endpoints for system monitoring
4. **Graceful Degradation**: Ensure system works when T5 unavailable

### Testing

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test end-to-end summarization workflows
3. **Performance Tests**: Verify SLA compliance under load
4. **Fallback Tests**: Test behavior when T5 models unavailable

## Support

For issues or questions regarding T5 implementation:

1. **Check Logs**: Review application logs for error details
2. **Test Endpoints**: Use GUI test buttons or API endpoints
3. **Verify Configuration**: Ensure correct environment variables
4. **Review Documentation**: Check this guide and code comments

## References

- [T5 Paper](https://arxiv.org/abs/1910.10683) - Original T5 research
- [Hugging Face T5](https://huggingface.co/docs/transformers/model_doc/t5) - Model documentation
- [Haystack Documentation](https://docs.haystack.deepset.ai/) - Pipeline framework
- [Switzerland Data Protection](https://www.admin.ch/opc/en/classified-compilation/20022520/index.html) - Compliance requirements
