# gateway/main.py
import logging
import os
import json # Added import
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Any, Dict, Optional # Added Dict here

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware

# Attempt to import project modules.
# This relies on PYTHONPATH being set correctly (e.g., to /app in Docker).
try:
    from prompt_preprocessor import clean_and_tag
    from orchestrator.core import handle as orchestrator_handle
    from tool_adapter.mock_google import route as call_tool_adapter # Added for /call endpoint
except ImportError as e:
    # Log an error and re-raise to prevent app startup if dependencies are missing.
    # This helps in diagnosing PYTHONPATH or module availability issues early.
    logging.basicConfig(level="ERROR", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger(__name__)
    logger.error("Failed to import project modules. Ensure PYTHONPATH is set correctly. Error: %s", e, exc_info=True)
    raise


# Logging setup
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
numeric_log_level = getattr(logging, log_level_str, logging.INFO) # Convert string level to numeric
logging.basicConfig(
    level=numeric_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from .log_handler import log_buffer, WebSocketLogHandler

app = FastAPI()

# CORS configuration
origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

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
        orchestrator_response = await orchestrator_handle(messages=payload.messages, session_id=payload.session_id)
        logger.info("Orchestrator response for session %s: %s", payload.session_id, orchestrator_response.get('reply'))
    except Exception as e:
        logger.error("Error in orchestrator for session %s: %s", payload.session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error in orchestrator.") from e
    
    if not isinstance(orchestrator_response, dict):
        logger.error("Orchestrator returned non-dict response: %s for session %s", orchestrator_response, payload.session_id)
        raise HTTPException(status_code=500, detail="Invalid response format from orchestrator.")

    return orchestrator_response

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

if __name__ == "__main__":
    # This block is for local development/debugging without Docker.
    # Ensure PYTHONPATH includes the repository root when running this directly.
    # Example: PYTHONPATH=$PYTHONPATH:$(pwd) python gateway/main.py (if in repo root)
    # or set it in your IDE's run configuration.
    logger.info("Starting Uvicorn server for local development...")
    import uvicorn
    # Note: uvicorn.run(app, ...) is more robust than uvicorn.run("main:app", ...) for some import scenarios.
    # It directly uses the 'app' instance from the current module.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=log_level_str.lower())


@app.get("/tools")
async def get_tools():
    logger.info("Received request for GET /tools")
    try:
        # Correct path construction assuming this file (main.py) is in gateway/
        # and TOOLS_JSON_PATH is relative to repository root.
        # Docker WORKDIR is /app (which is the repo root), so TOOLS_JSON_PATH should be fine as is.
        # For local execution: if running from gateway/, need to adjust.
        # If running 'python -m gateway.main' from repo root, path is fine.
        # If running 'python main.py' from gateway/, path needs '../'.
        # The Docker setup is the primary target, so TOOLS_JSON_PATH = "orchestrator/tool_registry/tools.json" is best.
        
        # Simple check for local dev if path needs adjustment (basic heuristic)
        # This is a bit of a hack for local dev; ideally, path management is more robust.
        current_dir = os.getcwd()
        path_to_check = TOOLS_JSON_PATH
        if "gateway" in current_dir.replace("\\", "/").split("/")[-1]: # If CWD is gateway
             # This check is a bit fragile. For robust local dev, use absolute paths or env vars for config.
             # Or ensure running from project root.
            alt_path = os.path.join("..", TOOLS_JSON_PATH)
            if os.path.exists(alt_path):
                 path_to_check = alt_path

        if not os.path.exists(path_to_check):
            # Fallback if the above logic didn't find it, try the direct path (for Docker)
            if os.path.exists(TOOLS_JSON_PATH):
                 path_to_check = TOOLS_JSON_PATH
            else:
                logger.error("Tools file not found. Checked: '%s' and '%s'", path_to_check, TOOLS_JSON_PATH)
                raise FileNotFoundError # Raise to be caught by the except block

        with open(path_to_check, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
        return tools_data
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tools definition file not found.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Error reading tools definition.") from exc
    except Exception as e:
        logger.error("An unexpected error occurred while fetching tools: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching tools.") from e


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
