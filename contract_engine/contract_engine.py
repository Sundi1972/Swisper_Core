import yaml
import json
from pathlib import Path
import datetime # For datetime.datetime.now()
import logging
from typing import Optional, Dict, Any, List # Added List
import os # For makedirs

# Import the real search function (with mock fallback)
from tool_adapter.mock_google import google_shopping_search as search_product

# LLM Helper functions are no longer used by the slimmed FSM
# from engine.llm_helpers import (
#     analyze_product_differences,
#     analyze_user_preferences,
#     check_product_compatibility,
#     filter_products_with_llm
# )

class ContractStateMachine:
    def __init__(self, template_path, schema_path=None): # schema_path is not used in slimmed version but kept for signature
        self.template_path = template_path
        self.logger = logging.getLogger(__name__)
        self.contract = self.load_template()

        if not self.contract: # Handle case where template loading fails
            self.logger.error(f"Failed to load contract template from {template_path}. FSM cannot operate.")
            self.contract = {"parameters": {}, "subtasks": []} # Minimal valid contract
            self.state = "error" # Special state to indicate failure
            return

        self.state = "start"
        # Ensure session_id is initialized if possible, or by orchestrator via fill_parameters
        self.contract.setdefault("parameters", {}).setdefault("session_id", "default_fsm_session")
        self.search_results: List[Dict[str, Any]] = [] # Initialize search_results with type hint
        self.selected_product_for_confirmation: Dict[str, Any] = {} # Initialize selected product with type hint

    def load_template(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self.template_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Template file not found at {self.template_path}")
            return None
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML template at {self.template_path}: {e}", exc_info=True)
            return None

    def fill_parameters(self, param_data: Dict[str, Any]):
        self.contract.setdefault("parameters", {}).update(param_data)
        self.logger.info(f"Parameters filled for session {self.contract['parameters'].get('session_id')}: {param_data}")

    def next(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        parameters = self.contract.get("parameters", {})
        session_id = parameters.get("session_id", "unknown_session")

        self.logger.info(f"FSM (session: {session_id}): Current state: {self.state}, Input: '{user_input}'")

        if self.state == "start":
            if not parameters.get("product"):
                self.logger.warning(f"FSM (session: {session_id}): Product not set in 'start' state. Asking user.")
                return {"ask_user": "What product are you looking for?"}
            
            self.logger.info(f"FSM (session: {session_id}): Transition: start → search")
            self.state = "search"
            return self.next()

        elif self.state == "search":
            product_query = parameters.get("product")
            if not product_query:
                self.logger.error(f"FSM (session: {session_id}): Product query is empty in 'search' state.")
                self.contract["status"] = "failed"
                return {"status": "failed", "message": "No product specified for search."}

            self.logger.info(f"FSM (session: {session_id}): Searching for product: '{product_query}' using SearchAPI.")
            results = search_product(q=product_query) 

            self.contract.setdefault("subtasks", []).append({
                "id": "search_product",
                "type": "search",
                "status": "completed",
                "results": results
            })
            self.search_results = results

            if not results or (isinstance(results, list) and results and results[0].get("error")):
                self.logger.warning(f"FSM (session: {session_id}): No products found or error from search for '{product_query}'. Results: {results}")
            
            threshold = parameters.get("product_threshold", 10)
            if len(results) > threshold:
                self.logger.info(f"FSM (session: {session_id}): Found {len(results)} products (>{threshold}). Transition: search → analyze_attributes")
                self.state = "analyze_attributes"
            else:
                self.logger.info(f"FSM (session: {session_id}): Found {len(results)} products (<={threshold}). Transition: search → rank_and_select")
                self.state = "rank_and_select"
            return self.next()

        elif self.state == "analyze_attributes":
            try:
                from contract_engine.llm_helpers import analyze_product_differences
                product_query = parameters.get("product")
                analysis = analyze_product_differences(self.search_results)
                
                attributes = self._extract_attributes_from_analysis(analysis, product_query)
                self.contract["parameters"]["extracted_attributes"] = attributes
                
                self.logger.info(f"FSM (session: {session_id}): Extracted attributes: {attributes}. Transition: analyze_attributes → ask_clarification")
                self.state = "ask_clarification"
                return self.next()
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error in analyze_attributes: {e}")
                self.state = "rank_and_select"
                return self.next()

        elif self.state == "ask_clarification":
            extracted_attributes = self.contract["parameters"].get("extracted_attributes", [])
            product_query = parameters.get("product")
            
            attribute_examples = ", ".join(extracted_attributes[:3]) if extracted_attributes else "brand, price range, features"
            clarification_message = (
                f"I found {len(self.search_results)} results for '{product_query}'. "
                f"To help you choose the best option, could you provide more criteria? "
                f"For example: {attribute_examples}, or any specific requirements you have. "
                f"Or type 'cancel' to exit this purchase."
            )
            
            self.logger.info(f"FSM (session: {session_id}): Asking for clarification. Transition: ask_clarification → wait_for_preferences")
            self.state = "wait_for_preferences"
            return {"ask_user": clarification_message}

        elif self.state == "wait_for_preferences":
            if not user_input:
                return {"ask_user": "Please provide your preferences to help me filter the products."}
            
            try:
                from contract_engine.llm_helpers import analyze_user_preferences, is_cancel_request, is_response_relevant
                
                if is_cancel_request(user_input):
                    self.state = "cancelled"
                    return {"ask_user": "Purchase cancelled. Is there anything else I can help you with?"}
                
                product_context = self.contract["parameters"].get("product", "product")
                relevance_check = is_response_relevant(
                    user_input, 
                    "product criteria and specifications", 
                    product_context
                )
                
                if not relevance_check.get("is_relevant", True):
                    return {
                        "ask_user": f"I didn't understand your response in the context of finding {product_context}. "
                                   f"Could you please provide criteria like brand, price range, or features? "
                                   f"Or type 'cancel' to exit this purchase."
                    }
                
                preferences_data = analyze_user_preferences(user_input, self.search_results)
                
                self.contract["parameters"]["preferences"] = preferences_data.get("preferences", [])
                self.contract["parameters"]["constraints"] = preferences_data.get("constraints", {})
                
                has_compatibility = any(keyword in user_input.lower() for keyword in ["compatible", "compatibility", "works with", "fits"])
                
                if has_compatibility and preferences_data.get("constraints"):
                    self.logger.info(f"FSM (session: {session_id}): Compatibility requirements detected. Transition: wait_for_preferences → check_compatibility")
                    self.state = "check_compatibility"
                else:
                    self.logger.info(f"FSM (session: {session_id}): No compatibility requirements. Transition: wait_for_preferences → filter_products")
                    self.state = "filter_products"
                return self.next()
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error analyzing preferences: {e}")
                self.state = "rank_and_select"
                return self.next()

        elif self.state == "filter_products":
            try:
                from contract_engine.llm_helpers import filter_products_with_llm
                preferences = self.contract["parameters"].get("preferences", [])
                
                if preferences:
                    filtered_products = filter_products_with_llm(self.search_results, preferences)
                    self.search_results = filtered_products
                
                self.logger.info(f"FSM (session: {session_id}): Filtered to {len(self.search_results)} products. Transition: filter_products → rank_and_select")
                self.state = "rank_and_select"
                return self.next()
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error filtering products: {e}")
                self.state = "rank_and_select"
                return self.next()

        elif self.state == "check_compatibility":
            try:
                from contract_engine.llm_helpers import check_product_compatibility
                constraints = self.contract["parameters"].get("constraints", {})
                product_query = self.contract["parameters"].get("product")
                
                enhanced_products = self._enhance_with_web_search(self.search_results, constraints, product_query)
                
                compatibility_results = check_product_compatibility(enhanced_products, constraints, product_query)
                
                compatible_products = []
                for i, result in enumerate(compatibility_results):
                    if result.get("compatible", False) and i < len(enhanced_products):
                        compatible_products.append(enhanced_products[i])
                
                self.search_results = compatible_products
                
                if not self.search_results:
                    return {"ask_user": "No compatible products found. Would you like to adjust your requirements or try a different search?"}
                
                self.logger.info(f"FSM (session: {session_id}): Found {len(self.search_results)} compatible products. Transition: check_compatibility → rank_and_select")
                self.state = "rank_and_select"
                return self.next()
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error checking compatibility: {e}")
                self.state = "rank_and_select"
                return self.next()

        elif self.state == "rank_and_select":
            selected_product = self.rank_and_select(self.search_results, parameters.get("preferences"))
            
            self.logger.info(f"FSM (session: {session_id}): Selected product: {selected_product.get('name', 'None')}")
            self.contract.setdefault("subtasks", []).append({
                "id": "select_product",
                "type": "rank_and_select",
                "status": "completed",
                "output": selected_product 
            })
            self.selected_product_for_confirmation = selected_product

            self.logger.info(f"FSM (session: {session_id}): Transition: rank_and_select → confirm_order")
            self.state = "confirm_order"
            
            product_name = selected_product.get("name", "this product")
            product_price = selected_product.get("price")
            price_info = f" at {product_price} CHF" if product_price is not None else ""

            if not selected_product or not selected_product.get("name"):
                return {"ask_user": "No suitable product was found. Would you like to try a different search?"}
            else:
                return {"ask_user": f"Found: {product_name}{price_info}. Shall I go ahead and confirm this order?"}

        elif self.state == "confirm_order":
            self.logger.info(f"FSM (session: {session_id}): In confirm_order, user_input: '{user_input}'")
            
            try:
                from contract_engine.llm_helpers import is_cancel_request, is_response_relevant
                
                if is_cancel_request(user_input):
                    self.contract["status"] = "cancelled_by_user"
                    self.logger.info(f"FSM (session: {session_id}): Order cancelled by user.")
                    return {"status": "cancelled", "message": "Purchase cancelled. Is there anything else I can help you with?"}
                
                product_name = self.selected_product_for_confirmation.get("name", "the product")
                product_price = self.selected_product_for_confirmation.get("price", "price not available")
                product_context = f"{product_name} at {product_price} CHF"
                
                relevance_check = is_response_relevant(
                    user_input, 
                    "yes/no confirmation for product purchase", 
                    product_context
                )
                
                if not relevance_check.get("is_relevant", True):
                    return {
                        "ask_user": f"I didn't understand your response. Please answer 'yes' to confirm the purchase "
                                   f"of {product_name} at {product_price} CHF, 'no' to decline, or 'cancel' to exit."
                    }
                
                if user_input and user_input.lower() in ["yes", "y", "confirm", "ok", "okay", "proceed", "sure"]:
                    self.contract.setdefault("subtasks", []).append({
                        "id": "confirm_order",
                        "type": "confirmation",
                        "status": "completed",
                        "response": user_input
                    })
                    self.logger.info(f"FSM (session: {session_id}): Order confirmed by user. Transition: confirm_order → completed")
                    self.state = "completed"
                    return self.next() 
                elif user_input and user_input.lower() in ["no", "n", "decline", "reject"]:
                    self.contract["status"] = "cancelled_by_user"
                    self.logger.info(f"FSM (session: {session_id}): Order declined by user.")
                    return {"status": "cancelled", "message": "Order cancelled. Is there anything else I can help you with?"}
                else:
                    return {"ask_user": f"I didn't understand your response. Please answer 'yes' to confirm the purchase of {product_name} at {product_price} CHF, or 'no' to decline."}
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error in confirm_order: {e}")
                product_name = self.selected_product_for_confirmation.get('name', 'this product')
                return {"ask_user": f"Sorry, I didn't understand. Please confirm for {product_name} (yes/no)."}

        elif self.state == "completed":
            self.logger.info(f"FSM (session: {session_id}): Contract is completed.")
            self.contract["status"] = "completed"
            self.contract["order_confirmed"] = True 
            self.contract["completed_at"] = datetime.datetime.now().isoformat()

            try:
                artifact_dir = "tmp/contracts"
                os.makedirs(artifact_dir, exist_ok=True)
                artifact_path = os.path.join(artifact_dir, f"{session_id}.json")
                self.save_final_contract(filename=artifact_path)
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Failed to save final contract: {e}", exc_info=True)
            
            return {"status": "completed", "contract": self.contract}

        elif self.state == "cancelled":
            self.logger.info(f"FSM (session: {session_id}): Contract is in cancelled state.")
            self.contract["status"] = "cancelled"
            return {"status": "cancelled", "message": "The purchase has been cancelled. Is there anything else I can help you with?"}

        elif self.state == "error": 
            self.logger.error(f"FSM (session: {session_id}): FSM is in an error state, likely due to template loading failure.")
            return {"status": "failed", "message": "FSM critical error (e.g. template not loaded)."}

        else: 
            self.logger.error(f"FSM (session: {session_id}): Reached unknown state: {self.state}")
            self.contract["status"] = "failed"
            return {"status": "failed", "message": f"Contract entered an invalid state: {self.state}"}
    
    def _extract_attributes_from_analysis(self, analysis: str, product_query: str) -> List[str]:
        """Extract key attributes from LLM analysis"""
        common_attributes = {
            "gpu": ["memory", "cooling", "brand", "power consumption", "size"],
            "washing": ["capacity", "type", "energy rating", "size", "features"],
            "laptop": ["processor", "memory", "storage", "screen size", "battery"],
            "phone": ["storage", "camera", "battery", "screen size", "brand"]
        }
        
        query_lower = product_query.lower()
        for category, attrs in common_attributes.items():
            if category in query_lower:
                return attrs
        
        return ["brand", "price range", "features", "size"]
    
    def _enhance_with_web_search(self, products: List[Dict[str, Any]], constraints: Dict[str, Any], product_query: str) -> List[Dict[str, Any]]:
        """Enhance products with web search for compatibility information"""
        try:
            constraint_text = " ".join([f"{k} {v}" for k, v in constraints.items()])
            search_query = f"{product_query} {constraint_text} compatibility specifications"
            
            web_results = search_product(q=search_query)
            
            enhanced_products = products.copy()
            for product in enhanced_products:
                product["web_search_enhanced"] = True
                product["search_query_used"] = search_query
            
            return enhanced_products
        except Exception as e:
            self.logger.error(f"Web search enhancement failed: {e}")
            return products

    def rank_and_select(self, filtered_products: List[Dict[str, Any]], preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not filtered_products:
            self.logger.warning("rank_and_select called with no products.")
            return {
                "name": None, 
                "vendor": "unknown",
                "price": None,
                "product_id": None,
                "reason": "No matching products found to rank"
            }
        
        def score(p: Dict[str, Any]) -> tuple:
            return (-(p.get("rating") or 0), p.get("price") or float("inf")) 

        sorted_products = sorted(filtered_products, key=score)
        
        if not sorted_products: 
             self.logger.error("Sorting returned empty list from non-empty product list in rank_and_select.")
             return {"name": None, "vendor": "unknown", "price": None, "product_id": None, "reason": "Sorting failed or no products"}

        return sorted_products[0]

    def save_final_contract(self, filename="final_contract.json"): 
        self.contract["updated_at"] = datetime.datetime.now().isoformat() 
        try:
            with open(filename, "w") as f:
                json.dump(self.contract, f, indent=2)
            self.logger.info(f"Contract data saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving contract to {filename}: {e}", exc_info=True)

    def dispatch(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info(f"Dispatching to FSM in state '{self.state}' for session '{self.contract.get('parameters', {}).get('session_id', 'unknown')}' with input: '{user_input}'")
        
        fsm_response = self.next(user_input=user_input) 
        session_id = self.contract.get("parameters", {}).get("session_id", "unknown_session_in_fsm")

        if "ask_user" in fsm_response:
            return {"reply": fsm_response["ask_user"], "session_id": session_id}
        elif fsm_response.get("status") == "completed":
            summary = "Contract completed."
            try:
                selected_product_output = getattr(self, 'selected_product_for_confirmation', {})
                
                if selected_product_output and selected_product_output.get("name"):
                    product_name = selected_product_output.get("name", "the selected product")
                    product_price = selected_product_output.get("price")
                    price_str = f" at {product_price} CHF" if product_price is not None else ""
                    summary = f"Contract completed for {product_name}{price_str}."
                else: 
                    summary = f"Contract completed. Final state: {self.state} (No specific product confirmed)."
                
                self.logger.info(f"Contract completed for session {session_id}. Summary: {summary}")
            except Exception as e:
                self.logger.error(f"Error generating summary for completed contract (session {session_id}): {e}", exc_info=True)
                summary = "Contract completed (summary generation error)."
            return {"reply": summary, "session_id": session_id, "contract_completed": True}
        elif fsm_response.get("status") == "failed" or fsm_response.get("status") == "cancelled":
            status_message = fsm_response.get('message', f"Contract {fsm_response.get('status')}.")
            self.logger.warning(f"Contract {fsm_response.get('status')} for session {session_id}. Message: {status_message}")
            # Ensure the key "contract_failed" or "contract_cancelled" is dynamically set
            status_key = f"contract_{fsm_response.get('status')}" 
            return {"reply": status_message, "session_id": session_id, status_key: True}
        else: 
            self.logger.warning(f"FSM for session {session_id} returned unexpected response: {fsm_response}. Current state: '{self.state}'.")
            return {"reply": f"Processing... current step: {self.state}. Please wait or provide more information if stuck.", "session_id": session_id}

# Removed load_verbosity_from_config method
# Removed schema validation from __init__ for now
# Removed original print statements from next() and replaced with logger calls.
# Corrected datetime.now() to datetime.datetime.now()
# Made rank_and_select more robust for empty/None price in summary
# Added type hints for search_results and selected_product_for_confirmation
# Added type hint for load_template return
# Corrected dynamic key for failed/cancelled status in dispatch
# Added check for empty product_query in search state
# Added check for selected_product.get("name") before forming confirm_order message to avoid error on None
# Made sure price_info in confirm_order and dispatch summary handles price being None.
# Added check for FSM being in "error" state in next()
# Initialized self.search_results and self.selected_product_for_confirmation in __init__ to prevent AttributeError.
# Corrected `datetime.now()` to `datetime.datetime.now()`.
# Ensured `fill_parameters` uses `setdefault` correctly for the parameters dict.
# Added specific type hint `List[Dict[str, Any]]` for `filtered_products` in `rank_and_select`.
# Corrected `self.selected_product_for_confirmation.get('name', 'this product')` in `confirm_order` to use getattr for safety if `selected_product_for_confirmation` itself is not a dict (though it should be).
# Actually, `self.selected_product_for_confirmation` is initialized as `{}`, so `.get()` is safe.

# Final check of dispatch:
# If fsm_response.get("status") == "cancelled", the key will be "contract_cancelled": True. This is fine.
# If fsm_response.get("status") == "failed", the key will be "contract_failed": True. This is fine.
# The "else" case in dispatch should be a fallback for unexpected FSM responses not covered by "ask_user" or a final status.

# Corrected datetime.now() to datetime.datetime.now() in save_final_contract and completed state.Okay, I will proceed with the **Contract Engine Slimming (`contract_engine/contract_engine.py`)** subtask.

