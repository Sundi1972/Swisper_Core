import logging
from typing import List, Dict, Any, Optional
import time
from .redis_client import redis_client
from .message_serializer import MessageSerializer
from .token_counter import TokenCounter

class BufferStore:
    """Redis Lists-based ephemeral buffer for 30-message/4k token storage"""
    
    def __init__(self, max_messages: int = 30, max_tokens: int = 4000, ttl_seconds: int = 21600):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.ttl_seconds = ttl_seconds
        self.serializer = MessageSerializer()
        self.token_counter = TokenCounter()
        self.logger = logging.getLogger(__name__)
    
    def _get_buffer_key(self, session_id: str) -> str:
        """Generate Redis key for session buffer"""
        return f"buffer:{session_id}"
    
    def _get_metadata_key(self, session_id: str) -> str:
        """Generate Redis key for buffer metadata"""
        return f"buffer_meta:{session_id}"
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add message to buffer with overflow handling"""
        try:
            client = redis_client.get_client()
            buffer_key = self._get_buffer_key(session_id)
            meta_key = self._get_metadata_key(session_id)
            
            serialized_message = self.serializer.serialize_message(message)
            
            client.rpush(buffer_key, serialized_message.encode('utf-8'))
            client.expire(buffer_key, self.ttl_seconds)
            
            client.hset(meta_key, "last_updated", str(int(time.time())))
            client.hset(meta_key, "message_count", str(client.llen(buffer_key)))
            client.expire(meta_key, self.ttl_seconds)
            
            self._enforce_limits(session_id)
            
            self.logger.debug(f"Added message to buffer for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add message to buffer: {e}")
            return False
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from buffer"""
        try:
            client = redis_client.get_client()
            buffer_key = self._get_buffer_key(session_id)
            
            if limit:
                serialized_messages = client.lrange(buffer_key, -limit, -1)
            else:
                serialized_messages = client.lrange(buffer_key, 0, -1)
            
            messages = []
            for serialized in serialized_messages:
                try:
                    if isinstance(serialized, bytes):
                        serialized_str = serialized.decode('utf-8')
                    else:
                        serialized_str = str(serialized)
                    message = self.serializer.deserialize_message(serialized_str)
                    messages.append(message)
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize message: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to get messages from buffer: {e}")
            return []
    
    def get_buffer_info(self, session_id: str) -> Dict[str, Any]:
        """Get buffer metadata and statistics"""
        try:
            client = redis_client.get_client()
            buffer_key = self._get_buffer_key(session_id)
            meta_key = self._get_metadata_key(session_id)
            
            message_count = client.llen(buffer_key)
            metadata = client.hgetall(meta_key)
            
            messages = self.get_messages(session_id)
            total_tokens = self.token_counter.count_batch_tokens(messages)
            
            return {
                "message_count": message_count,
                "total_tokens": total_tokens,
                "last_updated": int(metadata.get(b"last_updated", 0)) if metadata else 0,
                "ttl_remaining": client.ttl(buffer_key),
                "max_messages": self.max_messages,
                "max_tokens": self.max_tokens
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get buffer info: {e}")
            return {}
    
    def _enforce_limits(self, session_id: str):
        """Enforce message count and token limits"""
        try:
            client = redis_client.get_client()
            buffer_key = self._get_buffer_key(session_id)
            
            current_count = client.llen(buffer_key)
            if current_count > self.max_messages:
                excess = current_count - self.max_messages
                for _ in range(excess):
                    client.lpop(buffer_key)
                self.logger.debug(f"Removed {excess} messages due to count limit")
            
            messages = self.get_messages(session_id)
            total_tokens = self.token_counter.count_batch_tokens(messages)
            
            if total_tokens > self.max_tokens:
                overflow_count = 0
                current_tokens = total_tokens
                for i, message in enumerate(messages):
                    if current_tokens <= self.max_tokens:
                        break
                    message_tokens = self.token_counter.count_message_tokens(message)
                    current_tokens -= message_tokens
                    overflow_count += 1
                overflow_messages = messages[:overflow_count]
            else:
                overflow_messages = []
            
            if overflow_messages:
                for _ in range(len(overflow_messages)):
                    client.lpop(buffer_key)
                self.logger.debug(f"Removed {len(overflow_messages)} messages due to token limit")
                
        except Exception as e:
            self.logger.error(f"Failed to enforce buffer limits: {e}")
    
    def clear_buffer(self, session_id: str) -> bool:
        """Clear all messages from buffer"""
        try:
            client = redis_client.get_client()
            buffer_key = self._get_buffer_key(session_id)
            meta_key = self._get_metadata_key(session_id)
            
            client.delete(buffer_key, meta_key)
            
            self.logger.debug(f"Cleared buffer for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear buffer: {e}")
            return False
    
    def should_trigger_summary(self, session_id: str, threshold: int = 3000) -> bool:
        """Check if buffer should trigger summarization"""
        try:
            messages = self.get_messages(session_id)
            return self.token_counter.should_trigger_summary(messages, threshold)
        except Exception as e:
            self.logger.error(f"Failed to check summary trigger: {e}")
            return False
