import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from swisper_core import get_logger

logger = get_logger(__name__)

class LLMAdapter:
    """Base class for LLM adapters"""
    
    def __init__(self):
        self.client = None
        
    def chat_completion(self, messages: list, model: str = None, **kwargs) -> str:
        """Generate chat completion"""
        raise NotImplementedError
        
class OpenAIAdapter(LLMAdapter):
    """OpenAI LLM adapter"""
    
    def __init__(self):
        super().__init__()
        try:
            self.client = OpenAI()
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not found. LLM calls may fail.")
        except Exception as e:
            logger.error("Failed to initialize OpenAI client: %s", e)
            self.client = None
            
    def chat_completion(self, messages: list, model: str = "gpt-4o", **kwargs) -> str:
        """Generate chat completion using OpenAI"""
        if not self.client:
            raise Exception("OpenAI client not initialized")
            
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise

def get_llm_adapter() -> LLMAdapter:
    """Get LLM adapter based on environment configuration"""
    provider = os.environ.get("SWISPER_LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        return OpenAIAdapter()
    else:
        logger.warning(f"Unknown LLM provider: {provider}, falling back to OpenAI")
        return OpenAIAdapter()
