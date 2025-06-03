import re
import os
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI 
from pydantic import BaseModel 
import datetime 
import json 

# Import Haystack pipeline creation function for contract path
try:
    from contract_engine.contract_pipeline import create_product_selection_pipeline
except ImportError: 
    from contract_engine.contract_pipeline import create_product_selection_pipeline

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

logger = logging.getLogger(__name__)

# Initialize OpenAI client (for chat path)
try:
    async_client = AsyncOpenAI()
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found. LLM calls for chat/RAG path may fail.")
except Exception as e:
    logger.error("Failed to initialize AsyncOpenAI client: %s", e, exc_info=True)
    async_client = None

# Initialize Product Selection Pipeline (Contract Path)
try:
    PRODUCT_SELECTION_PIPELINE = create_product_selection_pipeline()
    logger.info("Product Selection Pipeline initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize Product Selection Pipeline: %s", e, exc_info=True)
    PRODUCT_SELECTION_PIPELINE = None

class Message(BaseModel): 
    role: str
    content: str

async def handle(messages: List[Message], session_id: str) -> Dict[str, Any]:
    logger.info("Orchestrator handling for session: %s, with %d messages.", session_id, len(messages))
    
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
            logger.info("Session %s: User confirmed order for %s.", session_id, product_name)
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
            logger.info("Session %s: User cancelled order for %s.", session_id, product_name)
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
        logger.info("Session %s: Continuing stored contract FSM with user input: '%s'", session_id, last_user_message_content)
        try:
            result = stored_fsm.next(last_user_message_content)
            
            if "ask_user" in result:
                reply_content = result["ask_user"]
                
                # If it's a confirmation question, set pending confirmation
                if "confirm" in reply_content.lower() and hasattr(stored_fsm, 'selected_product_for_confirmation'):
                    set_pending_confirmation(session_id, stored_fsm.selected_product_for_confirmation)
                    # Clear stored FSM since we're moving to confirmation
                    session_store.set_contract_fsm(session_id, None)
                elif stored_fsm.state in ["cancelled"]:
                    session_store.set_contract_fsm(session_id, None)
                else:
                    session_store.set_contract_fsm(session_id, stored_fsm)
            else:
                reply_content = "Sorry, I couldn't process your request. Could you try rephrasing?"
                session_store.set_contract_fsm(session_id, None)
                
        except Exception as e:
            logger.error("Error continuing stored contract FSM for session %s: %s", session_id, e, exc_info=True)
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
        
        logger.info("Session %s: Extracted intent: %s (confidence: %.2f)", 
                   session_id, intent_type, intent_data.get("confidence", 0.0))
        
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
            logger.info("Contract path triggered for session %s. Input: '%s'", session_id, last_user_message_content)
            try:
                from contract_engine.contract_engine import ContractStateMachine
                from contract_engine.llm_helpers import extract_initial_criteria
                
                logger.info("Session %s: Extracting criteria from prompt: '%s'", session_id, last_user_message_content)
                criteria_data = extract_initial_criteria(last_user_message_content)
                
                search_query = parameters.get("extracted_query", last_user_message_content)
                
                logger.info("Session %s: Extracted criteria: %s", session_id, criteria_data)
                logger.info("Session %s: Using search query: '%s'", session_id, search_query)
                
                fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
                fsm.fill_parameters({
                    "product": search_query,
                    "session_id": session_id,
                    "product_threshold": 10,
                    "initial_criteria": criteria_data,
                    "parsed_specifications": criteria_data.get("specifications", {}),
                    "enhanced_query": search_query
                })
                
                result = fsm.next()
                
                if "ask_user" in result:
                    reply_content = result["ask_user"]
                    
                    if "confirm" in reply_content.lower() and hasattr(fsm, 'selected_product_for_confirmation'):
                        set_pending_confirmation(session_id, fsm.selected_product_for_confirmation)
                    elif fsm.state in ["cancelled"]:
                        session_store.set_contract_fsm(session_id, None)
                    else:
                        session_store.set_contract_fsm(session_id, fsm)
                else:
                    reply_content = "Sorry, I couldn't find a suitable product for your query. Could you try rephrasing or a different product?"
                    
            except Exception as e:
                logger.error("Error running enhanced contract flow for session %s: %s", session_id, e, exc_info=True)
                reply_content = "Sorry, there was an error trying to find products for you."
        else:
            reply_content = f"Contract template {contract_template} is not yet supported."
    
    elif intent_type == "tool_usage":
        logger.info("Tool usage path triggered for session %s. Input: '%s'", session_id, last_user_message_content)
        tools_needed = parameters.get("tools_needed", [])
        try:
            reply_content = orchestrate_tools(last_user_message_content, tools_needed)
        except Exception as e:
            logger.error("Error in tool orchestration for session %s: %s", session_id, e, exc_info=True)
            reply_content = "Sorry, there was an error using the tools to help you."
    
    elif intent_type == "rag":
        logger.info("RAG path for session %s. Input: '%s'", session_id, last_user_message_content)
        question_for_rag = parameters.get("rag_question", "")
        
        if not question_for_rag:
            reply_content = "Please provide a question after the #rag trigger."
        else:
            try:
                reply_content = ask_document_pipeline(question=question_for_rag)
                logger.info("RAG pipeline returned for session %s: '%s...'", session_id, reply_content[:100])
            except Exception as e: 
                logger.error("Error calling RAG ask_document_pipeline for session %s: %s", session_id, e, exc_info=True)
                reply_content = "Sorry, there was an error trying to answer your document question."
    
    else:
        logger.info("Chat path for session %s. Input: '%s'", session_id, last_user_message_content)
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
