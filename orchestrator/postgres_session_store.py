import logging
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import db_manager, SwisperSession

logger = logging.getLogger(__name__)

def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"Session {session_id} not found when trying to get chat history. Returning empty list.")
                return []
            
            return session.chat_history or []
            
    except Exception as e:
        logger.error(f"Error getting chat history for session {session_id}: {e}", exc_info=True)
        return []

def add_chat_message(session_id: str, message: Dict[str, str]):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"Session {session_id} not found when trying to add chat message. Creating new session.")
                session = SwisperSession(
                    session_id=session_id,
                    chat_history=[],
                    session_metadata={}
                )
                db_session.add(session)
            
            message_with_timestamp = {
                **message, 
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            chat_history = session.chat_history or []
            chat_history.append(message_with_timestamp)
            session.chat_history = chat_history
            session.message_count = len(chat_history)
            session.updated_at = datetime.datetime.now()
            
            if message.get("role") == "user":
                session.last_user_text = message.get("content", "")
                session.last_user_ts = datetime.datetime.now()
            
            db_session.commit()
            logger.debug(f"Added message to history for session {session_id}. New history length: {len(chat_history)}")
            
    except Exception as e:
        logger.error(f"Error adding chat message to session {session_id}: {e}", exc_info=True)
        if 'db_session' in locals():
            db_session.rollback()

def save_session(session_id: str):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if session:
                chat_history = session.chat_history or []
                
                last_user_msg = None
                last_msg_time = None
                
                for msg in reversed(chat_history):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "")
                        last_msg_time = msg.get("timestamp")
                        break
                
                session.last_user_text = last_user_msg
                if last_msg_time:
                    try:
                        session.last_user_ts = datetime.datetime.fromisoformat(last_msg_time)
                    except:
                        session.last_user_ts = datetime.datetime.now()
                
                session.updated_at = datetime.datetime.now()
                db_session.commit()
                logger.debug(f"Session {session_id} saved successfully")
            else:
                logger.warning(f"Attempted to save non-existent session: {session_id}")
                
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}", exc_info=True)
        if 'db_session' in locals():
            db_session.rollback()

def set_pending_confirmation(session_id: str, product_details: Optional[Dict[str, Any]]):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                session = SwisperSession(
                    session_id=session_id,
                    chat_history=[],
                    session_metadata={}
                )
                db_session.add(session)
            
            metadata = session.session_metadata or {}
            metadata['pending_confirmation_product'] = product_details
            session.session_metadata = metadata
            session.has_contract = bool(product_details)
            session.updated_at = datetime.datetime.now()
            
            db_session.commit()
            
            product_name = product_details.get('name') if product_details else 'None'
            logger.info(f"Session {session_id}: Set pending confirmation for product: {product_name}")
            
    except Exception as e:
        logger.error(f"Error setting pending confirmation for session {session_id}: {e}", exc_info=True)
        if 'db_session' in locals():
            db_session.rollback()

def get_pending_confirmation(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                return None
            
            metadata = session.session_metadata or {}
            product = metadata.get('pending_confirmation_product')
            product_name = product.get('name') if product else 'None'
            logger.debug(f"Session {session_id}: Retrieved pending confirmation product: {product_name}")
            return product
            
    except Exception as e:
        logger.error(f"Error getting pending confirmation for session {session_id}: {e}", exc_info=True)
        return None

def clear_pending_confirmation(session_id: str):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if session:
                metadata = session.session_metadata or {}
                if 'pending_confirmation_product' in metadata:
                    del metadata['pending_confirmation_product']
                    session.session_metadata = metadata
                    session.has_contract = False
                    session.updated_at = datetime.datetime.now()
                    db_session.commit()
                    logger.info(f"Session {session_id}: Cleared pending confirmation.")
                    
    except Exception as e:
        logger.error(f"Error clearing pending confirmation for session {session_id}: {e}", exc_info=True)
        if 'db_session' in locals():
            db_session.rollback()

def set_contract_fsm(session_id: str, fsm):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                session = SwisperSession(
                    session_id=session_id,
                    chat_history=[],
                    session_metadata={}
                )
                db_session.add(session)
            
            metadata = session.session_metadata or {}
            
            if fsm and hasattr(fsm, 'context'):
                context_dict = fsm.context.to_dict()
                if hasattr(fsm, 'contract_template'):
                    context_dict['contract_template'] = fsm.contract_template
                elif hasattr(fsm, 'contract') and hasattr(fsm.contract, 'template_path'):
                    context_dict['contract_template'] = fsm.contract.template_path
                else:
                    context_dict['contract_template'] = 'contract_templates/purchase_item.yaml'
                metadata['contract_context'] = context_dict
            else:
                metadata['contract_context'] = None
            
            session.session_metadata = metadata
            session.updated_at = datetime.datetime.now()
            db_session.commit()
            
            logger.info(f"Session {session_id}: Stored contract FSM state and context.")
            
    except Exception as e:
        logger.error(f"Error setting contract FSM for session {session_id}: {e}", exc_info=True)
        if 'db_session' in locals():
            db_session.rollback()

def get_contract_fsm(session_id: str):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                return None
            
            metadata = session.session_metadata or {}
            context_data = metadata.get('contract_context')
            
            if context_data:
                try:
                    from contract_engine.contract_engine import ContractStateMachine
                    from contract_engine.context import SwisperContext
                    
                    contract_template = context_data.get('contract_template', 'contract_templates/purchase_item.yaml')
                    fsm = ContractStateMachine(contract_template)
                    fsm.context = SwisperContext.from_dict(context_data)
                    
                    logger.info(f"Reconstructed contract FSM for session {session_id} from context")
                    return fsm
                except Exception as e:
                    logger.error(f"Error reconstructing FSM for session {session_id}: {e}")
                    return None
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting contract FSM for session {session_id}: {e}", exc_info=True)
        return None

def get_contract_context(session_id: str):
    try:
        with db_manager.get_session() as db_session:
            session = db_session.query(SwisperSession).filter(
                SwisperSession.session_id == session_id
            ).first()
            
            if not session:
                return None
            
            metadata = session.session_metadata or {}
            return metadata.get('contract_context')
            
    except Exception as e:
        logger.error(f"Error getting contract context for session {session_id}: {e}", exc_info=True)
        return None

async def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    try:
        with db_manager.get_session() as db_session:
            sessions = db_session.query(SwisperSession).order_by(
                desc(SwisperSession.updated_at)
            ).all()
            
            session_list = {}
            
            for session in sessions:
                title = session.title
                if not title and session.chat_history:
                    from .session_store import generate_session_title
                    title = await generate_session_title(session.chat_history)
                    session.title = title
                    db_session.commit()
                elif not title:
                    title = "Untitled Session"
                
                last_user_message = session.last_user_text or ""
                if last_user_message and len(last_user_message) > 48:
                    truncated = last_user_message[:48]
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        last_user_message = truncated[:last_space] + "…"
                    else:
                        last_user_message = truncated + "…"
                
                formatted_time = ""
                if session.last_user_ts:
                    formatted_time = session.last_user_ts.strftime("%d %b, %H:%M")
                
                session_list[session.session_id] = {
                    "id": session.session_id,
                    "title": title,
                    "last_user_message": last_user_message or "No messages yet",
                    "message_count": session.message_count,
                    "last_updated": formatted_time,
                    "has_contract": session.has_contract
                }
            
            logger.debug(f"Retrieved {len(session_list)} sessions for frontend display")
            return session_list
            
    except Exception as e:
        logger.error(f"Error retrieving all sessions: {e}", exc_info=True)
        return {}

def search_chat_history(query: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with db_manager.get_session() as db_session:
            query_builder = db_session.query(SwisperSession)
            
            if session_id:
                query_builder = query_builder.filter(SwisperSession.session_id == session_id)
            
            sessions = query_builder.all()
            results = []
            
            for session in sessions:
                chat_history = session.chat_history or []
                for i, message in enumerate(chat_history):
                    content = message.get("content", "").lower()
                    if query.lower() in content:
                        results.append({
                            "session_id": session.session_id,
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
