import os
import shelve
import atexit
import logging
import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Ensure the shelve data folder exists
os.makedirs("db_data", exist_ok=True)
DB_PATH = "db_data/orchestrator_sessions"  # Don't include .db extension — shelve adds it

try:
    sessions = shelve.open(DB_PATH, writeback=True)
    atexit.register(sessions.close)
    logger.info(f"Session store initialized at {DB_PATH}")
except Exception as e:
    logger.error(f"Failed to initialize session store at {DB_PATH}: {e}", exc_info=True)
    sessions = {}  # fallback

# REMOVED: get_contract_engine and its import of ContractStateMachine

def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    if session_id not in sessions:
        logger.warning(f"Session {session_id} not found when trying to get chat history. Returning empty list.")
        return []
    return sessions[session_id].get("chat_history", [])

def add_chat_message(session_id: str, message: Dict[str, str]):
    if session_id not in sessions:
        # Initialize session if it doesn't exist.
        logger.warning(f"Session {session_id} not found when trying to add chat message. Initializing session.")
        sessions[session_id] = {"chat_history": []} # Initialize with at least chat_history
    
    history = sessions[session_id].get("chat_history", [])
    message_with_timestamp = {**message, "timestamp": datetime.datetime.now().isoformat()}
    history.append(message_with_timestamp)
    sessions[session_id]["chat_history"] = history
    logger.debug(f"Added message to history for session {session_id}. New history length: {len(history)}")

def save_session(session_id: str):
    try:
        if session_id in sessions:
            session_data = sessions[session_id]
            chat_history = session_data.get("chat_history", [])
            
            last_user_msg = None
            last_msg_time = None
            
            for msg in reversed(chat_history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    last_msg_time = msg.get("timestamp")
                    break
            
            session_data["last_user_message"] = last_user_msg
            session_data["last_message_time"] = last_msg_time
            
            sessions[session_id] = session_data
            
            if hasattr(sessions, 'sync'):
                sessions.sync()
                logger.debug(f"Session {session_id} synced to disk.")
        else:
            logger.warning(f"Attempted to save non-existent session: {session_id}")
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}", exc_info=True)

def set_pending_confirmation(session_id: str, product_details: Optional[Dict[str, Any]]):
    if session_id not in sessions:
        sessions[session_id] = {"chat_history": []} # Initialize session if not present, ensuring chat_history key exists
    sessions[session_id]['pending_confirmation_product'] = product_details
    product_name = product_details.get('name') if product_details else 'None'
    logger.info(f"Session {session_id}: Set pending confirmation for product: {product_name}")
    save_session(session_id)

def get_pending_confirmation(session_id: str) -> Optional[Dict[str, Any]]:
    if session_id not in sessions:
        return None
    product = sessions[session_id].get('pending_confirmation_product')
    product_name = product.get('name') if product else 'None'
    logger.debug(f"Session {session_id}: Retrieved pending confirmation product: {product_name}")
    return product

def clear_pending_confirmation(session_id: str):
    if session_id in sessions and 'pending_confirmation_product' in sessions[session_id]:
        del sessions[session_id]['pending_confirmation_product']
        logger.info(f"Session {session_id}: Cleared pending confirmation.")
        save_session(session_id)

def set_contract_fsm(session_id: str, fsm):
    """Store contract FSM state and context for multi-step interactions"""
    if not hasattr(sessions, '_contract_fsms'):
        sessions._contract_fsms = {}
    if not hasattr(sessions, '_contract_contexts'):
        sessions._contract_contexts = {}
    
    sessions._contract_fsms[session_id] = fsm
    
    if fsm and hasattr(fsm, 'context'):
        sessions._contract_contexts[session_id] = fsm.context.to_dict()
    else:
        sessions._contract_contexts[session_id] = None
        
    logger.info(f"Session {session_id}: Stored contract FSM state and context.")

def get_contract_fsm(session_id: str):
    """Retrieve stored contract FSM state and restore context"""
    if hasattr(sessions, '_contract_fsms'):
        fsm = sessions._contract_fsms.get(session_id)
        if fsm and hasattr(sessions, '_contract_contexts'):
            context_data = sessions._contract_contexts.get(session_id)
            if context_data:
                from contract_engine.context import SwisperContext
                fsm.context = SwisperContext.from_dict(context_data)
        return fsm
    return None

def get_contract_context(session_id: str):
    """Retrieve stored contract context as dictionary"""
    if hasattr(sessions, '_contract_contexts'):
        return sessions._contract_contexts.get(session_id)
    return None

async def generate_session_title(chat_history: List[Dict[str, str]]) -> str:
    """Generate a descriptive title for a session using LLM analysis of first 3 messages or 1000 tokens"""
    try:
        from .llm_adapter import get_llm_adapter
        
        messages_for_title = []
        total_tokens = 0
        
        for i, msg in enumerate(chat_history[:6]):  # Max 3 user + 3 assistant messages
            content = msg.get("content", "")
            msg_tokens = len(content) // 4
            
            if total_tokens + msg_tokens > 1000 or len(messages_for_title) >= 6:
                break
                
            messages_for_title.append(msg)
            total_tokens += msg_tokens
        
        if not messages_for_title:
            return "Untitled Session"
        
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" 
            for msg in messages_for_title
        ])
        
        title_prompt = f"""You are a helpful assistant. Summarize this chat session with a short descriptive title that helps the user remember what this session was about. Your answer must be:
- A maximum of 24 characters
- Descriptive but concise
- No quotation marks or punctuation at the end

Return only the title string.

Conversation:
{conversation_text}"""
        
        llm_adapter = get_llm_adapter()
        response = llm_adapter.chat_completion([
            {"role": "user", "content": title_prompt}
        ])
        
        title = response.strip()[:24]  # Ensure max 24 chars
        return title if title else "Untitled Session"
        
    except Exception as e:
        logger.error(f"Error generating session title: {e}", exc_info=True)
        return "Untitled Session"

async def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    """Get all sessions with metadata for frontend display"""
    try:
        if not hasattr(sessions, 'keys'):
            logger.warning("Sessions object does not have keys method. Returning empty dict.")
            return {}
        
        session_list = {}
        for session_id in sessions.keys():
            session_data = sessions[session_id]
            chat_history = session_data.get("chat_history", [])
            
            title = session_data.get("title")
            if not title and chat_history:
                title = await generate_session_title(chat_history)
                session_data["title"] = title
                sessions[session_id] = session_data
            elif not title:
                title = "Untitled Session"
            
            last_user_message = session_data.get("last_user_message", "")
            if last_user_message:
                if len(last_user_message) > 48:
                    truncated = last_user_message[:48]
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        last_user_message = truncated[:last_space] + "…"
                    else:
                        last_user_message = truncated + "…"
            
            last_message_time = session_data.get("last_message_time")
            formatted_time = ""
            if last_message_time:
                try:
                    dt = datetime.datetime.fromisoformat(last_message_time)
                    formatted_time = dt.strftime("%d %b, %H:%M")
                except:
                    formatted_time = ""
            
            session_list[session_id] = {
                "id": session_id,
                "title": title,
                "last_user_message": last_user_message,
                "message_count": len(chat_history),
                "last_updated": formatted_time,
                "has_contract": bool(session_data.get("pending_confirmation_product"))
            }
        
        logger.debug(f"Retrieved {len(session_list)} sessions for frontend display")
        return session_list
        
    except Exception as e:
        logger.error(f"Error retrieving all sessions: {e}", exc_info=True)
        return {}

def search_chat_history(query: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search through chat history across sessions or within a specific session"""
    try:
        if not hasattr(sessions, 'keys'):
            logger.warning("Sessions object does not have keys method. Returning empty list.")
            return []
        
        results = []
        search_sessions = [session_id] if session_id else list(sessions.keys())
        
        for sid in search_sessions:
            if sid not in sessions:
                continue
                
            chat_history = sessions[sid].get("chat_history", [])
            for i, message in enumerate(chat_history):
                content = message.get("content", "").lower()
                if query.lower() in content:
                    results.append({
                        "session_id": sid,
                        "message_index": i,
                        "role": message.get("role", "unknown"),
                        "content": message.get("content", ""),
                        "timestamp": message.get("timestamp"),
                        "preview": content[:200] + ("..." if len(content) > 200 else "")
                    })
        
        logger.debug(f"Search for '{query}' found {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error searching chat history: {e}", exc_info=True)
        return []
