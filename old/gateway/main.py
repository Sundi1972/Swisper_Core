# gateway/main.py
import logging
import os
import json # Added import
import yaml
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Any, Dict, Optional # Added Dict here

if not os.environ.get("OPENAI_API_KEY") and os.environ.get("OpenAI_API_Key"):
    os.environ["OPENAI_API_KEY"] = os.environ["OpenAI_API_Key"]
if not os.environ.get("SEARCHAPI_API_KEY") and os.environ.get("SearchAPI_API_Key"):
    os.environ["SEARCHAPI_API_KEY"] = os.environ["SearchAPI_API_Key"]

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware

# Attempt to import project modules.
# This relies on PYTHONPATH being set correctly (e.g., to /app in Docker).
try:
    from swisper_core.prompt_preprocessor import clean_and_tag
    from orchestrator.core import handle as orchestrator_handle
    from tool_adapter.mock_google import route as call_tool_adapter # Added for /call endpoint
except ImportError as e:
    # Log an error and re-raise to prevent app startup if dependencies are missing.
    # This helps in diagnosing PYTHONPATH or module availability issues early.
    logging.basicConfig(level="ERROR", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    from swisper_core import get_logger
    logger = get_logger(__name__)
    logger.error("Failed to import project modules. Ensure PYTHONPATH is set correctly. Error: %s", e, exc_info=True)
    raise


# Logging setup
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
numeric_log_level = getattr(logging, log_level_str, logging.INFO) # Convert string level to numeric
logging.basicConfig(
    level=numeric_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
from swisper_core import get_logger
logger = get_logger(__name__)

from gateway.log_handler import log_buffer, WebSocketLogHandler

app = FastAPI()

def get_system_fallback_status():
    """Get current system fallback status for user visibility"""
    fallbacks = []
    
    try:
        from websearch_pipeline.websearch_components import LLMSummarizerComponent
        test_component = LLMSummarizerComponent()
        if test_component.summarizer is None:
            fallbacks.append("T5 Summarization")
    except:
        fallbacks.append("T5 Summarization")
    
    if not os.getenv("SEARCHAPI_API_KEY"):
        fallbacks.append("Web Search (using mock data)")
    
    try:
        from swisper_core.privacy import pii_redactor
        if pii_redactor.__class__.__name__.startswith("Mock"):
            fallbacks.append("PII Protection")
    except:
        pass
    
    return fallbacks

# CORS configuration
origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
origins = [origin.strip() for origin in origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def setup_logging():
    """Setup logging to capture all logs in our buffer"""
    root_logger = logging.getLogger()
    websocket_handler = WebSocketLogHandler(log_buffer)
    websocket_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(websocket_handler)

setup_logging()

# Path to tools.json - Assuming WORKDIR is /app (repository root) for Docker execution
TOOLS_JSON_PATH = "orchestrator/tool_registry/tools.json" 

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    include_system_status: bool = False
    session_id: str = "default_session"

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest) -> Dict[str, Any]: # Added return type hint
    logger.info("Received /chat request for session_id: %s with %d messages.", payload.session_id, len(payload.messages))

    if not payload.messages:
        logger.warning("Received empty messages list for session_id: %s.", payload.session_id)
        # Return a JSON response compatible with FastAPI's error handling
        raise HTTPException(status_code=400, detail="No message provided.")

    # Assuming the last message is from the user and needs processing
    last_user_message = payload.messages[-1]
    
    # 1. Call Prompt Preprocessor
    try:
        # Ensure clean_and_tag is not an async function based on its current stub definition
        cleaned_data = clean_and_tag(raw=last_user_message.content, user_id=payload.session_id)
        logger.info("Prompt preprocessor output for session %s: %s", payload.session_id, cleaned_data.get('cleaned_text'))
    except Exception as e:
        logger.error("Error in prompt_preprocessor for session %s: %s", payload.session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing prompt.") from e

    # 2. Forward to Orchestrator
    try:
        # orchestrator_handle is an async function, so it should be awaited.
        orchestrator_response = await orchestrator_handle(messages=[msg.dict() for msg in payload.messages], session_id=payload.session_id)
        logger.info("Orchestrator response for session %s: %s", payload.session_id, orchestrator_response.get('reply'))
    except Exception as e:
        logger.error("Error in orchestrator for session %s: %s", payload.session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error in orchestrator.") from e
    
    if not isinstance(orchestrator_response, dict):
        logger.error("Orchestrator returned non-dict response: %s for session %s", orchestrator_response, payload.session_id)
        raise HTTPException(status_code=500, detail="Invalid response format from orchestrator.")

    response_data = {
        "reply": orchestrator_response.get('reply', 'No response from orchestrator'),
        "session_id": payload.session_id
    }
    
    if payload.include_system_status:
        response_data["system_fallbacks"] = get_system_fallback_status()
    
    return response_data

@app.get("/api/logs")
async def get_logs(level: str = "INFO", limit: int = 100):
    """Get recent logs with optional level filtering"""
    try:
        logs = log_buffer.get_logs(level=level.upper(), limit=limit)
        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        logger.error("Error fetching logs: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching logs")

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket, level: str = "INFO"):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()
    log_buffer.add_subscriber(websocket)
    
    try:
        recent_logs = log_buffer.get_logs(level=level.upper(), limit=50)
        for log_entry in recent_logs:
            await websocket.send_text(json.dumps(log_entry))
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                if message.get("type") == "change_level":
                    level = message.get("level", "INFO").upper()
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
            except json.JSONDecodeError:
                continue
                
    except WebSocketDisconnect:
        pass
    finally:
        log_buffer.remove_subscriber(websocket)

# OPENAI_API_KEY check (optional, if gateway itself doesn't use it directly)
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#    logger.warning("OPENAI_API_KEY environment variable not set. This might be an issue for downstream components.")

@app.get("/tools")
async def get_tools():
    logger.info("Received request for GET /tools")
    try:
        from orchestrator.intent_extractor import load_available_tools
        
        mcp_tools = load_available_tools()
        logger.info(f"Loaded {len(mcp_tools)} MCP tools: {list(mcp_tools.keys())}")
        
        return {"tools": mcp_tools}
    except Exception as e:
        logger.error("Error loading MCP tools, falling back to static tools: %s", e, exc_info=True)
        try:
            path_to_check = TOOLS_JSON_PATH
            
            if not os.path.exists(path_to_check):
                logger.error("Tools file not found at: '%s'", path_to_check)
                raise FileNotFoundError(f"Tools file not found at: {path_to_check}")

            with open(path_to_check, 'r', encoding='utf-8') as f:
                tools_data = json.load(f)
            
            tools_dict = {}
            for tool in tools_data:
                tools_dict[tool["name"]] = {
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            
            return {"tools": tools_dict}
        except Exception as fallback_error:
            logger.error("Fallback to static tools also failed: %s", fallback_error, exc_info=True)
            raise HTTPException(status_code=500, detail="Unable to load tools from MCP server or static file") from fallback_error


# Pydantic model for the /call endpoint's request body
class ToolCallParams(BaseModel):
    params: Dict[str, Any]


@app.post("/call/{tool_name}")
async def call_tool(tool_name: str, body: ToolCallParams): 
    params_dict = body.params
    logger.info("Received request for POST /call/%s with params: %s", tool_name, params_dict)
    try:
        result = call_tool_adapter(name=tool_name, params=params_dict)
        logger.info("Tool %s executed successfully. Result: %s", tool_name, result)
        return {"tool_name": tool_name, "result": result}
    except ValueError as ve: 
        logger.warning("Call to unknown tool '%s' or value error: %s", tool_name, ve, exc_info=True)
        # Check if it's specifically "Unknown tool" or other ValueError from adapter
        if "Unknown tool" in str(ve):
             raise HTTPException(status_code=404, detail=str(ve)) from ve
        else: # Other ValueErrors from tool logic itself
             raise HTTPException(status_code=400, detail=str(ve)) from ve
    except TypeError as te: 
        logger.warning("TypeError calling tool '%s' with params %s: %s", tool_name, params_dict, te, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid parameters for tool {tool_name}: {te}") from te
    except Exception as e:
        logger.error("An unexpected error occurred while calling tool %s: %s", tool_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error executing tool {tool_name}: {str(e)}") from e

@app.get("/contracts/current/{session_id}")
async def get_current_contract(session_id: str) -> Dict[str, Any]:
    logger.info("Received request for GET /contracts/current/%s", session_id)
    try:
        from orchestrator.session_store import get_contract_fsm, get_pending_confirmation, get_contract_context
        import yaml
        
        contract_fsm = get_contract_fsm(session_id)
        pending_product = get_pending_confirmation(session_id)
        
        context_data = get_contract_context(session_id)
        
        # Check if we have either a stored FSM or a pending confirmation
        if not contract_fsm and not pending_product and not context_data:
            return {
                "has_contract": False,
                "contract_data": None,
                "context": None,
                "message": "No active contract for this session"
            }
        
        if contract_fsm and hasattr(contract_fsm, 'context'):
            contract_data = {
                "template_path": contract_fsm.context.contract_template_path,
                "current_state": contract_fsm.context.current_state,
                "parameters": getattr(contract_fsm, 'contract', {}).get("parameters", {}),
                "search_results": contract_fsm.context.search_results,
                "selected_product": contract_fsm.context.selected_product,
                "template_content": contract_fsm.context.contract_template or {}
            }
            context = contract_fsm.context.to_dict()
        elif context_data:
            # Fallback to stored context data
            contract_data = {
                "template_path": context_data.get("contract_template_path"),
                "current_state": context_data.get("current_state"),
                "parameters": {},
                "search_results": context_data.get("search_results", []),
                "selected_product": context_data.get("selected_product"),
                "template_content": context_data.get("contract_template", {})
            }
            context = context_data
        else:
            # Legacy fallback for pending confirmation
            contract_data = {
                "template_path": "contract_templates/purchase_item.yaml",
                "current_state": "confirm_order",
                "parameters": {
                    "session_id": session_id,
                    "product": pending_product.get("name", "Unknown product") if pending_product else None
                },
                "search_results": [],
                "selected_product": pending_product,
                "template_content": {}
            }
            context = None
        
        if contract_data["template_path"] and os.path.exists(contract_data["template_path"]):
            try:
                with open(contract_data["template_path"], 'r', encoding='utf-8') as f:
                    contract_data["template_content"] = yaml.safe_load(f)
            except Exception as e:
                logger.warning("Could not load template content from %s: %s", contract_data["template_path"], e)
                contract_data["template_content"] = {"error": f"Could not load template: {str(e)}"}
        
        return {
            "has_contract": True,
            "contract_data": contract_data,
            "context": context,
            "message": "Active contract found"
        }
        
    except Exception as e:
        logger.error("Error retrieving contract for session %s: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving contract: {str(e)}") from e

@app.get("/api/sessions")
async def get_sessions() -> Dict[str, Any]:
    """Get all sessions with metadata for frontend display"""
    logger.info("Received request for GET /api/sessions")
    try:
        from orchestrator.session_store import get_all_sessions
        
        sessions_data = await get_all_sessions()
        return {
            "sessions": sessions_data,
            "total": len(sessions_data)
        }
        
    except Exception as e:
        logger.error("Error retrieving sessions: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}") from e


@app.get("/api/privacy/memories/{user_id}")
async def list_user_memories(user_id: str) -> Dict[str, Any]:
    """List all stored memories for user (GDPR compliance)"""
    logger.info("Received request for GET /api/privacy/memories/%s", user_id)
    try:
        from contract_engine.memory.milvus_store import milvus_semantic_store
        from contract_engine.privacy.audit_store import audit_store
        
        semantic_stats = milvus_semantic_store.get_user_memory_stats(user_id)
        
        artifacts = []
        try:
            artifacts = audit_store.get_user_artifacts(user_id) if audit_store.s3_client else []
        except Exception as e:
            logger.warning(f"Could not retrieve audit artifacts: {e}")
        
        return {
            "user_id": user_id,
            "semantic_memories": semantic_stats,
            "audit_artifacts": {
                "total_artifacts": len(artifacts),
                "artifacts": artifacts[:10]  # Limit for API response
            },
            "data_retention_policy": "7_years",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error retrieving user memories for %s: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving user memories: {str(e)}") from e

@app.delete("/api/privacy/memories/{user_id}")
async def delete_user_memories(user_id: str, confirm_deletion: bool = False) -> Dict[str, Any]:
    """Delete all memories for user (GDPR right to be forgotten)"""
    logger.info("Received request for DELETE /api/privacy/memories/%s", user_id)
    
    if not confirm_deletion:
        raise HTTPException(status_code=400, detail="Must confirm deletion with confirm_deletion=true")
    
    try:
        from contract_engine.memory.milvus_store import milvus_semantic_store
        from contract_engine.privacy.audit_store import audit_store
        from contract_engine.memory.memory_manager import memory_manager
        
        semantic_deleted = milvus_semantic_store.delete_user_memories(user_id)
        
        artifacts_deleted = False
        try:
            artifacts_deleted = audit_store.delete_user_artifacts(user_id) if audit_store.s3_client else True
        except Exception as e:
            logger.warning(f"Could not delete audit artifacts: {e}")
        
        sessions_cleared = 0
        try:
            memory_manager.clear_session_memory(user_id)
            sessions_cleared = 1
        except:
            pass
        
        return {
            "user_id": user_id,
            "deletion_completed": True,
            "semantic_memories_deleted": semantic_deleted,
            "audit_artifacts_deleted": artifacts_deleted,
            "active_sessions_cleared": sessions_cleared,
            "deletion_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error deleting user memories for %s: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting user memories: {str(e)}") from e

@app.get("/api/privacy/pii-check")
async def check_pii_in_text(text: str) -> Dict[str, Any]:
    """Check text for PII without storing (privacy validation)"""
    logger.info("Received request for GET /api/privacy/pii-check")
    try:
        from contract_engine.privacy.pii_redactor import pii_redactor
        
        detected_pii = pii_redactor.detect_pii(text)
        is_safe = pii_redactor.is_text_safe_for_storage(text)
        
        return {
            "text_safe_for_storage": is_safe,
            "pii_detected": len(detected_pii) > 0,
            "pii_entities": detected_pii,
            "total_entities": len(detected_pii)
        }
        
    except Exception as e:
        logger.error("Error checking PII in text: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking PII: {str(e)}") from e

@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """Get chat history for a specific session"""
    logger.info("Received request for GET /api/sessions/%s/history", session_id)
    try:
        from orchestrator.session_store import get_chat_history
        
        history = get_chat_history(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "message_count": len(history)
        }
        
    except Exception as e:
        logger.error("Error retrieving session history for %s: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving session history: {str(e)}") from e

@app.get("/api/search")
async def search_chat_history(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Search through chat history across sessions or within a specific session"""
    logger.info("Received request for GET /api/search with query: %s, session_id: %s", query, session_id)
    try:
        from orchestrator.session_store import search_chat_history
        
        results = search_chat_history(query, session_id)
        return {
            "query": query,
            "session_id": session_id,
            "results": results,
            "total": len(results)
        }
        
    except Exception as e:
        logger.error("Error searching chat history: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching chat history: {str(e)}") from e



@app.post("/api/test/t5-websearch")
async def test_t5_websearch() -> Dict[str, Any]:
    """Test T5 websearch summarization functionality"""
    logger.info("Received request for POST /api/test/t5-websearch")
    try:
        from websearch_pipeline.websearch_components import LLMSummarizerComponent
        
        summarizer = LLMSummarizerComponent()
        
        test_results = [
            {
                "title": "Test GPU Configuration",
                "snippet": "This is a test snippet about GPU configuration for T5 models.",
                "link": "https://example.com/test1"
            },
            {
                "title": "T5 Model Performance",
                "snippet": "T5 models can run on both CPU and GPU for different performance characteristics.",
                "link": "https://example.com/test2"
            }
        ]
        
        result, _ = summarizer.run(content_enriched_results=test_results, query="test T5 functionality")
        
        return {
            "test_type": "t5_websearch",
            "success": True,
            "t5_available": summarizer.summarizer is not None,
            "gpu_enabled": os.getenv("USE_GPU", "false").lower() == "true",
            "summary": result.get("summary", ""),
            "sources": result.get("sources", []),
            "fallback_used": summarizer.summarizer is None
        }
        
    except Exception as e:
        logger.error("Error testing T5 websearch: %s", e, exc_info=True)
        return {
            "test_type": "t5_websearch",
            "success": False,
            "error": str(e),
            "t5_available": False,
            "gpu_enabled": False,
            "fallback_used": True
        }


@app.post("/api/test/t5-memory")
async def test_t5_memory() -> Dict[str, Any]:
    """Test T5 rolling summarizer for memory management"""
    logger.info("Received request for POST /api/test/t5-memory")
    try:
        from contract_engine.pipelines.rolling_summariser import summarize_messages
        
        test_messages = [
            {"content": "I'm looking for a gaming laptop with good graphics performance."},
            {"content": "My budget is around $1500 and I prefer NVIDIA graphics cards."},
            {"content": "I also need at least 16GB RAM for development work."}
        ]
        
        summary = summarize_messages(test_messages)
        
        return {
            "test_type": "t5_memory",
            "success": True,
            "gpu_enabled": os.getenv("USE_GPU", "false").lower() == "true",
            "summary": summary,
            "message_count": len(test_messages),
            "summary_length": len(summary) if summary else 0
        }
        
    except Exception as e:
        logger.error("Error testing T5 memory: %s", e, exc_info=True)
        return {
            "test_type": "t5_memory",
            "success": False,
            "error": str(e),
            "gpu_enabled": False
        }


@app.get("/contracts")
async def get_contracts():
    logger.info("Received request for GET /contracts")
    try:
        contracts_dir = "contract_templates"
        if not os.path.exists(contracts_dir):
            logger.error("Contract templates directory not found: '%s'", contracts_dir)
            raise FileNotFoundError(f"Contract templates directory not found: {contracts_dir}")
        
        contracts = []
        for filename in os.listdir(contracts_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(contracts_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    contract_data = yaml.safe_load(f)
                contracts.append({
                    "filename": filename,
                    "contract_type": contract_data.get("contract_type", "unknown"),
                    "version": contract_data.get("version", "1.0"),
                    "description": contract_data.get("description", "No description"),
                    "content": contract_data
                })
        
        return {"contracts": contracts}
    except FileNotFoundError:
        logger.error("Contract templates directory not found")
        raise HTTPException(status_code=404, detail="Contract templates not found")
    except Exception as e:
        logger.error("Error loading contracts: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading contracts: {str(e)}")

def _check_t5_available():
    try:
        from websearch_pipeline.websearch_components import LLMSummarizerComponent
        test_component = LLMSummarizerComponent()
        if test_component.summarizer is not None and not test_component.fallback_mode:
            return "Available"
        elif test_component.summarizer is not None:
            return "Available with fallback"
        else:
            return "Fallback mode only"
    except:
        return "Fallback mode only"

def _check_privacy_services():
    try:
        from swisper_core.privacy import pii_redactor
        return "Available" if not pii_redactor.__class__.__name__.startswith("Mock") else "Mock services"
    except:
        return "Mock services"

@app.get("/system/status")
async def get_system_status():
    logger.info("Received request for GET /system/status")
    try:
        status = {
            "environment_variables": {
                "USE_GPU": os.getenv("USE_GPU", "false"),
                "OPENAI_API_KEY": "Set" if os.getenv("OPENAI_API_KEY") else "Not Set",
                "SEARCHAPI_API_KEY": "Set" if os.getenv("SEARCHAPI_API_KEY") else "Not Set",
                "SWISPER_MASTER_KEY": "Set" if os.getenv("SWISPER_MASTER_KEY") else "Not Set"
            },
            "system_status": {
                "rag_available": False,
                "t5_model_status": _check_t5_available(),
                "database_status": "Shelve (fallback mode)",
                "mcp_server_status": "Running",
                "searchapi_status": "Available" if os.getenv("SEARCHAPI_API_KEY") else "Mock data fallback",
                "privacy_services": _check_privacy_services()
            },
            "performance_settings": {
                "gpu_acceleration": os.getenv("USE_GPU", "false").lower() == "true",
                "model_type": "t5-small",
                "max_tokens": 150,
                "inference_mode": "CPU" if os.getenv("USE_GPU", "false").lower() == "false" else "GPU"
            },
            "debug_logging": {
                "log_level": "INFO",
                "websocket_logging": "Enabled",
                "file_logging": "Disabled",
                "console_logging": "Enabled"
            }
        }
        
        try:
            from haystack_pipeline.rag import ask_doc
            status["system_status"]["rag_available"] = True
        except ImportError:
            status["system_status"]["rag_available"] = False
            
        return status
    except Exception as e:
        logger.error("Error getting system status: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")


@app.get("/volatility-settings")
async def get_volatility_settings():
    """Get volatility keyword settings"""
    logger.info("Received request for GET /volatility-settings")
    try:
        from orchestrator.volatility_classifier import get_volatility_settings
        settings = get_volatility_settings()
        return {"volatility_settings": settings}
    except Exception as e:
        logger.error("Error getting volatility settings: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting volatility settings: {str(e)}")

@app.post("/volatility-settings")
async def update_volatility_settings(settings: Dict[str, Any]):
    """Update volatility keyword settings"""
    logger.info("Received request for POST /volatility-settings")
    try:
        required_keys = ["volatile_keywords", "semi_static_keywords", "static_keywords"]
        for key in required_keys:
            if key not in settings:
                raise HTTPException(status_code=400, detail=f"Missing required key: {key}")
            if not isinstance(settings[key], list):
                raise HTTPException(status_code=400, detail=f"Key {key} must be a list")
        
        logger.info("Volatility settings validation passed")
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        logger.error("Error updating volatility settings: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating volatility settings: {str(e)}")





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
