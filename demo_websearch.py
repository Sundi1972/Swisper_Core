#!/usr/bin/env python3
"""
WebSearch Demo Script
Demonstrates the WebSearch feature functionality in a simple web interface
"""

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

try:
    from orchestrator.core import handle
    logger.info("✅ Swisper components imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import Swisper components: {e}")
    handle = None

@app.route('/')
def index():
    return render_template('demo.html')

@app.route('/api/websearch', methods=['POST'])
def websearch_demo():
    """Demo endpoint for WebSearch functionality"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        if not handle:
            return jsonify({'error': 'Swisper orchestrator not available'}), 500
        
        session_id = "demo_websearch_session"
        
        import asyncio
        logger.info(f"Executing WebSearch for query: {query}")
        try:
            messages = [{"role": "user", "content": query}]
            result = asyncio.run(handle(messages, session_id))
            logger.info(f"Handle result type: {type(result)}, content: {result}")
        except Exception as e:
            logger.error(f"Handle execution error: {e}", exc_info=True)
            raise
        
        if isinstance(result, str):
            response_text = result
            actual_session_id = session_id
        else:
            response_text = result.get('reply', 'No response generated')
            actual_session_id = result.get('session_id', session_id)
        
        return jsonify({
            'query': query,
            'response': response_text,
            'session_id': actual_session_id,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"WebSearch demo error: {e}")
        return jsonify({
            'error': f'WebSearch demo failed: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/test-queries')
def test_queries():
    """Provide sample test queries for the demo"""
    return jsonify({
        'websearch_queries': [
            "Who are the new German ministers 2025?",
            "What is the latest news today?",
            "Current weather in Switzerland",
            "Recent developments in AI technology",
            "Breaking news about climate change"
        ],
        'contract_queries': [
            "I want to buy a laptop",
            "Find me a smartphone",
            "Shop for headphones"
        ],
        'rag_queries': [
            "#rag What is Swisper?",
            "#rag How does the contract engine work?"
        ]
    })

if __name__ == '__main__':
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
