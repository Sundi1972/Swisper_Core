import os
import shelve
import atexit
import logging
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
    history.append(message)
    sessions[session_id]["chat_history"] = history
    logger.debug(f"Added message to history for session {session_id}. New history length: {len(history)}")

def save_session(session_id: str):
    if hasattr(sessions, 'sync') and session_id in sessions:
        try:
            sessions.sync()
            logger.debug(f"Session {session_id} synced to disk.")
        except Exception as e:
            logger.error(f"Error syncing session {session_id} to disk: {e}", exc_info=True)
    elif not hasattr(sessions, 'sync'):
        logger.warning("Shelve object does not have 'sync' method. Sessions may not be persisted if shelve failed to initialize.")

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
