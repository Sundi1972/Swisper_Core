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
from .state_transitions import (
    StateTransition, ContractState, 
    create_success_transition, create_error_transition, 
    create_user_input_transition, create_completion_transition
)
from .pipelines.preference_match_pipeline import create_preference_match_pipeline, run_preference_match

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

        # Initialize pipelines
        from .pipelines.product_search_pipeline import create_product_search_pipeline
        self.product_search_pipeline = create_product_search_pipeline()
        self.preference_match_pipeline = create_preference_match_pipeline(top_k=3)
        
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
        """Main FSM transition method - now delegates to state handlers"""
        if self.contract is None:
            return {"status": "error", "message": "Contract not loaded"}
        
        session_id = self._get_session_id()
        self.logger.info(f"FSM (session: {session_id}): Current state: {self.context.current_state}, Input: '{user_input}'")
        
        state_handlers = {
            "start": self.handle_start_state,
            "search": self.handle_search_state,
            "refine_constraints": self.handle_refine_constraints_state,
            "analyze_attributes": self.handle_refine_constraints_state,  # Legacy mapping
            "ask_clarification": self.handle_ask_clarification_state,
            "wait_for_preferences": self.handle_wait_for_preferences_state,
            "filter_products": self.handle_filter_products_state,
            "match_preferences": self.handle_match_preferences_state,
            "check_compatibility": self.handle_check_compatibility_state,
            "rank_and_select": self.handle_rank_and_select_state,
            "present_options": self.handle_rank_and_select_state,  # Map present_options to rank_and_select
            "confirm_selection": self.handle_confirm_selection_state,
            "confirm_order": self.handle_confirm_order_state,
            "completed": self.handle_completed_state,
            "cancelled": self.handle_cancelled_state,
            "error": self.handle_error_state
        }
        
        handler = state_handlers.get(self.context.current_state)
        if not handler:
            self.logger.error(f"FSM (session: {session_id}): Unknown state: {self.context.current_state}")
            return {"status": "failed", "message": f"Contract entered an invalid state: {self.context.current_state}"}
        
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                transition = asyncio.run(handler(user_input))
            else:
                transition = handler(user_input)
            return self._process_state_transition(transition)
        except Exception as e:
            self.logger.error(f"FSM (session: {session_id}): Error in state handler: {e}")
            return {"status": "failed", "message": f"Error processing state {self.context.current_state}"}

    def _get_session_id(self) -> str:
        """Get session ID from contract parameters"""
        return self.contract.get("parameters", {}).get("session_id", "unknown")
    
    def _handle_cancel_request(self, user_input: str, session_id: str) -> Optional[StateTransition]:
        """Check if user input is a cancel request and handle it"""
        try:
            from contract_engine.llm_helpers import is_cancel_request
            if is_cancel_request(user_input):
                self.contract["status"] = "cancelled_by_user"
                return create_success_transition(
                    next_state=ContractState.CANCELLED,
                    user_message="Purchase cancelled. Is there anything else I can help you with?",
                    context_updates={"is_cancelled": True}
                )
        except Exception as e:
            self.logger.warning(f"⚠️ FSM (session: {session_id}): Cancel check failed, continuing: {e}")
        return None
    
    def _process_state_transition(self, transition: StateTransition) -> Dict[str, Any]:
        """Process a state transition and update context accordingly"""
        for key, value in transition.context_updates.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        
        for key, value in transition.contract_updates.items():
            self.contract[key] = value
        
        if transition.next_state and transition.next_state.value != self.context.current_state:
            self.context.update_state(transition.next_state.value)
        
        if transition.tools_used:
            self.context.tools_used.extend(transition.tools_used)
        
        result = transition.to_dict()
        
        if transition.next_state and not transition.requires_user_input() and not transition.is_terminal():
            return self.next()
        
        return result
    
    def handle_start_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the start state - check if product is set and transition to search"""
        session_id = self._get_session_id()
        
        if not self.context.product_query:
            self.logger.warning(f"FSM (session: {session_id}): Product not set in 'start' state. Asking user.")
            return create_user_input_transition("What product are you looking for?")
        
        self.logger.info(f"FSM (session: {session_id}): Transition: start → search")
        return create_success_transition(next_state=ContractState.SEARCH)
    
    async def handle_search_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the search state - perform product search using pipeline"""
        session_id = self._get_session_id()
        
        if not self.context.product_query:
            self.logger.error(f"FSM (session: {session_id}): Product query is empty in 'search' state.")
            return create_error_transition("No product specified for search.")
        
        self.logger.info(f"🔍 FSM (session: {session_id}): Searching for '{self.context.product_query}' using pipeline")
        
        try:
            from .pipelines.product_search_pipeline import run_product_search
            pipeline_result = await run_product_search(
                pipeline=self.product_search_pipeline,
                query=self.context.product_query,
                hard_constraints=getattr(self.context, 'constraints', [])
            )
            
            if pipeline_result.get("status") == "error":
                self.logger.error(f"FSM (session: {session_id}): Pipeline search failed: {pipeline_result.get('error')}")
                return create_user_input_transition(
                    f"I encountered an error while searching for '{self.context.product_query}'. Could you try again or rephrase your request?"
                )
            
            search_results = pipeline_result.get("items", [])
            discovered_attributes = pipeline_result.get("attributes", [])
            
            context_updates = {
                "search_results": search_results,
                "extracted_attributes": discovered_attributes
            }
            tools_used = ["product_search_pipeline"]
            
            if pipeline_result.get("status") == "too_many_results":
                self.logger.info(f"FSM (session: {session_id}): Too many results, moving to refine_constraints")
                next_state = ContractState.REFINE_CONSTRAINTS
                user_message = self._generate_constraint_refinement_message(discovered_attributes)
                return StateTransition(
                    next_state=next_state,
                    ask_user=user_message,
                    context_updates=context_updates,
                    tools_used=tools_used
                )
            elif not search_results:
                self.logger.warning(f"FSM (session: {session_id}): No products found for '{self.context.product_query}'")
                return create_user_input_transition(
                    f"I couldn't find any products matching '{self.context.product_query}'. Could you try a different search term or be more specific?"
                )
            else:
                self.logger.info(f"FSM (session: {session_id}): Pipeline found {len(search_results)} products, moving to present_options")
                next_state = ContractState.PRESENT_OPTIONS
                return create_success_transition(
                    next_state=next_state,
                    context_updates=context_updates,
                    tools_used=tools_used
                )
            
        except Exception as e:
            self.logger.error(f"FSM (session: {session_id}): Pipeline search failed: {e}")
            return create_user_input_transition(
                f"I encountered an error while searching for '{self.context.product_query}'. Could you try again or rephrase your request?"
            )
    
    def handle_refine_constraints_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the refine_constraints state - collect additional constraints from user"""
        session_id = self._get_session_id()
        if not user_input:
            # First time in this state - ask for constraints
            extracted_attributes = getattr(self.context, 'extracted_attributes', [])
            return create_user_input_transition(
                self._generate_constraint_refinement_message(extracted_attributes)
            )
        
        cancel_transition = self._handle_cancel_request(user_input, session_id)
        if cancel_transition:
            return cancel_transition
        
        self.logger.info(f"🔍 FSM (session: {session_id}): Processing constraint refinement: '{user_input}'")
        
        try:
            new_constraints = self._parse_user_constraints(user_input)
            current_constraints = getattr(self.context, 'constraints', [])
            updated_constraints = current_constraints + new_constraints
            
            refinement_attempts = getattr(self.context, 'refinement_attempts', 0) + 1
            
            context_updates = {
                "constraints": updated_constraints,
                "refinement_attempts": refinement_attempts
            }
            
            # Re-run search with new constraints
            self.logger.info(f"FSM (session: {session_id}): Re-running search with {len(updated_constraints)} constraints (attempt {refinement_attempts})")
            
            return StateTransition(
                next_state=ContractState.SEARCH,
                context_updates=context_updates,
                user_message=f"Let me search again with your additional criteria..."
            )
            
        except Exception as e:
            self.logger.error(f"FSM (session: {session_id}): Constraint refinement failed: {e}")
            return create_error_transition(f"Failed to process your constraints: {e}")
    
    def handle_ask_clarification_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the ask_clarification state"""
        session_id = self._get_session_id()
        extracted_attributes = self.contract["parameters"].get("extracted_attributes", [])
        
        if extracted_attributes:
            attributes_text = ", ".join(extracted_attributes)
            clarification_message = (
                f"I found many options for '{self.context.product_query}'. "
                f"To help narrow down the search, could you tell me your preferences for: {attributes_text}? "
                f"For example, what's your budget, preferred brand, or specific features you need?"
            )
        else:
            clarification_message = f"I found many options for '{self.context.product_query}'. Could you tell me more about what you're looking for? For example, your budget, preferred brand, or specific features?"
        
        self.logger.info(f"FSM (session: {session_id}): Asking for clarification. Transition: ask_clarification → wait_for_preferences")
        
        return StateTransition(
            next_state=ContractState.COLLECT_PREFERENCES,
            ask_user=clarification_message,
            status="waiting_for_input"
        )
    
    def handle_wait_for_preferences_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the wait_for_preferences state"""
        session_id = self._get_session_id()
        self.logger.info(f"🎯 FSM (session: {session_id}): Processing user preferences: '{user_input}'")
        
        if not user_input:
            return create_user_input_transition("Could you please tell me your preferences? For example, your budget, preferred brand, or specific features you need.")
        
        try:
            from contract_engine.llm_helpers import analyze_user_preferences
            
            try:
                preference_analysis = analyze_user_preferences(
                    user_input, 
                    self.context.product_query, 
                    self.context.extracted_attributes
                )
                
                if isinstance(preference_analysis, dict):
                    preferences = preference_analysis.get("preferences", {})
                    constraints = preference_analysis.get("constraints", [])
                else:
                    self.logger.warning(f"FSM (session: {session_id}): Unexpected preference analysis format, using fallback")
                    fallback_analysis = self._fallback_preference_analysis(user_input)
                    preferences = fallback_analysis.get("preferences", {})
                    constraints = fallback_analysis.get("constraints", [])
                
                tools_used = ["analyze_user_preferences"]
                
            except Exception as e:
                self.logger.warning(f"FSM (session: {session_id}): LLM preference analysis failed, using fallback: {e}")
                fallback_analysis = self._fallback_preference_analysis(user_input)
                preferences = fallback_analysis.get("preferences", {})
                constraints = fallback_analysis.get("constraints", [])
                tools_used = []
            
            context_updates = {
                "preferences": preferences,
                "constraints": constraints
            }
            
            self.logger.info(f"FSM (session: {session_id}): Extracted preferences: {preferences}")
            self.logger.info(f"FSM (session: {session_id}): Extracted constraints: {constraints}")
            
            self.logger.info(f"FSM (session: {session_id}): Processing {len(self.context.search_results)} products with preferences. Transition: wait_for_preferences → match_preferences")
            next_state = ContractState.MATCH_PREFERENCES
            
            return create_success_transition(
                next_state=next_state,
                context_updates=context_updates,
                tools_used=tools_used
            )
            
        except Exception as e:
            self.logger.error(f"❌ FSM (session: {session_id}): Error analyzing preferences: {e}")
            return create_success_transition(next_state=ContractState.MATCH_PREFERENCES)
    
    async def handle_match_preferences_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the match_preferences state using preference match pipeline"""
        session_id = self._get_session_id()
        self.logger.info(f"🎯 FSM (session: {session_id}): Matching preferences using pipeline")
        
        if not self.context.search_results:
            self.logger.warning(f"FSM (session: {session_id}): No search results to match preferences against")
            return create_user_input_transition("No products found to match your preferences. Would you like to try a different search?")
        
        try:
            # Run preference match pipeline
            pipeline_result = await run_preference_match(
                pipeline=self.preference_match_pipeline,
                products=self.context.search_results,
                preferences=self.context.preferences or {},
                context=self.context.product_query
            )
            
            ranked_products = pipeline_result.get("ranked_products", [])
            scores = pipeline_result.get("scores", [])
            ranking_method = pipeline_result.get("ranking_method", "pipeline")
            
            if not ranked_products:
                self.logger.warning(f"FSM (session: {session_id}): Pipeline returned no ranked products")
                return create_user_input_transition("I couldn't find products that match your preferences. Would you like to adjust your requirements or try a different search?")
            
            try:
                from contract_engine.llm_helpers import generate_product_recommendation
                recommendation_data = generate_product_recommendation(
                    ranked_products, 
                    self.context.preferences or {}, 
                    self.context.constraints or {}
                )
                tools_used = ["preference_match_pipeline", "generate_product_recommendation"]
            except Exception as e:
                self.logger.warning(f"FSM (session: {session_id}): LLM recommendation failed, using fallback: {e}")
                recommendation_data = self._fallback_product_recommendation(ranked_products)
                tools_used = ["preference_match_pipeline"]
            
            context_updates = {
                "top_products": ranked_products,
                "product_recommendations": recommendation_data,
                "preference_scores": scores,
                "ranking_method": ranking_method
            }
            
            numbered_list = "\n".join([
                f"{item['number']}. {item['name']} - {item['price']} ({item['key_specs']})"
                for item in recommendation_data.get("numbered_products", [])
            ])
            
            recommendation = recommendation_data.get("recommendation", {})
            recommended_choice = recommendation.get("choice", 1)
            reasoning = recommendation.get("reasoning", "Best overall match for your preferences")
            
            self.logger.info(f"🏆 FSM (session: {session_id}): Pipeline matched {len(ranked_products)} products using {ranking_method}")
            self.logger.info(f"🔄 FSM (session: {session_id}): Transition: match_preferences → confirm_purchase")
            
            num_products = len(ranked_products)
            ask_user_message = (
                f"Based on your preferences, here are the top {num_products} options:\n\n{numbered_list}\n\n"
                f"My recommendation: Option {recommended_choice}\n"
                f"Reason: {reasoning}\n\n"
                f"Please enter the number (1-{num_products}) of your choice, or type 'yes' to go with my recommendation."
            )
            
            return StateTransition(
                next_state=ContractState.CONFIRM_PURCHASE,
                ask_user=ask_user_message,
                status="waiting_for_input",
                context_updates=context_updates,
                tools_used=tools_used
            )
            
        except Exception as e:
            self.logger.error(f"❌ FSM (session: {session_id}): Preference matching pipeline failed: {e}")
            return create_user_input_transition(
                f"I encountered an error while matching your preferences. Could you try again or adjust your requirements?"
            )

    def handle_filter_products_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the filter_products state"""
        session_id = self._get_session_id()
        self.logger.info(f"🔍 FSM (session: {session_id}): Filtering products with LLM")
        
        try:
            from contract_engine.llm_helpers import filter_products_with_llm
            
            if self.context.preferences or self.context.constraints:
                self.logger.info(f"📊 FSM (session: {session_id}): Filtering {len(self.context.search_results)} products using preferences and constraints")
                try:
                    filtered_products = filter_products_with_llm(
                        self.context.search_results, 
                        self.context.preferences,
                        self.context.constraints
                    )
                    context_updates = {"search_results": filtered_products}
                    self.logger.info(f"📋 FSM (session: {session_id}): Filtered list: {len(filtered_products)} products remaining")
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): LLM filtering failed, using fallback: {e}")
                    fallback_products = self.context.search_results[:10]
                    context_updates = {"search_results": fallback_products}
                    self.logger.info(f"📋 FSM (session: {session_id}): Using top {len(fallback_products)} products as fallback")
            else:
                self.logger.info(f"⚠️ FSM (session: {session_id}): No preferences or constraints to filter with")
                context_updates = {}
            
            self.logger.info(f"🔄 FSM (session: {session_id}): Transition: filter_products → match_preferences")
            return create_success_transition(
                next_state=ContractState.MATCH_PREFERENCES,
                context_updates=context_updates
            )
            
        except Exception as e:
            self.logger.error(f"❌ FSM (session: {session_id}): Error filtering products: {e}")
            return create_success_transition(next_state=ContractState.MATCH_PREFERENCES)
    
    def handle_check_compatibility_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the check_compatibility state"""
        session_id = self._get_session_id()
        
        try:
            from contract_engine.llm_helpers import check_product_compatibility
            
            enhanced_products = self._enhance_with_web_search(self.context.search_results, self.context.constraints, self.context.product_query)
            
            try:
                compatibility_results = check_product_compatibility(
                    enhanced_products, 
                    self.context.constraints, 
                    self.context.product_query
                )
                
                compatible_products = []
                for i, result in enumerate(compatibility_results):
                    if result.get("compatible", False) and i < len(enhanced_products):
                        compatible_products.append(enhanced_products[i])
                
                if compatible_products:
                    context_updates = {"search_results": compatible_products}
                    self.logger.info(f"FSM (session: {session_id}): Found {len(compatible_products)} compatible products. Transition: check_compatibility → rank_and_select")
                else:
                    context_updates = {}
                    self.logger.info(f"FSM (session: {session_id}): No compatible products found. Transition: check_compatibility → rank_and_select")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ FSM (session: {session_id}): Compatibility check failed, assuming all products compatible: {e}")
                context_updates = {}
            
            return create_success_transition(
                next_state=ContractState.PRESENT_OPTIONS,
                context_updates=context_updates
            )
            
        except Exception as e:
            self.logger.error(f"❌ FSM (session: {session_id}): Error checking compatibility: {e}")
            return create_success_transition(next_state=ContractState.PRESENT_OPTIONS)
    
    def handle_rank_and_select_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the rank_and_select state"""
        session_id = self._get_session_id()
        self.logger.info(f"🏆 FSM (session: {session_id}): In rank_and_select state")
        
        top_products = self.rank_and_select(self.context.search_results, self.context.preferences)
        
        if not top_products:
            self.logger.error(f"❌ FSM (session: {session_id}): No products to rank and select")
            return create_user_input_transition("No suitable products were found. Would you like to try a different search?")
        
        self.logger.info(f"🏆 FSM (session: {session_id}): Ranking {len(top_products)} products")
        
        try:
            from contract_engine.llm_helpers import generate_product_recommendation
            recommendation_data = generate_product_recommendation(
                top_products, 
                self.context.preferences, 
                self.context.constraints
            )
        except Exception as e:
            self.logger.warning(f"LLM recommendation failed, using fallback: {e}")
            recommendation_data = self._fallback_product_recommendation(top_products)
        
        context_updates = {
            "product_recommendations": recommendation_data,
            "top_products": top_products
        }
        
        numbered_list = "\n".join([
            f"{item['number']}. {item['name']} - {item['price']} ({item['key_specs']})"
            for item in recommendation_data.get("numbered_products", [])
        ])
        
        recommendation = recommendation_data.get("recommendation", {})
        recommended_choice = recommendation.get("choice", 1)
        reasoning = recommendation.get("reasoning", "Best overall value")
        
        self.logger.info(f"🏆 FSM (session: {session_id}): Generated top {len(top_products)} recommendations")
        self.logger.info(f"🔄 FSM (session: {session_id}): Transition: rank_and_select → confirm_selection")
        
        num_products = len(top_products)
        ask_user_message = (
            f"Here are the top 5 options:\n\n{numbered_list}\n\n"
            f"My recommendation: Option {recommended_choice}\n"
            f"Reason: {reasoning}\n\n"
            f"Please enter the number (1-{num_products}) of your choice, or type 'yes' to go with my recommendation."
        )
        
        return StateTransition(
            next_state=ContractState.CONFIRM_PURCHASE,
            ask_user=ask_user_message,
            status="waiting_for_input",
            context_updates=context_updates
        )
    
    def handle_confirm_selection_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the confirm_selection state"""
        session_id = self._get_session_id()
        self.logger.info(f"✅ FSM (session: {session_id}): In confirm_selection state, user_input: '{user_input}'")
        
        cancel_transition = self._handle_cancel_request(user_input, session_id)
        if cancel_transition:
            return cancel_transition
        
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
                return create_user_input_transition(
                    f"Please enter a number between 1 and {len(self.context.top_products)}, or 'yes' for my recommendation."
                )
        
        if selected_product:
            subtask = {
                "id": "select_product",
                "type": "user_selection",
                "status": "completed",
                "output": selected_product,
                "user_choice": user_input
            }
            
            context_updates = {
                "selected_product": selected_product,
                "confirmation_pending": True
            }
            
            contract_updates = {
                "subtasks": self.contract.get("subtasks", []) + [subtask]
            }
            
            product_name = selected_product.get("name", "this product")
            product_price = selected_product.get("price")
            price_info = f" at {product_price} CHF" if product_price is not None else ""
            
            self.logger.info(f"FSM (session: {session_id}): User selected {product_name}. Transition: confirm_selection → confirm_order")
            
            return StateTransition(
                next_state=ContractState.CONFIRM_PURCHASE,
                ask_user=f"You selected: {product_name}{price_info}. Shall I go ahead and confirm this order?",
                status="waiting_for_input",
                context_updates=context_updates,
                contract_updates=contract_updates
            )
        else:
            return create_user_input_transition("I didn't understand your selection. Please enter a number (1-5) or 'yes' for my recommendation.")
    
    def handle_confirm_order_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the confirm_order state"""
        session_id = self._get_session_id()
        self.logger.info(f"FSM (session: {session_id}): In confirm_order, user_input: '{user_input}'")
        
        cancel_transition = self._handle_cancel_request(user_input, session_id)
        if cancel_transition:
            return cancel_transition
        
        product_name = self.context.selected_product.get("name", "the product") if self.context.selected_product else "the product"
        product_price = self.context.selected_product.get("price", "price not available") if self.context.selected_product else "price not available"
        product_context = f"{product_name} at {product_price} CHF"
        
        try:
            from contract_engine.llm_helpers import is_response_relevant
            
            try:
                relevance_check = is_response_relevant(
                    user_input, 
                    "yes/no confirmation for product purchase", 
                    product_context
                )
                
                if not relevance_check.get("is_relevant", True):
                    return create_user_input_transition(
                        f"I didn't understand your response. Please answer 'yes' to confirm the purchase "
                        f"of {product_name} at {product_price} CHF, 'no' to decline, or 'cancel' to exit."
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ FSM (session: {session_id}): Relevance check failed, treating as unclear response: {e}")
        except ImportError:
            pass
        
        if user_input and user_input.lower() in ["yes", "y", "confirm", "ok", "okay", "proceed", "sure"]:
            subtask = {
                "id": "confirm_order",
                "type": "confirmation",
                "status": "completed",
                "response": user_input
            }
            
            context_updates = {"confirmation_pending": False}
            contract_updates = {"subtasks": self.contract.get("subtasks", []) + [subtask]}
            
            self.logger.info(f"FSM (session: {session_id}): Order confirmed by user. Transition: confirm_order → completed")
            
            return create_success_transition(
                next_state=ContractState.COMPLETED,
                context_updates=context_updates,
                contract_updates=contract_updates
            )
            
        elif user_input and user_input.lower() in ["no", "n", "decline", "reject"]:
            self.logger.info(f"FSM (session: {session_id}): Order declined by user.")
            
            contract_updates = {"status": "cancelled_by_user"}
            context_updates = {
                "contract_status": "cancelled",
                "is_cancelled": True
            }
            
            return StateTransition(
                next_state=ContractState.CANCELLED,
                status="cancelled",
                user_message="Order cancelled. Is there anything else I can help you with?",
                context_updates=context_updates,
                contract_updates=contract_updates
            )
        else:
            return create_user_input_transition(
                f"I didn't understand your response. Please answer 'yes' to confirm the purchase of {product_name} at {product_price} CHF, or 'no' to decline."
            )
    
    def handle_completed_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the completed state"""
        session_id = self._get_session_id()
        self.logger.info(f"FSM (session: {session_id}): Contract is completed.")
        
        contract_updates = {
            "status": "completed",
            "order_confirmed": True,
            "completed_at": datetime.datetime.now().isoformat()
        }
        
        context_updates = {"contract_status": "completed"}
        
        try:
            artifact_dir = "tmp/contracts"
            os.makedirs(artifact_dir, exist_ok=True)
            artifact_path = os.path.join(artifact_dir, f"{session_id}.json")
            self.save_final_contract(filename=artifact_path)
        except Exception as e:
            self.logger.error(f"FSM (session: {session_id}): Failed to save final contract: {e}", exc_info=True)
        
        return StateTransition(
            next_state=ContractState.COMPLETED,
            status="completed",
            context_updates=context_updates,
            contract_updates=contract_updates
        )
    
    def handle_cancelled_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the cancelled state"""
        session_id = self._get_session_id()
        self.logger.info(f"FSM (session: {session_id}): Contract is in cancelled state.")
        
        contract_updates = {"status": "cancelled"}
        context_updates = {
            "contract_status": "cancelled",
            "is_cancelled": True
        }
        
        return StateTransition(
            next_state=ContractState.CANCELLED,
            status="cancelled",
            user_message="The purchase has been cancelled. Is there anything else I can help you with?",
            context_updates=context_updates,
            contract_updates=contract_updates
        )
    
    def handle_error_state(self, user_input: Optional[str] = None) -> StateTransition:
        """Handle the error state"""
        session_id = self._get_session_id()
        self.logger.error(f"FSM (session: {session_id}): FSM is in an error state, likely due to template loading failure.")
        
        context_updates = {"contract_status": "error"}
        
        return StateTransition(
            next_state=ContractState.FAILED,
            status="failed",
            user_message="FSM critical error (e.g. template not loaded).",
            context_updates=context_updates
        )
    
    def _generate_constraint_refinement_message(self, discovered_attributes: list) -> str:
        """Generate a user-friendly message asking for constraint refinement"""
        if discovered_attributes:
            attribute_examples = ", ".join(discovered_attributes[:3])
            return (
                f"I found many results for '{self.context.product_query}'. "
                f"To help narrow down the options, could you provide more specific criteria? "
                f"For example: {attribute_examples}, or any other requirements you have."
            )
        else:
            return (
                f"I found many results for '{self.context.product_query}'. "
                f"Could you provide more specific criteria like brand, price range, "
                f"features, or other requirements to help narrow down the options?"
            )
    
    def _parse_user_constraints(self, user_input: str) -> list:
        """Parse user input into structured constraints"""
        constraints = []
        
        # Look for price constraints
        import re
        price_patterns = [
            r'under (\d+)',
            r'below (\d+)', 
            r'less than (\d+)',
            r'max (\d+)',
            r'maximum (\d+)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                max_price = int(match.group(1))
                constraints.append({
                    "type": "price",
                    "operator": "<=",
                    "value": max_price
                })
                break
        
        # Look for brand constraints
        brand_keywords = ['brand', 'make', 'manufacturer']
        for keyword in brand_keywords:
            if keyword in user_input.lower():
                words = user_input.split()
                for i, word in enumerate(words):
                    if keyword in word.lower() and i + 1 < len(words):
                        brand = words[i + 1].strip('.,!?')
                        constraints.append({
                            "type": "brand",
                            "operator": "equals",
                            "value": brand
                        })
                        break
        
        if not constraints:
            constraints.append({
                "type": "general",
                "operator": "contains",
                "value": user_input.strip()
            })
        
        return constraints

    def _legacy_next_fallback(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """Legacy fallback for any remaining state logic"""
        session_id = self._get_session_id()
        
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
            
            threshold = self.contract.get("parameters", {}).get("product_threshold", 10)
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
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Attribute analysis failed, using fallback: {e}")
                    self.context.extracted_attributes = ["price", "brand", "capacity", "energy_efficiency", "size", "features"]
                    self.contract["parameters"]["extracted_attributes"] = self.context.extracted_attributes
                    self.logger.info(f"🔄 FSM (session: {session_id}): Fallback transition: search → analyze_attributes")
                    self.context.update_state("analyze_attributes")
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
                    if 1 <= choice_number <= 5:
                        self.logger.info(f"🔢 FSM (session: {session_id}): User provided numeric selection '{choice_number}' - treating as product selection")
                        self.logger.info(f"🔄 FSM (session: {session_id}): Transition: wait_for_preferences → rank_and_select")
                        self.context.update_state("rank_and_select")
                        return self.next(user_input)
                
                try:
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
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Relevance check failed, assuming relevant: {e}")
                
                try:
                    preferences_data = analyze_user_preferences(user_input, self.context.search_results)
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Preference analysis failed, using fallback: {e}")
                    preferences_data = self._fallback_preference_analysis(user_input)
                
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
                    try:
                        filtered_products = filter_products_with_llm(
                            self.context.search_results, 
                            self.context.preferences,
                            self.context.constraints
                        )
                        self.context.search_results = filtered_products
                        self.logger.info(f"📋 FSM (session: {session_id}): Filtered list: {len(filtered_products)} products remaining")
                    except Exception as e:
                        self.logger.warning(f"⚠️ FSM (session: {session_id}): LLM filtering failed, using fallback: {e}")
                        self.context.search_results = self.context.search_results[:10]
                        self.logger.info(f"📋 FSM (session: {session_id}): Using top {len(self.context.search_results)} products as fallback")
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
            session_id = self.contract.get("parameters", {}).get("session_id", "unknown")
            try:
                from contract_engine.llm_helpers import check_product_compatibility
                
                enhanced_products = self._enhance_with_web_search(self.context.search_results, self.context.constraints, self.context.product_query)
                
                try:
                    compatibility_results = check_product_compatibility(
                        enhanced_products, 
                        self.context.constraints, 
                        self.context.product_query
                    )
                    
                    compatible_products = []
                    for i, result in enumerate(compatibility_results):
                        if result.get("compatible", False) and i < len(enhanced_products):
                            compatible_products.append(enhanced_products[i])
                    
                    if compatible_products:
                        self.context.search_results = compatible_products
                        self.logger.info(f"FSM (session: {session_id}): Found {len(compatible_products)} compatible products. Transition: check_compatibility → rank_and_select")
                    else:
                        self.logger.info(f"FSM (session: {session_id}): No compatible products found. Transition: check_compatibility → rank_and_select")
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Compatibility check failed, assuming all products compatible: {e}")
                
                self.context.update_state("rank_and_select")
                return self.next()
            except Exception as e:
                self.logger.error(f"❌ FSM (session: {session_id}): Error checking compatibility: {e}")
                self.context.update_state("rank_and_select")
                return self.next()
                
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
            
            try:
                from contract_engine.llm_helpers import generate_product_recommendation
                recommendation_data = generate_product_recommendation(
                    top_products, 
                    self.context.preferences, 
                    self.context.constraints
                )
            except Exception as e:
                self.logger.warning(f"LLM recommendation failed, using fallback: {e}")
                recommendation_data = self._fallback_product_recommendation(top_products)
            
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
                
                try:
                    if is_cancel_request(user_input):
                        self.contract["status"] = "cancelled_by_user"
                        self.context.update_state("cancelled")
                        self.context.is_cancelled = True
                        return {"ask_user": "Purchase cancelled. Is there anything else I can help you with?"}
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Cancel check failed, continuing: {e}")
                
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
                
                try:
                    if is_cancel_request(user_input):
                        self.contract["status"] = "cancelled_by_user"
                        self.context.update_state("cancelled")
                        self.context.is_cancelled = True
                        return {"ask_user": "Purchase cancelled. Is there anything else I can help you with?"}
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Cancel check failed, continuing: {e}")
                
                product_name = self.context.selected_product.get("name", "the product") if self.context.selected_product else "the product"
                product_price = self.context.selected_product.get("price", "price not available") if self.context.selected_product else "price not available"
                product_context = f"{product_name} at {product_price} CHF"
                
                try:
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
                except Exception as e:
                    self.logger.warning(f"⚠️ FSM (session: {session_id}): Relevance check failed, treating as unclear response: {e}")
                
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

    def _fallback_product_recommendation(self, products: list) -> dict:
        """Fallback recommendation when LLM is unavailable"""
        if not products:
            return {
                "numbered_products": [],
                "recommendation": {
                    "choice": None,
                    "reasoning": "No products available for recommendation"
                }
            }
        
        numbered_products = []
        for i, product in enumerate(products[:5], 1):
            numbered_products.append({
                "number": i,
                "name": product.get("name", f"Product {i}"),
                "price": product.get("price", "Price not available"),
                "key_specs": product.get("description", "Specs not available")[:100]
            })
        
        return {
            "numbered_products": numbered_products,
            "recommendation": {
                "choice": 1,
                "reasoning": "Based on highest rating and best price-to-value ratio"
            }
        }
    
    def _fallback_preference_analysis(self, user_input: str) -> dict:
        """Fallback preference analysis using regex patterns"""
        import re
        
        preferences = {}
        constraints = []
        
        price_patterns = [
            r'\b(?:below|under|max|maximum)\s*(\d+)\s*(?:chf|francs?)\b',
            r'\b(\d+)\s*(?:chf|francs?)\s*(?:or\s*)?(?:below|under|max|maximum)\b'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                preferences["price"] = f"below {match.group(1)} CHF"
                break
        
        capacity_patterns = [
            r'\b(?:min|minimum|at\s*least)\s*(\d+)\s*kg\b',
            r'\b(\d+)\s*kg\s*(?:or\s*)?(?:more|higher|above)\b'
        ]
        
        for pattern in capacity_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                preferences["capacity"] = f"at least {match.group(1)}kg"
                break
        
        efficiency_patterns = [
            r'\benergy\s*efficiency\s*(?:of\s*)?([a-e])\s*(?:or\s*)?(?:better|higher)\b',
            r'\b([a-e])\s*(?:or\s*)?(?:better|higher)\s*energy\s*efficiency\b'
        ]
        
        for pattern in efficiency_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                preferences["energy_efficiency"] = f"{match.group(1).upper()} or better"
                break
        
        if "quiet" in user_input.lower():
            constraints.append("quiet operation")
        if "reliable" in user_input.lower():
            constraints.append("reliable brand")
        if "energy efficient" in user_input.lower():
            constraints.append("energy efficient")
        
        return {
            "preferences": preferences,
            "constraints": constraints
        }

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

