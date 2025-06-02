# swisper/gateway/main.py
import logging
import os
import json # Added import
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict # Added Dict here

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

app = FastAPI()

# CORS configuration
# origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Add other origins as needed, e.g., from environment variables
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to tools.json - Assuming WORKDIR is /app (swisper/) for Docker execution
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

# OPENAI_API_KEY check (optional, if gateway itself doesn't use it directly)
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#    logger.warning("OPENAI_API_KEY environment variable not set. This might be an issue for downstream components.")

if __name__ == "__main__":
    # This block is for local development/debugging without Docker.
    # Ensure PYTHONPATH includes the 'swisper' directory root when running this directly.
    # Example: PYTHONPATH=$PYTHONPATH:$(pwd) python gateway/main.py (if in swisper dir)
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
        # Correct path construction assuming this file (main.py) is in swisper/gateway/
        # and TOOLS_JSON_PATH is relative to swisper/ root.
        # Docker WORKDIR is /app (which is swisper/), so TOOLS_JSON_PATH should be fine as is.
        # For local execution: if running from swisper/gateway/, need to adjust.
        # If running 'python -m gateway.main' from 'swisper/', path is fine.
        # If running 'python main.py' from 'swisper/gateway', path needs '../'.
        # The Docker setup is the primary target, so TOOLS_JSON_PATH = "orchestrator/tool_registry/tools.json" is best.
        
        # Simple check for local dev if path needs adjustment (basic heuristic)
        # This is a bit of a hack for local dev; ideally, path management is more robust.
        current_dir = os.getcwd()
        path_to_check = TOOLS_JSON_PATH
        if "swisper/gateway" in current_dir.replace("\\", "/"): # If CWD is gateway
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
