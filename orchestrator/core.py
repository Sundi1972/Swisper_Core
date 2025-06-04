import re
import os
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI 
from pydantic import BaseModel 
import datetime 
import json 

# Import pipeline creation functions for contract path
try:
    from contract_engine.contract_pipeline import create_product_selection_pipeline
    from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline
    from contract_engine.pipelines.preference_match_pipeline import create_preference_match_pipeline
except ImportError: 
    from contract_engine.contract_pipeline import create_product_selection_pipeline
    create_product_search_pipeline = None
    create_preference_match_pipeline = None

# Import RAG function
try:
    from haystack_pipeline import ask_doc as ask_document_pipeline
    RAG_AVAILABLE = True
    logging.getLogger(__name__).info("RAG `ask_doc` function imported successfully.")
except ImportError:
    logging.getLogger(__name__).warning("Failed to import `ask_doc` from `haystack_pipeline`. RAG functionality will be disabled.")
    RAG_AVAILABLE = False
    # Define a dummy function if import fails, so the rest of the code doesn't break
    def ask_document_pipeline(question: str):
        """Dummy function to handle RAG unavailability."""
        return "RAG system is currently unavailable due to an import error."

# Import session store functions
from . import session_store 
from .session_store import set_pending_confirmation, get_pending_confirmation, clear_pending_confirmation
from contract_engine.session_persistence import load_session_context, cleanup_old_sessions

logger = logging.getLogger(__name__)

# Initialize OpenAI client (for chat path)
try:
    async_client = AsyncOpenAI()
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found. LLM calls for chat/RAG path may fail.")
except Exception as e:
    logger.error("Failed to initialize AsyncOpenAI client: %s", e, exc_info=True)
    async_client = None

# Initialize Pipelines (Contract Path)
try:
    PRODUCT_SELECTION_PIPELINE = create_product_selection_pipeline()
    logger.info("Product Selection Pipeline initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize Product Selection Pipeline: %s", e, exc_info=True)
    PRODUCT_SELECTION_PIPELINE = None

# Initialize new pipeline architecture
try:
    if create_product_search_pipeline and create_preference_match_pipeline:
        PRODUCT_SEARCH_PIPELINE = create_product_search_pipeline()
        PREFERENCE_MATCH_PIPELINE = create_preference_match_pipeline(top_k=3)
        logger.info("New pipeline architecture initialized successfully.")
    else:
        PRODUCT_SEARCH_PIPELINE = None
        PREFERENCE_MATCH_PIPELINE = None
        logger.warning("New pipeline architecture not available, using legacy pipeline.")
except Exception as e:
    logger.error("Failed to initialize new pipeline architecture: %s", e, exc_info=True)
    PRODUCT_SEARCH_PIPELINE = None
    PREFERENCE_MATCH_PIPELINE = None

class Message(BaseModel): 
    role: str
    content: str

async def handle(messages: List[Message], session_id: str) -> Dict[str, Any]:
    logger.info("🚀 Session start: Querying available tools and contracts", extra={"session_id": session_id})
    
    try:
        cleaned_count = cleanup_old_sessions(max_age_hours=24)
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} expired sessions", extra={"session_id": session_id})
    except Exception as e:
        logger.warning(f"Failed to cleanup old sessions: {e}")
    
    try:
        from .intent_extractor import load_available_contracts, load_available_tools
        contracts = load_available_contracts()
        tools = load_available_tools()
        logger.info("📋 Available contracts loaded", extra={"session_id": session_id, "contracts": list(contracts.keys())})
        logger.info("🔧 Available tools loaded", extra={"session_id": session_id, "tools": list(tools.keys()) if tools else []})
    except Exception as e:
        logger.error("Failed to load contracts/tools", extra={"session_id": session_id, "error": str(e)})
    
    logger.info("🚀 Orchestrator handling request", extra={"session_id": session_id, "message_count": len(messages)})
    
    if not messages:
        logger.warning("Orchestrator received empty messages list for session: %s", session_id)
        return {"reply": "No messages provided to orchestrator.", "session_id": session_id}

    last_user_message_pydantic = messages[-1] 
    last_user_message_content = last_user_message_pydantic.content
    
    session_store.add_chat_message(session_id, last_user_message_pydantic.dict())

    reply_content = "" # Initialize reply_content

    # 1. Check for a pending confirmation (from contract path)
    pending_product = get_pending_confirmation(session_id)
    if pending_product:
        product_name = pending_product.get("name", "the selected product")
        if last_user_message_content.lower() in ["yes", "y", "confirm", "ok", "okay", "proceed", "sure"]:
            reply_content = f"Great! Order confirmed for {product_name}."
            logger.info("✅ Order confirmed", extra={"session_id": session_id, "product": product_name})
            try:
                artifact_dir = "tmp/contracts"
                os.makedirs(artifact_dir, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_session_id = re.sub(r'[^a-zA-Z0-9_-]', '_', session_id) 
                artifact_path = os.path.join(artifact_dir, f"{safe_session_id}_{timestamp}.json")
                artifact_data = {
                    "session_id": session_id, "confirmed_product": pending_product,
                    "confirmation_time": datetime.datetime.now().isoformat(),
                    "chat_history_at_confirmation": session_store.get_chat_history(session_id) 
                }
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(artifact_data, f, indent=2)
                logger.info("Session %s: Contract artifact saved to %s", session_id, artifact_path)
            except Exception as e:
                logger.error("Session %s: Failed to save contract artifact: %s", session_id, e, exc_info=True)
            clear_pending_confirmation(session_id)
        elif last_user_message_content.lower() in ["no", "n", "cancel", "stop"]:
            reply_content = f"Okay, the order for {product_name} has been cancelled."
            logger.info("❌ Order cancelled", extra={"session_id": session_id, "product": product_name})
            clear_pending_confirmation(session_id)
        else: 
            reply_content = f"Sorry, I didn't quite understand. For {product_name}, please confirm with 'yes' or 'no'."
        
        # This return is inside the 'if pending_product:' block
        if reply_content: # Ensure reply_content was set
             session_store.add_chat_message(session_id, {"role": "assistant", "content": reply_content})
        session_store.save_session(session_id)
        return {"reply": reply_content, "session_id": session_id}

    stored_fsm = session_store.get_contract_fsm(session_id)
    if stored_fsm:
        logger.info("🔄 FSM continuation: Retrieved stored FSM for session %s with user input: '%s'", session_id, last_user_message_content)
        logger.info("🔄 FSM continuation: Current state before processing: %s", stored_fsm.context.current_state if hasattr(stored_fsm, 'context') else 'unknown')
        try:
            result = stored_fsm.next(last_user_message_content)
            logger.info("🔄 FSM continuation: Processing completed", extra={
                "session_id": session_id,
                "result_keys": list(result.keys()) if isinstance(result, dict) else "not_dict",
                "new_state": stored_fsm.context.current_state if hasattr(stored_fsm, 'context') else 'unknown'
            })
            
            if "ask_user" in result:
                reply_content = result["ask_user"]
                logger.info("🔄 FSM continuation: FSM asking user", extra={"session_id": session_id, "question": reply_content})
                
                # If it's a confirmation question, set pending confirmation
                if "confirm" in reply_content.lower() and hasattr(stored_fsm, 'context') and stored_fsm.context.selected_product:
                    set_pending_confirmation(session_id, stored_fsm.context.selected_product)
                    # Clear stored FSM since we're moving to confirmation
                    session_store.set_contract_fsm(session_id, None)
                    logger.info("🔄 FSM continuation: Moving to confirmation, FSM cleared", extra={"session_id": session_id})
                elif hasattr(stored_fsm, 'context') and stored_fsm.context.current_state in ["cancelled"]:
                    session_store.set_contract_fsm(session_id, None)
                    logger.info("🔄 FSM continuation: FSM cancelled, cleared from storage", extra={"session_id": session_id})
                else:
                    session_store.set_contract_fsm(session_id, stored_fsm)
                    logger.info("🔄 FSM continuation: FSM updated and stored for next interaction", extra={"session_id": session_id, "state": stored_fsm.context.current_state if hasattr(stored_fsm, 'context') else 'unknown'})
            else:
                reply_content = "Sorry, I couldn't process your request. Could you try rephrasing?"
                session_store.set_contract_fsm(session_id, None)
                logger.error("🔄 FSM continuation: FSM did not return ask_user, clearing FSM", extra={"session_id": session_id, "result": result})
                
        except Exception as e:
            logger.error("🔄 FSM continuation: Error continuing stored contract FSM for session %s: %s", session_id, e, exc_info=True)
            reply_content = "Sorry, there was an error processing your request."
            session_store.set_contract_fsm(session_id, None)
        
        session_store.add_chat_message(session_id, {"role": "assistant", "content": reply_content})
        session_store.save_session(session_id)
        return {"reply": reply_content, "session_id": session_id}

    # 3. If no pending confirmation or stored FSM, proceed with routing using LLM intent extraction
    try:
        from .intent_extractor import extract_user_intent
        from .tool_orchestrator import orchestrate_tools
        
        intent_data = extract_user_intent(last_user_message_content)
        intent_type = intent_data.get("intent_type")
        parameters = intent_data.get("parameters", {})
        
        logger.info("🎯 User intent extracted", extra={
            "session_id": session_id, 
            "intent": intent_type, 
            "confidence": intent_data.get("confidence", 0.0),
            "reasoning": intent_data.get("reasoning", "")
        })
        
        if intent_type == "contract":
            contract_template = parameters.get("contract_template")
            logger.info("🎯 User intent matched to Contract", extra={
                "session_id": session_id,
                "contract_template": contract_template
            })
        
    except Exception as e:
        logger.error("Intent extraction failed, using fallback: %s", e)
        contract_keywords = r"\b(buy|purchase|order|acquire|get me|shop for|find a|buy an)\b"
        is_contract_intent = bool(PRODUCT_SELECTION_PIPELINE and re.search(contract_keywords, last_user_message_content, re.IGNORECASE))
        rag_trigger_keyword = "#rag"
        is_rag_intent = bool(last_user_message_content.lower().startswith(rag_trigger_keyword))
        
        if is_contract_intent:
            intent_type = "contract"
            parameters = {"contract_template": "purchase_item.yaml", "extracted_query": last_user_message_content}
        elif is_rag_intent:
            intent_type = "rag"
            parameters = {"rag_question": last_user_message_content[len(rag_trigger_keyword):].lstrip()}
        else:
            intent_type = "chat"
            parameters = {}

    if intent_type == "contract":
        contract_template = parameters.get("contract_template")
        if contract_template == "purchase_item.yaml":
            logger.info("🛒 Contract path triggered", extra={"session_id": session_id, "contract_query": last_user_message_content})
            try:
                from contract_engine.contract_engine import ContractStateMachine
                from contract_engine.llm_helpers import extract_initial_criteria
                
                logger.info("📝 Extracting criteria from user prompt", extra={"session_id": session_id, "prompt": last_user_message_content})
                criteria_data = extract_initial_criteria(last_user_message_content)
                
                search_query = parameters.get("extracted_query", last_user_message_content)
                
                logger.info("📋 Criteria extracted", extra={"session_id": session_id, "criteria": criteria_data})
                logger.info("🔍 Searching for products", extra={"session_id": session_id, "product": search_query, "criteria": criteria_data})
                
                fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
                
                enhanced_context = load_session_context(session_id)
                if enhanced_context:
                    fsm.context = enhanced_context
                    logger.info("🔄 Enhanced session context loaded", extra={"session_id": session_id, "state": enhanced_context.current_state})
                
                # Initialize FSM with new pipeline architecture if available
                if PRODUCT_SEARCH_PIPELINE and PREFERENCE_MATCH_PIPELINE:
                    fsm.product_search_pipeline = PRODUCT_SEARCH_PIPELINE
                    fsm.preference_match_pipeline = PREFERENCE_MATCH_PIPELINE
                    logger.info("🔧 FSM initialized with new pipeline architecture", extra={"session_id": session_id})
                else:
                    logger.warning("🔧 FSM initialized with legacy architecture", extra={"session_id": session_id})
                
                fsm.fill_parameters({
                    "product": search_query,
                    "session_id": session_id,
                    "product_threshold": 10,
                    "initial_criteria": criteria_data,
                    "parsed_specifications": criteria_data.get("specifications", {}),
                    "enhanced_query": search_query
                })
                
                logger.info("🔧 FSM initialized", extra={"session_id": session_id, "initial_state": fsm.context.current_state})
                
                result = fsm.next()
                
                logger.info("🔧 FSM first execution completed", extra={
                    "session_id": session_id,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else "not_dict",
                    "context_state": fsm.context.current_state,
                    "context_status": fsm.context.contract_status
                })
                
                if "ask_user" in result:
                    reply_content = result["ask_user"]
                    logger.info("❓ FSM asking user", extra={"session_id": session_id, "question": reply_content})
                    
                    if "confirm" in reply_content.lower() and hasattr(fsm, 'context') and fsm.context.selected_product:
                        set_pending_confirmation(session_id, fsm.context.selected_product)
                    elif hasattr(fsm, 'context') and fsm.context.current_state in ["cancelled"]:
                        session_store.set_contract_fsm(session_id, None)
                    else:
                        session_store.set_contract_fsm(session_id, fsm)
                        logger.info("💾 FSM stored for continuation", extra={"session_id": session_id, "state": fsm.context.current_state})
                else:
                    reply_content = "Sorry, I couldn't find a suitable product for your query. Could you try rephrasing or a different product?"
                    logger.error("❌ FSM did not return ask_user", extra={"session_id": session_id, "result": result})
                    
            except Exception as e:
                logger.error("Error running enhanced contract flow for session %s: %s", session_id, e, exc_info=True)
                reply_content = "Sorry, there was an error trying to find products for you."
        else:
            reply_content = f"Contract template {contract_template} is not yet supported."
    
    elif intent_type == "tool_usage":
        logger.info("Tool usage path triggered for session %s. Input: '%s'", session_id, last_user_message_content)
        tools_needed = parameters.get("tools_needed", [])
        if not isinstance(tools_needed, list):
            tools_needed = [tools_needed] if tools_needed else []
        try:
            reply_content = orchestrate_tools(last_user_message_content, tools_needed)
        except Exception as e:
            logger.error("Error in tool orchestration for session %s: %s", session_id, e, exc_info=True)
            reply_content = "Sorry, there was an error using the tools to help you."
    
    elif intent_type == "rag":
        logger.info("📚 RAG path triggered", extra={"session_id": session_id, "rag_question": last_user_message_content})
        question_for_rag = parameters.get("rag_question", "")
        
        if not question_for_rag:
            reply_content = "Please provide a question after the #rag trigger."
        else:
            try:
                reply_content = ask_document_pipeline(question=question_for_rag)
                logger.info("📖 RAG response generated", extra={"session_id": session_id, "response_preview": reply_content[:100]})
            except Exception as e: 
                logger.error("Error calling RAG ask_document_pipeline for session %s: %s", session_id, e, exc_info=True)
                reply_content = "Sorry, there was an error trying to answer your document question."
    
    else:
        logger.info("💬 Chat path triggered", extra={"session_id": session_id, "user_input": last_user_message_content})
        if not async_client:
            logger.error("AsyncOpenAI client not available for chat path.")
            reply_content = "Error: LLM service not available." 
        else:
            current_chat_history = session_store.get_chat_history(session_id)
            try:
                llm_response = await async_client.chat.completions.create(model="gpt-4o", messages=current_chat_history)
                reply_content = llm_response.choices[0].message.content
            except Exception as e:
                logger.error("OpenAI API call failed for session %s: %s", session_id, e, exc_info=True)
                reply_content = "Sorry, an error occurred with the AI assistant."

    # Fallback reply if no path explicitly set it (should be rare given the logic structure)
    if not reply_content: 
        logger.error("Orchestrator did not produce a reply for session %s. This indicates a logic gap.", session_id)
        reply_content = "I'm not sure how to respond to that. Please try again."

    session_store.add_chat_message(session_id, {"role": "assistant", "content": reply_content})
    session_store.save_session(session_id)
    return {"reply": reply_content, "session_id": session_id}
