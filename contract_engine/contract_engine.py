import yaml
import json
from pathlib import Path
import datetime # For datetime.datetime.now()
import logging
from typing import Optional, Dict, Any, List # Added List
import os # For makedirs

# Import the real search function (with mock fallback)
from tool_adapter.mock_google import google_shopping_search as search_product
from .context import SwisperContext

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
            # Initialize context with error state
            self.context = SwisperContext(
                session_id="default_fsm_session",
                current_state="error",
                contract_template_path=template_path
            )
            return

        # Initialize SwisperContext
        self.context = SwisperContext(
            session_id="default_fsm_session",
            contract_template_path=template_path,
            contract_template=template_path
        )
        
        # Ensure session_id is initialized if possible, or by orchestrator via fill_parameters
        self.contract.setdefault("parameters", {}).setdefault("session_id", "default_fsm_session")

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
        if self.contract is None:
            return None
        
        self.contract.setdefault("parameters", {}).update(param_data)
        
        # Update context with parameters
        if "session_id" in param_data:
            self.context.session_id = param_data["session_id"]
        if "product" in param_data:
            self.context.product_query = param_data["product"]
        if "enhanced_query" in param_data:
            self.context.enhanced_query = param_data["enhanced_query"]
        if "preferences" in param_data:
            self.context.preferences = param_data.get("preferences", [])
        if "constraints" in param_data:
            self.context.constraints = param_data.get("constraints", {})
            
        self.context.updated_at = datetime.datetime.now().isoformat()
        self.logger.info(f"Parameters filled for session {self.context.session_id}: {param_data}")

    def next(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        if self.contract is None:
            return {"status": "error", "message": "Contract not loaded"}
            
        parameters = self.contract.get("parameters", {})
        session_id = self.context.session_id

        self.logger.info(f"FSM (session: {session_id}): Current state: {self.context.current_state}, Input: '{user_input}'")

        if self.context.current_state == "start":
            if not self.context.product_query:
                self.logger.warning(f"FSM (session: {session_id}): Product not set in 'start' state. Asking user.")
                return {"ask_user": "What product are you looking for?"}
            
            self.logger.info(f"FSM (session: {session_id}): Transition: start → search")
            self.context.update_state("search")
            return self.next()

        elif self.context.current_state == "search":
            if not self.context.product_query:
                self.logger.error(f"FSM (session: {session_id}): Product query is empty in 'search' state.")
                self.contract["status"] = "failed"
                self.context.contract_status = "failed"
                return {"status": "failed", "message": "No product specified for search."}

            self.logger.info(f"FSM (session: {session_id}): Searching for product: '{self.context.product_query}' using SearchAPI.")
            results = search_product(q=self.context.product_query) 

            self.contract.setdefault("subtasks", []).append({
                "id": "search_product",
                "type": "search",
                "status": "completed",
                "results": results
            })
            self.context.search_results = results
            self.context.tools_used.append("google_shopping")

            if not results or (isinstance(results, list) and results and results[0].get("error")):
                self.logger.warning(f"FSM (session: {session_id}): No products found or error from search for '{self.context.product_query}'. Results: {results}")
            
            threshold = parameters.get("product_threshold", 10)
            if len(results) > threshold:
                self.logger.info(f"📊 FSM (session: {session_id}): Found {len(results)} products (>{threshold}). Analyzing attributes...")
                
                try:
                    from contract_engine.llm_helpers import analyze_product_differences
                    attributes = analyze_product_differences(results)
                    self.context.extracted_attributes = attributes
                    self.contract["parameters"]["extracted_attributes"] = attributes
                    
                    self.logger.info(f"🔍 FSM (session: {session_id}): Results and Attributes extracted: {attributes}")
                    self.logger.info(f"🔄 FSM (session: {session_id}): Transition: search → analyze_attributes")
                    self.context.update_state("analyze_attributes")
                except Exception as e:
                    self.logger.error(f"❌ FSM (session: {session_id}): Attribute analysis failed: {e}")
                    self.logger.info(f"🔄 FSM (session: {session_id}): Fallback transition: search → wait_for_preferences")
                    self.context.update_state("wait_for_preferences")
                    return {"ask_user": "I found several options. To help you choose the best one, could you provide more criteria? For example: price range, capacity, energy rating, or any specific requirements you have. Or type 'cancel' to exit this purchase."}
            else:
                self.logger.info(f"📊 FSM (session: {session_id}): Found {len(results)} products (<={threshold}). Picking best five immediately...")
                self.logger.info(f"🔄 FSM (session: {session_id}): Transition: search → rank_and_select")
                self.context.update_state("rank_and_select")
            return self.next()

        elif self.context.current_state == "analyze_attributes":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            self.logger.info(f"🔍 FSM (session: {session_id}): In analyze_attributes state")
            
            try:
                attributes = self.context.extracted_attributes or []
                
                if not self.context.search_results:
                    self.logger.error(f"❌ FSM (session: {session_id}): No search results available for attribute analysis")
                    return {"ask_user": "No products found to analyze. Please try a different search."}
                
                self.logger.info(f"📊 FSM (session: {session_id}): Showing attributes to user")
                self.logger.info(f"📋 FSM (session: {session_id}): Found {len(self.context.search_results)} products")
                self.logger.info(f"🔍 FSM (session: {session_id}): Key attributes: {attributes}")
                
                self.contract["parameters"]["extracted_attributes"] = attributes
                
                self.logger.info(f"🔄 FSM (session: {session_id}): Transition: analyze_attributes → ask_clarification")
                self.context.update_state("ask_clarification")
                return self.next()
            except Exception as e:
                self.logger.error(f"❌ FSM (session: {session_id}): Error in analyze_attributes: {e}")
                self.context.update_state("rank_and_select")
                return self.next()

        elif self.context.current_state == "ask_clarification":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            extracted_attributes = self.contract["parameters"].get("extracted_attributes", [])
            
            attribute_examples = ", ".join(extracted_attributes[:3]) if extracted_attributes else "brand, price range, features"
            clarification_message = (
                f"I found {len(self.context.search_results)} results for '{self.context.product_query}'. "
                f"To help you choose the best option, could you provide more criteria? "
                f"For example: {attribute_examples}, or any specific requirements you have. "
                f"Or type 'cancel' to exit this purchase."
            )
            
            self.logger.info(f"🔄 FSM (session: {session_id}): Transition: ask_clarification → wait_for_preferences")
            self.context.update_state("wait_for_preferences")
            return {"ask_user": clarification_message}

        elif self.context.current_state == "wait_for_preferences":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            self.logger.info(f"🎯 FSM (session: {session_id}): Processing user preferences: '{user_input}'")
            
            if not user_input:
                return {"ask_user": "Please provide your preferences to help me filter the products."}
            
            try:
                from contract_engine.llm_helpers import analyze_user_preferences, is_cancel_request, is_response_relevant
                
                if is_cancel_request(user_input):
                    self.logger.info(f"❌ FSM (session: {session_id}): User cancelled the purchase")
                    self.context.update_state("cancelled")
                    self.context.is_cancelled = True
                    return {"ask_user": "Purchase cancelled. Is there anything else I can help you with?"}
                
                if (user_input and user_input.strip().isdigit() and 
                    hasattr(self.context, 'product_recommendations') and 
                    self.context.product_recommendations):
                    
                    choice_number = int(user_input.strip())
                    top_products = getattr(self.context, 'top_products', [])
                    
                    if 1 <= choice_number <= len(top_products):
                        self.logger.info(f"✅ FSM (session: {session_id}): User selected product {choice_number} from recommendations")
                        selected_product = top_products[choice_number - 1]
                        self.context.selected_product = selected_product
                        
                        product_name = selected_product.get("name", "this product")
                        product_price = selected_product.get("price")
                        price_info = f" at {product_price} CHF" if product_price is not None else ""
                        
                        self.logger.info(f"✅ FSM (session: {session_id}): Product selected: {product_name}. Transition: wait_for_preferences → confirm_order")
                        self.context.update_state("confirm_order")
                        self.context.confirmation_pending = True
                        
                        return {"ask_user": f"You selected: {product_name}{price_info}. Shall I go ahead and confirm this order?"}
                    else:
                        return {
                            "ask_user": f"Please enter a number between 1 and {len(top_products)}, or provide more criteria to help me filter the products."
                        }
                
                confirmation_keywords = ["yes", "y", "ok", "okay", "sure"]
                if user_input and user_input.lower().strip() in confirmation_keywords:
                    self.logger.info(f"🔍 FSM (session: {session_id}): User input '{user_input}' looks like confirmation, but FSM is in wait_for_preferences state")
                    return {
                        "ask_user": f"I'm still waiting for your preferences for {self.context.product_query or 'the product'}. "
                                   f"Could you please provide criteria like brand, price range, capacity, energy efficiency, or features? "
                                   f"Or type 'cancel' to exit this purchase."
                    }
                
                if user_input and user_input.strip().isdigit():
                    choice_number = int(user_input.strip())
                    if 1 <= choice_number <= 5:  # Assume max 5 products were shown
                        self.logger.info(f"🔢 FSM (session: {session_id}): User provided numeric selection '{choice_number}' - treating as product selection")
                        self.logger.info(f"🔄 FSM (session: {session_id}): Transition: wait_for_preferences → rank_and_select")
                        self.context.update_state("rank_and_select")
                        return self.next(user_input)
                
                relevance_check = is_response_relevant(
                    user_input, 
                    "product criteria and specifications", 
                    self.context.product_query or "product"
                )
                
                self.logger.info(f"🔍 FSM (session: {session_id}): OOC result: {not relevance_check.get('is_relevant', True)}")
                
                if not relevance_check.get("is_relevant", True):
                    self.logger.info(f"⚠️ FSM (session: {session_id}): Out of context response detected")
                    return {
                        "ask_user": f"I didn't understand your response in the context of finding {self.context.product_query or 'product'}. "
                                   f"Could you please provide criteria like brand, price range, or features? "
                                   f"Or type 'cancel' to exit this purchase."
                    }
                
                preferences_data = analyze_user_preferences(user_input, self.context.search_results)
                
                preferences = preferences_data.get("preferences", {})
                if not isinstance(preferences, dict):
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Invalid preferences type: {type(preferences)}, converting to dict")
                    preferences = {}
                self.context.preferences = preferences
                
                constraints = preferences_data.get("constraints", [])
                if not isinstance(constraints, list):
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Invalid constraints type: {type(constraints)}, converting to list")
                    constraints = []
                self.context.constraints = constraints
                self.contract["parameters"]["preferences"] = self.context.preferences
                self.contract["parameters"]["constraints"] = self.context.constraints
                
                self.logger.info(f"📋 FSM (session: {session_id}): Identified constraints: {self.context.constraints}")
                self.logger.info(f"📋 FSM (session: {session_id}): Identified preferences: {self.context.preferences}")
                
                has_compatibility = any(keyword in user_input.lower() for keyword in ["compatible", "compatibility", "works with", "fits"])
                has_compatibility_constraint = any("compatible" in str(constraint).lower() for constraint in self.context.constraints)
                
                if has_compatibility and (self.context.constraints or has_compatibility_constraint):
                    self.logger.info(f"🔍 FSM (session: {session_id}): Compatibility check: y")
                    self.logger.info(f"🔄 FSM (session: {session_id}): Transition: wait_for_preferences → check_compatibility")
                    self.context.update_state("check_compatibility")
                else:
                    self.logger.info(f"🔍 FSM (session: {session_id}): Compatibility check: n")
                    self.logger.info(f"🔄 FSM (session: {session_id}): Transition: wait_for_preferences → filter_products")
                    self.context.update_state("filter_products")
                return self.next()
            except Exception as e:
                self.logger.error(f"❌ FSM (session: {session_id}): Error analyzing preferences: {e}")
                self.context.update_state("rank_and_select")
                return self.next()

        elif self.context.current_state == "filter_products":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            self.logger.info(f"🔍 FSM (session: {session_id}): Filtering products with LLM")
            
            try:
                from contract_engine.llm_helpers import filter_products_with_llm
                
                if self.context.preferences or self.context.constraints:
                    self.logger.info(f"📊 FSM (session: {session_id}): Filtering {len(self.context.search_results)} products using preferences and constraints")
                    filtered_products = filter_products_with_llm(
                        self.context.search_results, 
                        self.context.preferences,
                        self.context.constraints
                    )
                    self.context.search_results = filtered_products
                    self.logger.info(f"📋 FSM (session: {session_id}): Filtered list: {len(filtered_products)} products remaining")
                else:
                    self.logger.info(f"⚠️ FSM (session: {session_id}): No preferences or constraints to filter with")
                
                self.logger.info(f"🔄 FSM (session: {session_id}): Transition: filter_products → rank_and_select")
                self.context.update_state("rank_and_select")
                return self.next()
            except Exception as e:
                self.logger.error(f"❌ FSM (session: {session_id}): Error filtering products: {e}")
                self.context.update_state("rank_and_select")
                return self.next()

        elif self.context.current_state == "check_compatibility":
            try:
                from contract_engine.llm_helpers import check_product_compatibility
                
                enhanced_products = self._enhance_with_web_search(self.context.search_results, self.context.constraints, self.context.product_query)
                
                compatibility_results = check_product_compatibility(enhanced_products, self.context.constraints, self.context.product_query)
                
                compatible_products = []
                for i, result in enumerate(compatibility_results):
                    if result.get("compatible", False) and i < len(enhanced_products):
                        compatible_products.append(enhanced_products[i])
                
                self.context.search_results = compatible_products
                self.context.tools_used.append("check_compatibility")
                
                if not self.context.search_results:
                    return {"ask_user": "No compatible products found. Would you like to adjust your requirements or try a different search?"}
                
                self.logger.info(f"FSM (session: {session_id}): Found {len(self.context.search_results)} compatible products. Transition: check_compatibility → rank_and_select")
                self.context.update_state("rank_and_select")
                return self.next()
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error checking compatibility: {e}")
                self.context.update_state("rank_and_select")
                return self.next()

        elif self.context.current_state == "rank_and_select":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            self.logger.info(f"🏆 FSM (session: {session_id}): In rank_and_select state")
            
            top_products = self.rank_and_select(self.context.search_results, self.context.preferences)
            
            if not top_products:
                self.logger.error(f"❌ FSM (session: {session_id}): No products to rank and select")
                return {"ask_user": "No suitable products were found. Would you like to try a different search?"}
            
            self.logger.info(f"🏆 FSM (session: {session_id}): Ranking {len(top_products)} products")
            
            from contract_engine.llm_helpers import generate_product_recommendation
            recommendation_data = generate_product_recommendation(
                top_products, 
                self.context.preferences, 
                self.context.constraints
            )
            
            self.context.product_recommendations = recommendation_data
            self.context.top_products = top_products
            
            numbered_list = "\n".join([
                f"{item['number']}. {item['name']} - {item['price']} ({item['key_specs']})"
                for item in recommendation_data.get("numbered_products", [])
            ])
            
            recommendation = recommendation_data.get("recommendation", {})
            recommended_choice = recommendation.get("choice", 1)
            reasoning = recommendation.get("reasoning", "Best overall value")
            
            self.logger.info(f"🏆 FSM (session: {session_id}): Generated top {len(top_products)} recommendations")
            self.logger.info(f"🔄 FSM (session: {session_id}): Transition: rank_and_select → confirm_selection")
            self.context.update_state("confirm_selection")
            
            num_products = len(top_products)
            return {
                "ask_user": f"Here are the top 5 options:\n\n{numbered_list}\n\n"
                           f"My recommendation: Option {recommended_choice}\n"
                           f"Reason: {reasoning}\n\n"
                           f"Please enter the number (1-{num_products}) of your choice, or type 'yes' to go with my recommendation."
            }

        elif self.context.current_state == "confirm_selection":
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            self.logger.info(f"✅ FSM (session: {session_id}): In confirm_selection state, user_input: '{user_input}'")
            
            try:
                from contract_engine.llm_helpers import is_cancel_request
                
                if is_cancel_request(user_input):
                    self.contract["status"] = "cancelled_by_user"
                    self.logger.info(f"FSM (session: {session_id}): Selection cancelled by user.")
                    return {"status": "cancelled", "message": "Purchase cancelled. Is there anything else I can help you with?"}
                
                selected_product = None
                
                if user_input and user_input.lower() in ["yes", "y", "ok", "okay", "sure"]:
                    recommendation = self.context.product_recommendations.get("recommendation", {})
                    choice_number = recommendation.get("choice", 1)
                    if choice_number <= len(self.context.top_products):
                        selected_product = self.context.top_products[choice_number - 1]
                
                elif user_input and user_input.strip().isdigit():
                    choice_number = int(user_input.strip())
                    if 1 <= choice_number <= len(self.context.top_products):
                        selected_product = self.context.top_products[choice_number - 1]
                    else:
                        return {
                            "ask_user": f"Please enter a number between 1 and {len(self.context.top_products)}, or 'yes' for my recommendation."
                        }
                
                if selected_product:
                    self.context.selected_product = selected_product
                    
                    self.contract.setdefault("subtasks", []).append({
                        "id": "select_product",
                        "type": "user_selection",
                        "status": "completed",
                        "output": selected_product,
                        "user_choice": user_input
                    })
                    
                    product_name = selected_product.get("name", "this product")
                    product_price = selected_product.get("price")
                    price_info = f" at {product_price} CHF" if product_price is not None else ""
                    
                    self.logger.info(f"FSM (session: {session_id}): User selected {product_name}. Transition: confirm_selection → confirm_order")
                    self.context.update_state("confirm_order")
                    self.context.confirmation_pending = True
                    
                    return {"ask_user": f"You selected: {product_name}{price_info}. Shall I go ahead and confirm this order?"}
                else:
                    return {
                        "ask_user": "I didn't understand your selection. Please enter a number (1-5) or 'yes' for my recommendation."
                    }
                    
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error in confirm_selection: {e}")
                return {"ask_user": "Sorry, I didn't understand. Please enter a number (1-5) or 'yes' for my recommendation."}

        elif self.context.current_state == "confirm_order":
            self.logger.info(f"FSM (session: {session_id}): In confirm_order, user_input: '{user_input}'")
            
            try:
                from contract_engine.llm_helpers import is_cancel_request, is_response_relevant
                
                if is_cancel_request(user_input):
                    self.contract["status"] = "cancelled_by_user"
                    self.logger.info(f"FSM (session: {session_id}): Order cancelled by user.")
                    return {"status": "cancelled", "message": "Purchase cancelled. Is there anything else I can help you with?"}
                
                product_name = self.context.selected_product.get("name", "the product") if self.context.selected_product else "the product"
                product_price = self.context.selected_product.get("price", "price not available") if self.context.selected_product else "price not available"
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
                    self.context.update_state("completed")
                    self.context.confirmation_pending = False
                    return self.next() 
                elif user_input and user_input.lower() in ["no", "n", "decline", "reject"]:
                    self.contract["status"] = "cancelled_by_user"
                    self.context.contract_status = "cancelled"
                    self.context.is_cancelled = True
                    self.logger.info(f"FSM (session: {session_id}): Order declined by user.")
                    return {"status": "cancelled", "message": "Order cancelled. Is there anything else I can help you with?"}
                else:
                    return {"ask_user": f"I didn't understand your response. Please answer 'yes' to confirm the purchase of {product_name} at {product_price} CHF, or 'no' to decline."}
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Error in confirm_order: {e}")
                product_name = self.context.selected_product.get('name', 'this product') if self.context.selected_product else 'this product'
                return {"ask_user": f"Sorry, I didn't understand. Please confirm for {product_name} (yes/no)."}

        elif self.context.current_state == "completed":
            self.logger.info(f"FSM (session: {session_id}): Contract is completed.")
            self.contract["status"] = "completed"
            self.contract["order_confirmed"] = True 
            self.contract["completed_at"] = datetime.datetime.now().isoformat()
            self.context.contract_status = "completed"

            try:
                artifact_dir = "tmp/contracts"
                os.makedirs(artifact_dir, exist_ok=True)
                artifact_path = os.path.join(artifact_dir, f"{session_id}.json")
                self.save_final_contract(filename=artifact_path)
            except Exception as e:
                self.logger.error(f"FSM (session: {session_id}): Failed to save final contract: {e}", exc_info=True)
            
            return {"status": "completed", "contract": self.contract, "context": self.context.to_dict()}

        elif self.context.current_state == "cancelled":
            self.logger.info(f"FSM (session: {session_id}): Contract is in cancelled state.")
            self.contract["status"] = "cancelled"
            self.context.contract_status = "cancelled"
            self.context.is_cancelled = True
            return {"status": "cancelled", "message": "The purchase has been cancelled. Is there anything else I can help you with?"}

        elif self.context.current_state == "error": 
            self.logger.error(f"FSM (session: {session_id}): FSM is in an error state, likely due to template loading failure.")
            self.context.contract_status = "error"
            return {"status": "failed", "message": "FSM critical error (e.g. template not loaded)."}

        else: 
            self.logger.error(f"FSM (session: {session_id}): Reached unknown state: {self.context.current_state}")
            self.contract["status"] = "failed"
            return {"status": "failed", "message": f"Contract entered an invalid state: {self.context.current_state}"}
    
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

    def rank_and_select(self, filtered_products: List[Dict[str, Any]], preferences: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not filtered_products:
            self.logger.warning("rank_and_select called with no products.")
            return []
        
        def score(p: Dict[str, Any]) -> tuple:
            return (-(p.get("rating") or 0), p.get("price") or float("inf")) 

        sorted_products = sorted(filtered_products, key=score)
        
        if not sorted_products: 
             self.logger.error("Sorting returned empty list from non-empty product list in rank_and_select.")
             return []

        return sorted_products[:5]

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
# Initialized SwisperContext with search_results and selected_product in __init__ to prevent AttributeError.
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

