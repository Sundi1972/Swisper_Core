from typing import Dict, List, Any, Optional
import time
from .buffer_store import BufferStore
from .summary_store import SummaryStore
from .token_counter import TokenCounter
from .redis_client import redis_client
from swisper_core import SwisperContext, get_logger
from .milvus_store import milvus_semantic_store

class MemoryManager:
    """Unified memory management interface for orchestrator integration"""
    
    def __init__(self, 
                 summary_trigger_tokens: int = 3000,
                 max_buffer_tokens: int = 4000,
                 max_buffer_messages: int = 30):
        self.buffer_store = BufferStore(
            max_messages=max_buffer_messages,
            max_tokens=max_buffer_tokens
        )
        self.summary_store = SummaryStore()
        self.token_counter = TokenCounter()
        self.summary_trigger_tokens = summary_trigger_tokens
        self.logger = get_logger(__name__)
        
        self._session_configs = {}
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add message to memory with automatic summarization"""
        try:
            success = self.buffer_store.add_message(session_id, message)
            
            if success:
                self._check_and_trigger_summary(session_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to add message to memory: {e}")
            return False
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get complete memory context for session"""
        try:
            buffer_messages = self.buffer_store.get_messages(session_id)
            current_summary = self.summary_store.get_current_summary(session_id)
            buffer_info = self.buffer_store.get_buffer_info(session_id)
            
            return {
                "buffer_messages": buffer_messages,
                "current_summary": current_summary,
                "buffer_info": buffer_info,
                "total_tokens": buffer_info.get("total_tokens", 0),
                "message_count": buffer_info.get("message_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory context: {e}")
            return {
                "buffer_messages": [],
                "current_summary": None,
                "buffer_info": {},
                "total_tokens": 0,
                "message_count": 0
            }
    
    def save_context(self, session_id: str, context: SwisperContext) -> bool:
        """Save SwisperContext to memory (compatibility with existing session store)"""
        try:
            context_message = {
                "type": "context_update",
                "content": context.to_dict(),
                "timestamp": int(time.time())
            }
            
            return self.add_message(session_id, context_message)
            
        except Exception as e:
            self.logger.error(f"Failed to save context to memory: {e}")
            return False
    
    def _check_and_trigger_summary(self, session_id: str):
        """Check if summarization should be triggered"""
        try:
            config = self._get_session_config(session_id)
            trigger_threshold = config.get("summary_trigger_tokens", self.summary_trigger_tokens)
            
            if self.buffer_store.should_trigger_summary(session_id, trigger_threshold):
                self._trigger_summarization(session_id)
                
        except Exception as e:
            self.logger.error(f"Failed to check summary trigger: {e}")
    
    def _trigger_summarization(self, session_id: str):
        """Trigger summarization of oldest messages"""
        try:
            messages = self.buffer_store.get_messages(session_id)
            
            if len(messages) < 10:
                return
            
            messages_to_summarize = messages[:10]
            
            summary_text = self._create_summary(messages_to_summarize)
            
            if summary_text:
                self.summary_store.add_summary(session_id, summary_text)
                
                for _ in range(len(messages_to_summarize)):
                    client = redis_client.get_client()
                    buffer_key = self.buffer_store._get_buffer_key(session_id)
                    client.lpop(buffer_key)
                
                self.logger.info(f"Summarized {len(messages_to_summarize)} messages for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to trigger summarization: {e}")
    
    def _create_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create summary from messages using T5-based RollingSummariser"""
        try:
            from contract_engine.pipelines.rolling_summariser import summarize_messages
            return summarize_messages(messages)
        except Exception as e:
            self.logger.error(f"Failed to create T5 summary: {e}")
            if not messages:
                return ""
            
            content_parts = []
            for msg in messages:
                if isinstance(msg, dict) and "content" in msg:
                    content_parts.append(str(msg["content"]))
            
            combined_content = " ".join(content_parts)
            
            if len(combined_content) > 200:
                return combined_content[:200] + "..."
            
            return combined_content
    
    def set_session_config(self, session_id: str, config: Dict[str, Any]):
        """Set per-session memory configuration"""
        self._session_configs[session_id] = config
        self.logger.debug(f"Updated memory config for session {session_id}: {config}")
    
    def _get_session_config(self, session_id: str) -> Dict[str, Any]:
        """Get session-specific configuration with defaults"""
        return self._session_configs.get(session_id, {})
    
    def get_memory_stats(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            buffer_info = self.buffer_store.get_buffer_info(session_id)
            summary_stats = self.summary_store.get_summary_stats(session_id)
            redis_memory = redis_client.get_memory_usage()
            
            return {
                "buffer": buffer_info,
                "summary": summary_stats,
                "redis_memory": redis_memory,
                "session_config": self._get_session_config(session_id),
                "is_redis_available": redis_client.is_available()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    def clear_session_memory(self, session_id: str) -> bool:
        """Clear all memory for session"""
        try:
            buffer_cleared = self.buffer_store.clear_buffer(session_id)
            summary_cleared = self.summary_store.clear_summaries(session_id)
            
            if session_id in self._session_configs:
                del self._session_configs[session_id]
            
            success = buffer_cleared and summary_cleared
            self.logger.info(f"Cleared memory for session {session_id}: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to clear session memory: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if memory system is available"""
        return redis_client.is_available()
    
    def add_semantic_memory(self, user_id: str, content: str, memory_type: str = "preference", metadata: Dict[str, Any] = None) -> bool:
        """Add semantic memory for long-term storage"""
        try:
            return milvus_semantic_store.add_memory(user_id, content, memory_type, metadata)
        except Exception as e:
            self.logger.error(f"Failed to add semantic memory: {e}")
            return False

    def get_semantic_context(self, user_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Get relevant semantic memories for query"""
        try:
            return milvus_semantic_store.search_memories(user_id, query, top_k)
        except Exception as e:
            self.logger.error(f"Failed to get semantic context: {e}")
            return []

    def get_enhanced_context(self, session_id: str, user_id: str = None, query: str = None) -> Dict[str, Any]:
        """Get complete memory context including semantic memories"""
        try:
            context = self.get_context(session_id)
            
            if user_id and query:
                semantic_memories = self.get_semantic_context(user_id, query)
                context["semantic_memories"] = semantic_memories
            else:
                context["semantic_memories"] = []
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get enhanced context: {e}")
            return self.get_context(session_id)

memory_manager = MemoryManager()
