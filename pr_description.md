# Enhanced Intent Detection with Volatility-Based Classification

## Overview
This PR implements the enhanced intent detection specification with a sophisticated volatility-based classification system to improve routing between chat and websearch intents.

## Problem Solved
- **Issue**: General biographical queries like "Who is Angela Merkel" were incorrectly triggering websearch instead of chat
- **Issue**: Time-sensitive queries like "Who are the ministers of German government" needed better detection for websearch routing
- **Issue**: Lack of configurable volatility indicators for fine-tuning intent classification

## Implementation Details

### New Modules Created
- **`orchestrator/volatility_classifier.py`**: Keyword-based heuristics for static/semi_static/volatile classification
- **`orchestrator/prompt_preprocessor.py`**: Temporal cue detection with comprehensive keyword patterns

### Enhanced Components
- **`orchestrator/intent_extractor.py`**: Two-step inference process (keyword pre-analysis → LLM confirmation)
- **`frontend/src/components/common/SettingsModal.tsx`**: New "Volatility Indicators" tab for editable keyword categories
- **`gateway/main.py`**: Backend API endpoints (`/volatility-settings` GET/POST) for settings management

### Key Features
1. **Two-Step Inference Process**:
   - Step 1: Keyword-based volatility pre-classification (volatile/semi_static/static/unknown)
   - Step 2: LLM classification with volatility context and temporal cues

2. **Volatility Classification Categories**:
   - **Volatile**: Current/time-sensitive information (ministers, CEO, prices, breaking news)
   - **Semi-static**: Occasionally changing information (product specs, company info)
   - **Static**: Stable/historical information (biography, geography, definitions)

3. **Enhanced LLM Prompts**: Include volatility pre-analysis and temporal context for better classification decisions

4. **Configurable Keywords**: UI interface for editing volatility keyword categories

## Test Results ✅

### Core Issue Resolution
- `"Who is Angela Merkel"` → **chat** ✅ (was incorrectly websearch before)
- `"Who are the ministers of German government"` → **websearch** ✅
- `"Who is the CEO of UBS?"` → **websearch** ✅
- `"Price of Bitcoin today"` → **websearch** ✅
- `"Latest news about German politics"` → **websearch** ✅

### Comprehensive Test Suite
- All volatility classification tests pass (5/5) ✅
- Enhanced intent extraction tests pass ✅
- Temporal cue detection tests pass ✅
- Websearch vs chat distinction tests pass ✅

## API Changes

### New Endpoints
```
GET /volatility-settings - Retrieve current volatility keyword settings
POST /volatility-settings - Update volatility keyword settings
```

### Response Format
All intent classification responses now include:
- `confidence`: 0.0-1.0 confidence score
- `reasoning`: Detailed explanation including volatility analysis
- `volatility_level`: Classification result (static/semi_static/volatile/unknown)
- `requires_websearch`: Boolean flag for websearch requirement

## UI Enhancements
- New "Volatility Indicators" tab in Settings Modal
- Editable text areas for three keyword categories
- Real-time validation and update functionality

## Architecture Impact
The enhanced system maintains backward compatibility while adding sophisticated classification capabilities. The two-step inference process provides better accuracy by combining keyword heuristics with LLM reasoning.

## Link to Devin Run
https://app.devin.ai/sessions/19dbfc0fd2654113a8da76af39ed72c1

## Requested by
Heiko Sundermann (heiko.sundermann@gmail.com)

## Testing Instructions
1. Start the backend: `poetry run python gateway/main.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Test intent classification with various queries
4. Access Settings Modal → Volatility Indicators tab to configure keywords
5. Run test suite: `poetry run pytest tests/unit/test_volatility_classification.py`
