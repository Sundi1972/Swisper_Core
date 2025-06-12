from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from .models import ChatRequest, ChatResponse, Message, DocumentQuery, DocumentResponse, ContractState
from .config import settings
from .session_manager import session_manager
from .intent_detector import intent_detector
from .workflows.contract_workflow import contract_workflow
from .workflows.rag_workflow import rag_workflow

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Swisper LangGraph AI Assistant",
    description="Modern AI assistant built with LangGraph and LangChain",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Swisper LangGraph AI Assistant")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"OpenAI Model: {settings.openai_model}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Swisper LangGraph AI Assistant")
    await session_manager.cleanup_expired_sessions()

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "message": "Swisper LangGraph AI Assistant API",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.app_env
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "swisper-langgraph",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for the AI assistant.
    Routes requests to appropriate workflows based on intent detection.
    """
    try:
        logger.info(f"Chat request for session {request.session_id} with {len(request.messages)} messages")
        
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        user_message = request.messages[-1]
        if user_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        await session_manager.add_message(request.session_id, user_message)
        
        intent = await intent_detector.detect_intent(user_message.content)
        logger.info(f"Detected intent: {intent} for session {request.session_id}")
        
        reply = await _route_to_workflow(intent, user_message.content, request.session_id)
        
        assistant_message = Message(
            role="assistant",
            content=reply,
            timestamp=datetime.utcnow()
        )
        
        await session_manager.add_message(request.session_id, assistant_message)
        
        return ChatResponse(
            reply=reply,
            session_id=request.session_id,
            intent=intent,
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/rag", response_model=DocumentResponse)
async def rag_endpoint(query: DocumentQuery):
    """
    Dedicated RAG endpoint for document queries.
    """
    try:
        logger.info(f"RAG query for session {query.session_id}: {query.question[:100]}...")
        
        response = await rag_workflow.process_query(query)
        return response
        
    except Exception as e:
        logger.error(f"Error in RAG endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG processing failed")

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information and message history."""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = await session_manager.get_messages(session_id, limit=50)
        
        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": session.message_count,
            "messages": [msg.model_dump() for msg in messages]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data."""
    try:
        success = await session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session")

async def _route_to_workflow(intent: str, message: str, session_id: str) -> str:
    """
    Route user message to appropriate workflow based on detected intent.
    
    Args:
        intent: Detected intent (contract, rag, websearch, chat)
        message: User message content
        session_id: Session identifier
        
    Returns:
        Response string from the appropriate workflow
    """
    try:
        if intent == "contract":
            return await _handle_contract_workflow(message, session_id)
        elif intent == "rag":
            return await _handle_rag_workflow(message, session_id)
        elif intent == "websearch":
            return await _handle_websearch_workflow(message, session_id)
        else:  # chat
            return await _handle_chat_workflow(message, session_id)
            
    except Exception as e:
        logger.error(f"Error routing workflow for intent {intent}: {e}", exc_info=True)
        return f"I encountered an error processing your request. Please try again."

async def _handle_contract_workflow(message: str, session_id: str) -> str:
    """Handle contract/purchase workflow using LangGraph."""
    try:
        initial_state = ContractState(
            session_id=session_id,
            user_query=message,
            intent="contract"
        )
        
        result = await contract_workflow.app.ainvoke(initial_state.model_dump())
        
        logger.info(f"Contract workflow result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        logger.info(f"Contract workflow result: {result}")
        
        if result.get("error_message"):
            return f"I encountered an issue with your product search: {result['error_message']}"
        
        if result.get("presentation"):
            return result["presentation"]
        elif result.get("confirmation_message"):
            return result["confirmation_message"]
        elif result.get("ranked_products") and result.get("current_step") == "awaiting_selection":
            presentation = contract_workflow._format_product_presentation(result["ranked_products"])
            return presentation
        else:
            return "I'm processing your product search request. Let me find some options for you..."
            
    except Exception as e:
        logger.error(f"Error in contract workflow: {e}", exc_info=True)
        return "I'm having trouble processing your product search right now. Please try again."

async def _handle_rag_workflow(message: str, session_id: str) -> str:
    """Handle RAG document queries."""
    try:
        clean_question = message.replace("#rag", "").strip()
        
        query = DocumentQuery(
            question=clean_question,
            session_id=session_id,
            context_limit=5
        )
        
        response = await rag_workflow.process_query(query)
        
        reply = response.answer
        if response.sources:
            reply += f"\n\n**Sources:** {', '.join(response.sources)}"
        
        return reply
        
    except Exception as e:
        logger.error(f"Error in RAG workflow: {e}", exc_info=True)
        return "I'm having trouble accessing the documents right now. Please try again."

async def _handle_websearch_workflow(message: str, session_id: str) -> str:
    """Handle web search queries (placeholder for now)."""
    return (
        f"I detected that you're asking about current information: '{message}'. "
        "Web search functionality is not yet implemented in this version. "
        "For now, I can help with product searches and document questions."
    )

async def _handle_chat_workflow(message: str, session_id: str) -> str:
    """Handle general chat conversations."""
    try:
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "Hello! I'm your AI assistant. I can help you with product searches, answer questions about documents, or just have a conversation. What would you like to do today?"
        
        elif any(thanks in message_lower for thanks in ["thank you", "thanks", "appreciate"]):
            return "You're welcome! Is there anything else I can help you with?"
        
        elif "help" in message_lower:
            return """I can help you with several things:

🛍️ **Product Search**: Ask me to find products like "find me a laptop" or "I want to buy headphones"

📄 **Document Questions**: Use #rag followed by your question to search through documents

💬 **General Chat**: Just talk to me naturally about anything

What would you like to try?"""
        
        else:
            return f"I understand you're saying: '{message}'. I'm a specialized AI assistant focused on product searches and document analysis. How can I help you with those tasks today?"
            
    except Exception as e:
        logger.error(f"Error in chat workflow: {e}", exc_info=True)
        return "I'm here to help! What can I do for you today?"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
