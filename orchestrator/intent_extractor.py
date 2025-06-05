import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
import yaml

from .llm_adapter import get_llm_adapter
from swisper_core import get_logger

logger = get_logger(__name__)

def load_available_contracts() -> Dict[str, Any]:
    """Load available contract templates"""
    contracts = {}
    contract_dir = "contract_templates"
    
    if os.path.exists(contract_dir):
        for filename in os.listdir(contract_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                try:
                    with open(os.path.join(contract_dir, filename), 'r') as f:
                        contract_data = yaml.safe_load(f)
                        contracts[filename] = {
                            "type": contract_data.get("contract_type"),
                            "description": contract_data.get("description"),
                            "parameters": list(contract_data.get("parameters", {}).keys())
                        }
                except Exception as e:
                    logger.error(f"Failed to load contract {filename}: {e}")
    
    return contracts

def load_available_tools() -> Dict[str, Any]:
    """Load available MCP tools"""
    try:
        from mcp_server.swisper_mcp import create_mcp_server
        server = create_mcp_server()
        tools_data = server.list_tools()
        return tools_data.get("tools", {})
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}")
        return {}

def extract_user_intent(user_message: str) -> Dict[str, Any]:
    """Extract user intent using LLM with fallback to regex"""
    
    contracts = load_available_contracts()
    tools = load_available_tools()
    
    system_prompt = f"""You are an intent classifier for the Swisper AI assistant. Analyze user messages and classify their intent.

Available Contract Templates:
{json.dumps(contracts, indent=2)}

Available Tools:
{json.dumps(tools, indent=2)}

Classify the user's intent into one of these types:
1. "contract" - User wants to execute a structured workflow (e.g., purchase, booking)
2. "rag" - User wants to ask questions about documents (starts with #rag)
3. "tool_usage" - User needs tools but no structured workflow exists
4. "chat" - General conversation

Respond with JSON in this exact format:
{{
  "intent_type": "contract|rag|tool_usage|chat",
  "confidence": 0.0-1.0,
  "parameters": {{
    "contract_template": "filename.yaml or null",
    "tools_needed": ["tool1", "tool2"] or [],
    "extracted_query": "enhanced search query",
    "rag_question": "document question or null"
  }},
  "reasoning": "brief explanation"
}}

Be confident in your classifications. Use high confidence (>0.8) for clear intents."""

    user_prompt = f"User message: {user_message}"
    
    try:
        llm_adapter = get_llm_adapter()
        response = llm_adapter.chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        intent_data = json.loads(response)
        
        confidence = intent_data.get("confidence", 0.0)
        if confidence < 0.85:
            logger.info(f"LLM confidence {confidence} below threshold, using fallback")
            return _fallback_intent_extraction(user_message)
            
        return intent_data
        
    except Exception as e:
        logger.error(f"LLM intent extraction failed: {e}")
        return _fallback_intent_extraction(user_message)

def _fallback_intent_extraction(user_message: str) -> Dict[str, Any]:
    """Fallback regex-based intent extraction"""
    
    if user_message.lower().startswith("#rag"):
        return {
            "intent_type": "rag",
            "confidence": 1.0,
            "parameters": {
                "contract_template": None,
                "tools_needed": [],
                "extracted_query": "",
                "rag_question": user_message[4:].strip()
            },
            "reasoning": "RAG prefix detected"
        }
    
    contract_keywords = r"\b(buy|purchase|order|acquire|get me|shop for|find a|buy an)\b"
    if re.search(contract_keywords, user_message, re.IGNORECASE):
        return {
            "intent_type": "contract",
            "confidence": 0.9,
            "parameters": {
                "contract_template": "purchase_item.yaml",
                "tools_needed": [],
                "extracted_query": user_message,
                "rag_question": None
            },
            "reasoning": "Purchase keywords detected"
        }
    
    tool_keywords = r"\b(compare|check|compatibility|compatible|specifications|specs|analyze|filter)\b"
    if re.search(tool_keywords, user_message, re.IGNORECASE):
        return {
            "intent_type": "tool_usage",
            "confidence": 0.8,
            "parameters": {
                "contract_template": None,
                "tools_needed": ["search_products", "analyze_product_attributes"],
                "extracted_query": user_message,
                "rag_question": None
            },
            "reasoning": "Tool usage keywords detected"
        }
    
    return {
        "intent_type": "chat",
        "confidence": 0.8,
        "parameters": {
            "contract_template": None,
            "tools_needed": [],
            "extracted_query": "",
            "rag_question": None
        },
        "reasoning": "No specific intent detected"
    }
