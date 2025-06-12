import re
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging
from .config import settings

logger = logging.getLogger(__name__)

class IntentDetector:
    """
    Intent detection system using hybrid approach:
    1. Keyword-based pre-classification
    2. LLM-based final classification
    """
    
    def __init__(self):
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.1
            )
        else:
            self.llm = None
            logger.warning("Intent detector initialized without OpenAI API key - using fallback keyword detection")
        
        self.contract_keywords = [
            r'\b(buy|purchase|order|acquire|get me|shop for|find a|buy an)\b',
            r'\b(product|item|thing|stuff)\b',
            r'\b(price|cost|expensive|cheap|budget)\b'
        ]
        
        self.rag_keywords = [
            r'^#rag\b',  # Explicit RAG trigger
            r'\b(document|file|pdf|contract|agreement)\b',
            r'\b(what does|explain|clarify|according to)\b'
        ]
        
        self.websearch_keywords = [
            r'\b(today|now|currently|latest|recent|new)\b',
            r'\b(news|current|update|as of)\b',
            r'\b(2024|2025)\b'  # Current year indicators
        ]
        
        if self.llm:
            self.classification_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an intent classifier for an AI assistant that handles:
1. CONTRACT - Product search, purchase workflows, shopping queries
2. RAG - Document questions, file analysis, contract interpretation  
3. WEBSEARCH - Current events, recent news, time-sensitive information
4. CHAT - General conversation, greetings, casual questions

Analyze the user message and respond with exactly one word: CONTRACT, RAG, WEBSEARCH, or CHAT

Consider:
- Contract: buying, shopping, product search, price inquiries
- RAG: document questions, file analysis, #rag prefix
- WebSearch: current events, "today", "latest", "recent", time-sensitive queries
- Chat: greetings, general questions, casual conversation"""),
                ("user", "User message: {message}\n\nKeyword analysis: {keyword_analysis}\n\nIntent:")
            ])
            
            self.chain = self.classification_prompt | self.llm | StrOutputParser()
        else:
            self.classification_prompt = None
            self.chain = None
    
    def _keyword_analysis(self, message: str) -> Dict[str, bool]:
        """Perform keyword-based pre-analysis."""
        message_lower = message.lower()
        
        analysis = {
            "contract_match": any(re.search(pattern, message_lower) for pattern in self.contract_keywords),
            "rag_match": any(re.search(pattern, message_lower) for pattern in self.rag_keywords),
            "websearch_match": any(re.search(pattern, message_lower) for pattern in self.websearch_keywords),
            "explicit_rag": message.strip().startswith("#rag")
        }
        
        return analysis
    
    async def detect_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Detect user intent using hybrid keyword + LLM approach.
        
        Args:
            message: User message to classify
            context: Optional session context for better classification
            
        Returns:
            Intent string: 'contract', 'rag', 'websearch', or 'chat'
        """
        try:
            keyword_analysis = self._keyword_analysis(message)
            
            if keyword_analysis["explicit_rag"]:
                logger.info(f"Explicit RAG intent detected: {message[:50]}...")
                return "rag"
            
            if not self.llm or not self.chain:
                return self._fallback_keyword_intent(keyword_analysis, message)
            
            keyword_summary = ", ".join([
                f"{k.replace('_', ' ')}: {v}" for k, v in keyword_analysis.items()
            ])
            
            intent = await self.chain.ainvoke({
                "message": message,
                "keyword_analysis": keyword_summary
            })
            
            intent_normalized = intent.strip().lower()
            if intent_normalized not in ["contract", "rag", "websearch", "chat"]:
                logger.warning(f"Unknown intent '{intent}', defaulting to 'chat'")
                intent_normalized = "chat"
            
            logger.info(f"Intent detected: {intent_normalized} for message: {message[:50]}...")
            return intent_normalized
            
        except Exception as e:
            logger.error(f"Error in intent detection: {e}", exc_info=True)
            return "chat"  # Safe fallback
    
    def _fallback_keyword_intent(self, keyword_analysis: Dict[str, bool], message: str) -> str:
        """Fallback keyword-based intent detection when LLM is not available."""
        if keyword_analysis["explicit_rag"]:
            return "rag"
        elif keyword_analysis["contract_match"]:
            return "contract"
        elif keyword_analysis["websearch_match"]:
            return "websearch"
        else:
            return "chat"

intent_detector = IntentDetector()
