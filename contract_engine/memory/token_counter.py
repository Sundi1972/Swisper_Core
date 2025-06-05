import tiktoken
import logging
from typing import List, Dict, Any, Union
from swisper_core import get_logger


class TokenCounter:
    """Token counting service using tiktoken"""
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
        self.logger = get_logger(__name__)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a single text string"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            self.logger.error(f"Token counting failed for text: {e}")
            return len(text) // 4
    
    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """Count tokens in a message dictionary"""
        try:
            if message is None:
                return 0
            
            if isinstance(message, dict):
                text = str(message.get("content", "")) + str(message.get("role", ""))
            else:
                text = str(message)
            return self.count_tokens(text)
        except Exception as e:
            self.logger.error(f"Message token counting failed: {e}")
            return 0
    
    def count_batch_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Count total tokens in a batch of messages"""
        total = 0
        for message in messages:
            total += self.count_message_tokens(message)
        return total
    
    def estimate_context_tokens(self, context: Dict[str, Any]) -> int:
        """Estimate tokens in SwisperContext"""
        try:
            text_fields = ["product_query", "enhanced_query", "step_log"]
            total = 0
            
            for field in text_fields:
                if field in context and context[field]:
                    if isinstance(context[field], list):
                        total += sum(self.count_tokens(str(item)) for item in context[field])
                    else:
                        total += self.count_tokens(str(context[field]))
            
            return total
        except Exception as e:
            self.logger.error(f"Context token estimation failed: {e}")
            return 0
    
    def should_trigger_summary(self, messages: List[Dict[str, Any]], threshold: int = 3000) -> bool:
        """Check if message buffer should trigger summarization"""
        return self.count_batch_tokens(messages) >= threshold
    
    def get_overflow_messages(self, messages: List[Dict[str, Any]], max_tokens: int = 4000) -> List[Dict[str, Any]]:
        """Get messages that exceed token limit for removal"""
        total_tokens = 0
        overflow_count = 0
        
        for i in range(len(messages) - 1, -1, -1):
            msg_tokens = self.count_message_tokens(messages[i])
            if total_tokens + msg_tokens > max_tokens:
                overflow_count = len(messages) - i
                break
            total_tokens += msg_tokens
        
        return messages[:overflow_count] if overflow_count > 0 else []
