# Examples Directory

This directory contains demo scripts and usage examples for the Swisper Core system.

## Available Examples

### Demo Scripts
- **`demo_enhanced_flow.py`** - Demonstrates the enhanced contract flow with real APIs
  - Tests laptop and GPU search scenarios
  - Shows SearchAPI integration with fallback mechanisms
  - Demonstrates configurable thresholds for enhanced flow
  
- **`demo_websearch.py`** - Web interface demo for WebSearch functionality
  - Flask-based web interface for testing WebSearch features
  - Provides sample queries for different intent types
  - Demonstrates orchestrator integration

## Running Examples

### Enhanced Flow Demo
```bash
python examples/demo_enhanced_flow.py
```

### WebSearch Demo
```bash
python examples/demo_websearch.py
```
Then visit `http://localhost:8080` to interact with the web interface.

## Environment Requirements

Examples may require:
- OpenAI API key (`OpenAI_API_Key` environment variable)
- SearchAPI credentials for product search functionality
- Flask for web-based demos

## Usage Notes

- Demo scripts are designed for testing and demonstration purposes
- They may use mock data or require external API credentials
- Check individual script documentation for specific requirements
- Examples showcase real-world usage patterns of the Swisper Core system
