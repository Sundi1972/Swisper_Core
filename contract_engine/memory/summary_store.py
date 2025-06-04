import logging
from typing import List, Dict, Any, Optional
import time
import json
from .redis_client import redis_client
from .message_serializer import MessageSerializer
try:
    from orchestrator.postgres_session_store import PostgresSessionStore
    postgres_session_store = PostgresSessionStore()
except (ImportError, Exception):
    postgres_session_store = None

class SummaryStore:
    """Redis→PostgreSQL persistence for rolling session summaries"""
    
    def __init__(self, redis_ttl: int = 86400):
        self.redis_ttl = redis_ttl
        self.serializer = MessageSerializer()
        self.postgres_store = postgres_session_store
        self.logger = logging.getLogger(__name__)
    
    def _get_summary_key(self, session_id: str) -> str:
        """Generate Redis key for session summary"""
        return f"summary:{session_id}"
    
    def _get_summary_list_key(self, session_id: str) -> str:
        """Generate Redis key for summary list"""
        return f"summary_list:{session_id}"
    
    def add_summary(self, session_id: str, summary_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add new summary to rolling summary store"""
        try:
            client = redis_client.get_client()
            summary_key = self._get_summary_key(session_id)
            list_key = self._get_summary_list_key(session_id)
            
            summary_entry = {
                "text": summary_text,
                "timestamp": int(time.time()),
                "metadata": metadata or {}
            }
            
            serialized_summary = self.serializer.serialize_message(summary_entry)
            
            pipe = client.pipeline()
            pipe.rpush(list_key, serialized_summary)
            pipe.expire(list_key, self.redis_ttl)
            
            pipe.set(summary_key, summary_text)
            pipe.expire(summary_key, self.redis_ttl)
            
            pipe.execute()
            
            self._persist_to_postgres(session_id, summary_text)
            self._manage_summary_count(session_id)
            
            self.logger.debug(f"Added summary for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add summary: {e}")
            return False
    
    def get_current_summary(self, session_id: str) -> Optional[str]:
        """Get current consolidated summary"""
        try:
            client = redis_client.get_client()
            summary_key = self._get_summary_key(session_id)
            
            summary = client.get(summary_key)
            if summary:
                return summary.decode('utf-8')
            
            return self._load_from_postgres(session_id)
            
        except Exception as e:
            self.logger.error(f"Failed to get current summary: {e}")
            return None
    
    def get_summary_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary history with timestamps"""
        try:
            client = redis_client.get_client()
            list_key = self._get_summary_list_key(session_id)
            
            serialized_summaries = client.lrange(list_key, -limit, -1)
            
            summaries = []
            for serialized in serialized_summaries:
                try:
                    summary = self.serializer.deserialize_message(serialized.decode('utf-8'))
                    summaries.append(summary)
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize summary: {e}")
                    continue
            
            return summaries
            
        except Exception as e:
            self.logger.error(f"Failed to get summary history: {e}")
            return []
    
    def _persist_to_postgres(self, session_id: str, summary_text: str):
        """Persist summary to PostgreSQL"""
        try:
            if postgres_session_store is None:
                self.logger.warning("PostgreSQL session store not available, skipping persistence")
                return
            
            if not hasattr(postgres_session_store, 'db_manager'):
                self.logger.warning("PostgreSQL db_manager not available, skipping persistence")
                return
                
            with postgres_session_store.db_manager.get_session() as db_session:
                session = db_session.query(postgres_session_store.SwisperSession).filter(
                    postgres_session_store.SwisperSession.session_id == session_id
                ).first()
                if session:
                    session.short_summary = summary_text
                    db_session.commit()
                    self.logger.debug(f"Persisted summary to PostgreSQL for session {session_id}")
                else:
                    self.logger.warning(f"Session {session_id} not found in PostgreSQL for summary update")
                
        except Exception as e:
            self.logger.error(f"Failed to persist summary to PostgreSQL: {e}")
    
    def _load_from_postgres(self, session_id: str) -> Optional[str]:
        """Load summary from PostgreSQL as fallback"""
        try:
            if postgres_session_store is None:
                self.logger.warning("PostgreSQL session store not available, skipping load")
                return None
            
            if not hasattr(postgres_session_store, 'db_manager'):
                self.logger.warning("PostgreSQL db_manager not available, skipping load")
                return None
                
            with postgres_session_store.db_manager.get_session() as db_session:
                session = db_session.query(postgres_session_store.SwisperSession).filter(
                    postgres_session_store.SwisperSession.session_id == session_id
                ).first()
                if session and session.short_summary:
                    summary = session.short_summary
                    
                    client = redis_client.get_client()
                    summary_key = self._get_summary_key(session_id)
                    client.setex(summary_key, self.redis_ttl, summary)
                    
                    return summary
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load summary from PostgreSQL: {e}")
            return None
    
    def _manage_summary_count(self, session_id: str, max_summaries: int = 8):
        """Manage summary count and merge old summaries"""
        try:
            client = redis_client.get_client()
            list_key = self._get_summary_list_key(session_id)
            
            summary_count = client.llen(list_key)
            
            if summary_count > max_summaries:
                summaries_to_merge = []
                for _ in range(3):
                    oldest = client.lpop(list_key)
                    if oldest:
                        try:
                            summary_data = self.serializer.deserialize_message(oldest.decode('utf-8'))
                            summaries_to_merge.append(summary_data["text"])
                        except Exception as e:
                            self.logger.warning(f"Failed to deserialize summary for merging: {e}")
                
                if summaries_to_merge:
                    merged_summary = self._merge_summaries(summaries_to_merge)
                    self.add_summary(session_id, merged_summary, {"type": "merged"})
                    
                self.logger.debug(f"Merged {len(summaries_to_merge)} old summaries for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to manage summary count: {e}")
    
    def _merge_summaries(self, summaries: List[str]) -> str:
        """Simple summary merging logic"""
        if not summaries:
            return ""
        
        if len(summaries) == 1:
            return summaries[0]
        
        combined = " ".join(summaries)
        if len(combined) > 500:
            return combined[:500] + "..."
        
        return combined
    
    def get_summary_stats(self, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for monitoring"""
        try:
            client = redis_client.get_client()
            list_key = self._get_summary_list_key(session_id)
            summary_key = self._get_summary_key(session_id)
            
            return {
                "summary_count": client.llen(list_key),
                "current_summary_length": len(self.get_current_summary(session_id) or ""),
                "redis_ttl": client.ttl(summary_key),
                "last_updated": int(time.time())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get summary stats: {e}")
            return {}
    
    def clear_summaries(self, session_id: str) -> bool:
        """Clear all summaries for session"""
        try:
            client = redis_client.get_client()
            summary_key = self._get_summary_key(session_id)
            list_key = self._get_summary_list_key(session_id)
            
            pipe = client.pipeline()
            pipe.delete(summary_key)
            pipe.delete(list_key)
            pipe.execute()
            
            self.logger.debug(f"Cleared summaries for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear summaries: {e}")
            return False
