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
    current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up from orchestrator to repo root
    contract_dir = os.path.join(current_dir, "contract_templates")
    
    logger.info(f"Looking for contracts in: {contract_dir}")
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
        return {
            "search_web": {
                "description": "Search the web for current events, news, and general information using SearchAPI.io",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Web search query for current events, news, or general information"}
                    },
                    "required": ["query"]
                }
            },
            "search_products": {
                "description": "Search for products using SearchAPI.io with fallback to mock data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Product search query"}
                    },
                    "required": ["query"]
                }
            },
            "analyze_product_attributes": {
                "description": "Analyze products to extract key differentiating attributes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "products": {"type": "array", "description": "List of product objects"},
                        "product_type": {"type": "string", "description": "Product category"}
                    },
                    "required": ["products"]
                }
            },
            "check_compatibility": {
                "description": "Check product compatibility against user constraints",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "products": {"type": "array", "description": "List of products"},
                        "constraints": {"type": "object", "description": "User constraints"},
                        "product_type": {"type": "string", "description": "Product category"}
                    },
                    "required": ["products", "constraints"]
                }
            },
            "filter_products_by_preferences": {
                "description": "Filter products based on user preferences",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "products": {"type": "array", "description": "List of products"},
                        "preferences": {"type": "array", "description": "User preferences"}
                    },
                    "required": ["products", "preferences"]
                }
            }
        }

def _generate_routing_manifest() -> Dict[str, Any]:
    """Generate routing manifest with available contracts, tools, and intent types"""
    
    contracts = load_available_contracts()
    tools = load_available_tools()
    
    contract_options = []
    for filename, contract_info in contracts.items():
        contract_name = contract_info.get("type", filename.replace(".yaml", ""))
        description = contract_info.get("description", f"Execute {contract_name} workflow")
        
        trigger_keywords = []
        if contract_name == "purchase_item":
            trigger_keywords = ["buy", "purchase", "order", "acquire", "shop for", "find to buy", "want to buy", "looking for", "need to buy"]
        
        contract_options.append({
            "name": contract_name,
            "template": filename,
            "description": description,
            "trigger_keywords": trigger_keywords
        })
    
    tool_names = list(tools.keys())
    
    routing_manifest = {
        "routing_options": [
            {
                "intent_type": "chat",
                "description": "General open-ended conversation"
            },
            {
                "intent_type": "rag", 
                "description": "Ask questions about uploaded or stored documents (prefix with #rag)"
            },
            {
                "intent_type": "tool_usage",
                "description": "Use tools for analysis, comparison, or information gathering",
                "tools": tool_names
            },
            {
                "intent_type": "contract",
                "description": "Execute structured workflows with specific business logic",
                "contracts": contract_options
            }
        ]
    }
    
    return routing_manifest

def extract_user_intent(user_message: str) -> Dict[str, Any]:
    """Extract user intent using two-step process: volatility classification then LLM confirmation"""
    from .volatility_classifier import classify_entity_category
    from .prompt_preprocessor import has_temporal_cue
    
    volatility_result = classify_entity_category(user_message)
    temporal_cue = has_temporal_cue(user_message)
    
    logger.info("Pre-classification - Volatility: %s, Temporal: %s", volatility_result['volatility'], temporal_cue)
    
    routing_manifest = _generate_routing_manifest()
    
    try:
        intent_result = _classify_intent_with_llm_enhanced(
            user_message, routing_manifest, volatility_result, temporal_cue
        )
        
        confidence = intent_result.get("confidence", 0.0)
        logger.info("Enhanced LLM classified intent as '%s' with confidence %s", intent_result['intent_type'], confidence)
        logger.info("LLM reasoning: %s", intent_result.get('reasoning', 'No reasoning provided'))
        
        if confidence < 0.6:
            logger.warning("Low LLM confidence %s, falling back to regex classification", confidence)
            return _create_chat_fallback(user_message, f"Low LLM confidence: {confidence}")
        
        return intent_result
        
    except Exception as e:
        logger.error("Enhanced LLM intent classification failed: %s", e)
        logger.info("Falling back to regex-based classification")
        return _create_chat_fallback(user_message, f"LLM unavailable: {str(e)}")

def _classify_intent_with_llm(user_message: str, routing_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Use dedicated LLM to classify intent based on routing manifest"""
    
    available_templates = []
    for option in routing_manifest.get("routing_options", []):
        if option.get("intent_type") == "contract":
            for contract in option.get("contracts", []):
                available_templates.append(contract.get("template"))
    
    system_prompt = f"""You are a routing assistant for an intelligent agent platform. Given a user message and a list of available intents, choose the most appropriate one and justify your decision.

AVAILABLE ROUTING OPTIONS:
{json.dumps(routing_manifest, indent=2)}

CLASSIFICATION RULES:
1. For purchase-related requests (buy, purchase, order, acquire, shop for), use "contract" intent
2. For document questions starting with "#rag", use "rag" intent  
3. For analysis, comparison, or tool-based tasks, use "tool_usage" intent
4. For general conversation, use "chat" intent

STRICT TEMPLATE SELECTION:
- You MUST only select contract templates from this exact list: {available_templates}
- Do NOT invent template names like "filename.yaml" 
- For purchase requests, use EXACTLY: "purchase_item.yaml"

CONFIDENCE SCORING:
- 0.9-1.0: Very clear intent match with strong keywords
- 0.7-0.9: Good intent match with supporting context  
- 0.5-0.7: Reasonable intent match but some ambiguity
- 0.3-0.5: Low confidence but still classifiable
- 0.0-0.3: Unclear or ambiguous intent

Respond with JSON in this exact format:
{{
  "intent_type": "contract|rag|tool_usage|chat",
  "confidence": 0.0-1.0,
  "contract_template": "purchase_item.yaml|null",
  "tools_needed": ["tool1", "tool2"] or [],
  "extracted_query": "enhanced search query or original message", 
  "rag_question": "document question or null",
  "reasoning": "detailed explanation of classification decision including matched keywords and context"
}}

CRITICAL: Only use exact template names from the available list. Never invent new template names."""

    user_prompt = f"User message: {user_message}"
    
    try:
        llm_adapter = get_llm_adapter()
        response = llm_adapter.chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        return _parse_llm_response(response, user_message, available_templates)
        
    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        logger.error(f"Raw response was: {response if 'response' in locals() else 'No response'}")
        raise

def _classify_intent_with_llm_enhanced(user_message: str, routing_manifest: Dict[str, Any], 
                                     volatility_result: Dict[str, Any], temporal_cue: bool) -> Dict[str, Any]:
    """Enhanced LLM classification with volatility and temporal context"""
    
    available_templates = []
    for option in routing_manifest.get("routing_options", []):
        if option.get("intent_type") == "contract":
            for contract in option.get("contracts", []):
                available_templates.append(contract.get("template"))
    
    system_prompt = f"""You are an intelligent intent classification engine for a privacy-first AI assistant.

Your job is to determine how a user request should be handled based on:
- The user's original message
- Volatility classification from keyword heuristics
- Temporal cue detection
- Available contracts and tools

AVAILABLE ROUTING OPTIONS:
{json.dumps(routing_manifest, indent=2)}

PRE-ANALYSIS CONTEXT:
- Volatility Level: {volatility_result['volatility']}
- Temporal Cue Detected: {temporal_cue}
- Keyword Reason: {volatility_result['reason']}

ENHANCED CLASSIFICATION RULES:
1. For purchase-related requests (buy, purchase, order, acquire, shop for), use "contract" intent
2. For document questions starting with "#rag", use "rag" intent  
3. For analysis, comparison, or tool-based tasks, use "tool_usage" intent
4. For general conversation and static knowledge, use "chat" intent
5. For current/time-sensitive information requests, use "websearch" intent

WEBSEARCH vs CHAT DISTINCTION:
- Use "websearch" for queries requiring current, up-to-date information:
  * Current government officials, ministers, cabinet members, CEOs
  * Latest news, recent events, breaking news, current prices
  * Questions with temporal indicators or volatile keywords
  * Volatility level "volatile" strongly suggests websearch
- Use "chat" for general knowledge that doesn't change frequently:
  * Historical facts, biographical information about well-known figures
  * Geographic information, scientific facts, mathematical concepts
  * Volatility level "static" strongly suggests chat

STRICT TEMPLATE SELECTION:
- You MUST only select contract templates from this exact list: {available_templates}
- For purchase requests, use EXACTLY: "purchase_item.yaml"

Respond with JSON in this exact format:
{{
  "intent_type": "chat|websearch|rag|tool_usage|contract",
  "confidence": 0.0-1.0,
  "contract_template": "purchase_item.yaml|null",
  "tools_needed": ["tool1", "tool2"] or [],
  "extracted_query": "enhanced search query or original message",
  "rag_question": "document question or null",
  "volatility_level": "{volatility_result['volatility']}",
  "requires_websearch": true/false,
  "reasoning": "detailed explanation including volatility analysis and temporal context"
}}"""

    user_prompt = f"User message: {user_message}"
    
    llm_adapter = get_llm_adapter()
    response = llm_adapter.chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    return _parse_llm_response(response, user_message, available_templates)

def _parse_llm_response(response: str, user_message: str, available_templates: list) -> Dict[str, Any]:
    """Parse and validate LLM response for intent classification"""
    logger.info("LLM raw response: %s", response)
    
    if not response or not response.strip():
        raise ValueError("Empty LLM response")
    
    cleaned_response = response.strip()
    if cleaned_response.startswith('```json'):
        cleaned_response = cleaned_response[7:]
    if cleaned_response.startswith('```'):
        cleaned_response = cleaned_response[3:]
    if cleaned_response.endswith('```'):
        cleaned_response = cleaned_response[:-3]
    cleaned_response = cleaned_response.strip()
    
    logger.info("Cleaned response: %s", cleaned_response)
        
    intent_data = json.loads(cleaned_response)
    
    required_fields = ["intent_type", "confidence", "reasoning"]
    for field in required_fields:
        if field not in intent_data:
            raise ValueError(f"Missing required field: {field}")
    
    if "contract_template" not in intent_data:
        intent_data["contract_template"] = None
    elif intent_data["contract_template"]:
        template = intent_data["contract_template"]
        logger.info(f"LLM returned contract_template: '{template}'")
        
        if template in available_templates:
            logger.info(f"✅ Valid contract template: '{template}'")
        else:
            logger.warning(f"❌ Invalid contract template '{template}' not in available list: {available_templates}")
            if intent_data.get("intent_type") == "contract" and "purchase_item.yaml" in available_templates:
                intent_data["contract_template"] = "purchase_item.yaml"
                logger.info(f"🔧 Corrected to valid template: 'purchase_item.yaml'")
            else:
                logger.error(f"No valid contract template found, falling back to chat")
                return _create_chat_fallback(user_message, f"Invalid contract template: {template}")
    
    for field, default in [
        ("tools_needed", []),
        ("extracted_query", user_message),
        ("rag_question", None),
        ("volatility_level", "unknown"),
        ("requires_websearch", False)
    ]:
        if field not in intent_data:
            intent_data[field] = default
    
    if intent_data["extracted_query"] == "?":
        intent_data["extracted_query"] = user_message
        
    intent_data["parameters"] = {
        "contract_template": intent_data["contract_template"],
        "tools_needed": intent_data["tools_needed"],
        "extracted_query": intent_data["extracted_query"],
        "rag_question": intent_data["rag_question"]
    }
    
    return intent_data

def _create_chat_fallback(user_message: str, reason: str) -> Dict[str, Any]:
    """Create chat intent fallback for low confidence or error cases"""
    
    if user_message.strip().startswith("#rag"):
        rag_question = user_message.strip()[4:].strip()
        logger.info(f"🔍 RAG prefix detected in fallback, routing to RAG: {user_message}")
        return {
            "intent_type": "rag",
            "confidence": 0.95,
            "contract_template": None,
            "tools_needed": [],
            "extracted_query": user_message,
            "rag_question": rag_question,
            "parameters": {
                "contract_template": None,
                "tools_needed": [],
                "extracted_query": user_message,
                "rag_question": rag_question
            },
            "reasoning": f"RAG fallback: detected #rag prefix in '{user_message}'",
            "fallback_reason": f"RAG prefix detected: {reason}"
        }
    
    purchase_keywords = r"\b(buy|purchase|order|acquire|shop for|find to buy|want to buy|looking for|need to buy|get me|buying|find me a|find a good|looking to get|need a new)\b"
    logger.info(f"🔍 DEBUG: Checking Purchase contract keywords in '{user_message}' with pattern '{purchase_keywords}'")
    purchase_match = re.search(purchase_keywords, user_message, re.IGNORECASE)
    logger.info(f"🔍 DEBUG: Purchase regex match result: {purchase_match}")
    if purchase_match:
        logger.info(f"🔍 Purchase keywords detected in fallback, routing to contract: {user_message}")
        return {
            "intent_type": "contract",
            "confidence": 0.85,
            "contract_template": "purchase_item.yaml",
            "tools_needed": [],
            "extracted_query": user_message,
            "rag_question": None,
            "parameters": {
                "contract_template": "purchase_item.yaml",
                "tools_needed": [],
                "extracted_query": user_message,
                "rag_question": None
            },
            "reasoning": f"Contract fallback: detected purchase keywords '{purchase_match.group()}' in '{user_message}'",
            "fallback_reason": f"Purchase keywords detected: {reason}"
        }
    
    websearch_keywords = r"\b(latest|current|recent|2025|2024|breaking|news|search the web|ministers|government|politics|developments|events)\b"
    logger.info(f"🔍 DEBUG: Checking WebSearch keywords in '{user_message}' with pattern '{websearch_keywords}'")
    websearch_match = re.search(websearch_keywords, user_message, re.IGNORECASE)
    logger.info(f"🔍 DEBUG: WebSearch regex match result: {websearch_match}")
    if websearch_match:
        logger.info(f"🔍 WebSearch keywords detected in fallback, routing to websearch: {user_message}")
        return {
            "intent_type": "websearch",
            "confidence": 0.75,
            "contract_template": None,
            "tools_needed": [],
            "extracted_query": user_message,
            "rag_question": None,
            "parameters": {
                "contract_template": None,
                "tools_needed": [],
                "extracted_query": user_message,
                "rag_question": None
            },
            "reasoning": f"WebSearch fallback: detected time-sensitive keywords '{websearch_match.group()}' in '{user_message}'",
            "fallback_reason": f"WebSearch keywords detected: {reason}"
        }
    
    tool_keywords = r"\b(compare|check|analyze|filter|compatibility|specifications)\b"
    tool_match = re.search(tool_keywords, user_message, re.IGNORECASE)
    if tool_match:
        logger.info(f"🔍 Tool keywords detected in fallback, routing to tool_usage: {user_message}")
        return {
            "intent_type": "tool_usage",
            "confidence": 0.75,
            "contract_template": None,
            "tools_needed": [],
            "extracted_query": user_message,
            "rag_question": None,
            "parameters": {
                "contract_template": None,
                "tools_needed": [],
                "extracted_query": user_message,
                "rag_question": None
            },
            "reasoning": f"Tool usage fallback: detected tool keywords '{tool_match.group()}' in '{user_message}'",
            "fallback_reason": f"Tool keywords detected: {reason}"
        }
    
    return {
        "intent_type": "chat",
        "confidence": 0.7,
        "contract_template": None,
        "tools_needed": [],
        "extracted_query": user_message,
        "rag_question": None,
        "parameters": {
            "contract_template": None,
            "tools_needed": [],
            "extracted_query": user_message,
            "rag_question": None
        },
        "reasoning": f"Fallback to chat: {reason}",
        "fallback_reason": reason
    }
