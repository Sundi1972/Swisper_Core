import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from contract_engine.context import SwisperContext

class MessageSerializer:
    """Dedicated serialization component for memory storage"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.version = "1.0"
    
    def serialize_message(self, message: Dict[str, Any]) -> str:
        """Serialize message to JSON string with validation"""
        try:
            serialized = {
                "version": self.version,
                "timestamp": datetime.now().isoformat(),
                "data": message
            }
            return json.dumps(serialized, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Message serialization failed: {e}")
            raise ValueError(f"Failed to serialize message: {e}")
    
    def deserialize_message(self, data: str) -> Dict[str, Any]:
        """Deserialize JSON string to message with validation"""
        try:
            parsed = json.loads(data)
            if "data" not in parsed:
                raise ValueError("Invalid message format: missing data field")
            return parsed["data"]
        except json.JSONDecodeError as e:
            self.logger.error(f"Message deserialization failed: {e}")
            raise ValueError(f"Failed to deserialize message: {e}")
    
    def serialize_context(self, context: SwisperContext) -> str:
        """Serialize SwisperContext using existing to_dict method"""
        return self.serialize_message(context.to_dict())
    
    def deserialize_context(self, data: str) -> SwisperContext:
        """Deserialize to SwisperContext using existing from_dict method"""
        message_data = self.deserialize_message(data)
        return SwisperContext.from_dict(message_data)
    
    def serialize_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Serialize batch of messages"""
        return [self.serialize_message(msg) for msg in messages]
    
    def deserialize_batch(self, data_list: List[str]) -> List[Dict[str, Any]]:
        """Deserialize batch of messages"""
        return [self.deserialize_message(data) for data in data_list]
