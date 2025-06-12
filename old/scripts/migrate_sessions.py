#!/usr/bin/env python3

import os
import sys
import shelve
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.database import db_manager, SwisperSession
from swisper_core import get_logger

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

def migrate_shelve_to_postgres():
    shelve_path = "db_data/orchestrator_sessions"
    
    if not os.path.exists(f"{shelve_path}.db") and not os.path.exists(f"{shelve_path}.dat"):
        logger.info("No existing shelve database found, skipping migration")
        return
    
    try:
        with shelve.open(shelve_path, flag='r') as shelve_sessions:
            logger.info(f"Found {len(shelve_sessions)} sessions to migrate")
            
            with db_manager.get_session() as db_session:
                for session_id, session_data in shelve_sessions.items():
                    existing = db_session.query(SwisperSession).filter(
                        SwisperSession.session_id == session_id
                    ).first()
                    
                    if existing:
                        logger.info(f"Session {session_id} already exists, skipping")
                        continue
                    
                    pg_session = SwisperSession(
                        session_id=session_id,
                        title=session_data.get('title'),
                        chat_history=session_data.get('chat_history', []),
                        session_metadata=session_data,
                        message_count=len(session_data.get('chat_history', [])),
                        last_user_text=session_data.get('last_user_message'),
                        has_contract=bool(session_data.get('pending_confirmation_product'))
                    )
                    
                    db_session.add(pg_session)
                    logger.info(f"Migrated session {session_id}")
                
                db_session.commit()
                logger.info("Migration completed successfully")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    migrate_shelve_to_postgres()
