from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging
import json
from ..models import ContractState, Product
from ..config import settings

logger = logging.getLogger(__name__)

class ContractWorkflow:
    """
    LangGraph-based contract workflow replacing the original FSM.
    Handles: product search → ranking → selection → confirmation → completion
    """
    
    def __init__(self):
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.3
            )
        else:
            self.llm = None
            logger.warning("Contract workflow initialized without OpenAI API key - using fallback ranking")
        
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(ContractState)
        
        workflow.add_node("search_products", self._search_products)
        workflow.add_node("rank_products", self._rank_products)
        workflow.add_node("present_options", self._present_options)
        workflow.add_node("confirm_selection", self._confirm_selection)
        workflow.add_node("complete_order", self._complete_order)
        workflow.add_node("handle_error", self._handle_error)
        
        workflow.set_entry_point("search_products")
        
        workflow.add_edge("search_products", "rank_products")
        workflow.add_edge("rank_products", "present_options")
        
        workflow.add_conditional_edges(
            "present_options",
            self._should_proceed_to_confirmation,
            {
                "confirm": "confirm_selection",
                "search_again": "search_products",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "confirm_selection",
            self._should_complete_order,
            {
                "complete": "complete_order",
                "modify": "present_options",
                "cancel": END
            }
        )
        
        workflow.add_edge("complete_order", END)
        workflow.add_edge("handle_error", END)
        
        return workflow
    
    async def _search_products(self, state: ContractState) -> Dict[str, Any]:
        """Search for products based on user query."""
        try:
            logger.info(f"Searching products for query: {state.user_query}")
            
            mock_products = await self._mock_product_search(state.user_query)
            
            return {
                "search_results": mock_products,
                "current_step": "search_completed"
            }
            
        except Exception as e:
            logger.error(f"Error in product search: {e}", exc_info=True)
            return {
                "error_message": f"Product search failed: {str(e)}",
                "current_step": "error"
            }
    
    async def _rank_products(self, state: ContractState) -> Dict[str, Any]:
        """Rank and filter products using LLM or fallback ranking."""
        try:
            if not state.search_results:
                return {
                    "error_message": "No products found to rank",
                    "current_step": "error"
                }
            
            if self.llm:
                ranking_prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a product ranking expert. Rank the given products based on how well they match the user's query.
                    
Consider:
- Relevance to user query
- Price appropriateness
- Product quality indicators (ratings, reviews)
- User intent and context

Return the top 3 products in JSON format with ranking scores (0-1).
Format: [{"product_id": "id", "score": 0.95, "reason": "explanation"}, ...]"""),
                    ("user", "User query: {query}\n\nProducts to rank:\n{products}")
                ])
                
                products_text = "\n".join([
                    f"ID: {p.id}, Name: {p.name}, Price: ${p.price}, Rating: {p.rating or 'N/A'}"
                    for p in state.search_results
                ])
                
                chain = ranking_prompt | self.llm | StrOutputParser()
                ranking_result = await chain.ainvoke({
                    "query": state.user_query,
                    "products": products_text
                })
                
                ranked_products = self._parse_ranking_results(ranking_result, state.search_results)
            else:
                logger.info("Using fallback ranking - no LLM available")
                ranked_products = self._fallback_ranking(state.search_results, state.user_query)
            
            return {
                "ranked_products": ranked_products[:3],  # Top 3
                "current_step": "ranking_completed"
            }
            
        except Exception as e:
            logger.error(f"Error in product ranking: {e}", exc_info=True)
            try:
                ranked_products = self._fallback_ranking(state.search_results, state.user_query)
                return {
                    "ranked_products": ranked_products[:3],
                    "current_step": "ranking_completed"
                }
            except Exception as fallback_error:
                logger.error(f"Fallback ranking also failed: {fallback_error}", exc_info=True)
                return {
                    "error_message": f"Product ranking failed: {str(e)}",
                    "current_step": "error"
                }
    
    async def _present_options(self, state: ContractState) -> Dict[str, Any]:
        """Present ranked products to user."""
        try:
            if not state.ranked_products:
                return {
                    "error_message": "No ranked products to present",
                    "current_step": "error"
                }
            
            presentation = self._format_product_presentation(state.ranked_products)
            
            return {
                "current_step": "awaiting_selection",
                "presentation": presentation
            }
            
        except Exception as e:
            logger.error(f"Error presenting options: {e}", exc_info=True)
            return {
                "error_message": f"Failed to present options: {str(e)}",
                "current_step": "error"
            }
    
    async def _confirm_selection(self, state: ContractState) -> Dict[str, Any]:
        """Handle user selection confirmation."""
        try:
            if not state.selected_product:
                return {
                    "error_message": "No product selected for confirmation",
                    "current_step": "error"
                }
            
            order_details = {
                "product": state.selected_product.model_dump(),
                "quantity": 1,  # Default quantity
                "total_price": state.selected_product.price,
                "currency": state.selected_product.currency,
                "order_id": f"ORDER_{state.session_id}_{len(state.messages)}"
            }
            
            return {
                "order_details": order_details,
                "current_step": "awaiting_confirmation"
            }
            
        except Exception as e:
            logger.error(f"Error in selection confirmation: {e}", exc_info=True)
            return {
                "error_message": f"Confirmation failed: {str(e)}",
                "current_step": "error"
            }
    
    async def _complete_order(self, state: ContractState) -> Dict[str, Any]:
        """Complete the order process."""
        try:
            logger.info(f"Completing order for session {state.session_id}")
            
            completion_result = {
                "order_completed": True,
                "order_id": state.order_details.get("order_id"),
                "confirmation_message": f"Order confirmed! Your {state.selected_product.name} will be processed.",
                "current_step": "completed",
                "completed": True
            }
            
            return completion_result
            
        except Exception as e:
            logger.error(f"Error completing order: {e}", exc_info=True)
            return {
                "error_message": f"Order completion failed: {str(e)}",
                "current_step": "error"
            }
    
    async def _handle_error(self, state: ContractState) -> Dict[str, Any]:
        """Handle workflow errors."""
        return {
            "completed": True,
            "current_step": "error_handled"
        }
    
    def _should_proceed_to_confirmation(self, state: ContractState) -> str:
        """Determine next step after presenting options."""
        if state.current_step == "error":
            return "end"
        elif state.selected_product:
            return "confirm"
        elif state.user_query and "search again" in state.user_query.lower():
            return "search_again"
        else:
            return "end"
    
    def _should_complete_order(self, state: ContractState) -> str:
        """Determine if order should be completed."""
        if state.user_confirmation is True:
            return "complete"
        elif state.user_confirmation is False:
            return "cancel"
        else:
            return "modify"
    
    async def _mock_product_search(self, query: str) -> List[Product]:
        """Mock product search - replace with real API integration."""
        mock_products = [
            Product(
                name=f"Premium {query.title()} - Model A",
                description=f"High-quality {query} with advanced features",
                price=299.99,
                rating=4.5,
                reviews_count=1250,
                url="https://example.com/product-a"
            ),
            Product(
                name=f"Budget {query.title()} - Model B",
                description=f"Affordable {query} with essential features",
                price=99.99,
                rating=4.0,
                reviews_count=850,
                url="https://example.com/product-b"
            ),
            Product(
                name=f"Professional {query.title()} - Model C",
                description=f"Professional-grade {query} for serious users",
                price=599.99,
                rating=4.8,
                reviews_count=2100,
                url="https://example.com/product-c"
            )
        ]
        
        return mock_products
    
    def _parse_ranking_results(self, ranking_text: str, products: List[Product]) -> List[Product]:
        """Parse LLM ranking results and return sorted products."""
        try:
            import re
            json_match = re.search(r'\[.*\]', ranking_text, re.DOTALL)
            if json_match:
                rankings = json.loads(json_match.group())
                
                product_lookup = {p.id: p for p in products}
                
                sorted_rankings = sorted(rankings, key=lambda x: x.get('score', 0), reverse=True)
                return [product_lookup[r['product_id']] for r in sorted_rankings if r['product_id'] in product_lookup]
            
        except Exception as e:
            logger.warning(f"Failed to parse ranking results: {e}")
        
        return products[:3]
    
    def _format_product_presentation(self, products: List[Product]) -> str:
        """Format products for user presentation."""
        presentation = "Here are the top products I found:\n\n"
        
        for i, product in enumerate(products, 1):
            presentation += f"{i}. **{product.name}**\n"
            presentation += f"   Price: ${product.price} {product.currency}\n"
            presentation += f"   Rating: {product.rating or 'N/A'} ⭐\n"
            presentation += f"   Description: {product.description}\n\n"
        
        presentation += "Which product would you like to select? (Reply with the number or 'none' to search again)"
        return presentation
    
    def _fallback_ranking(self, products: List[Product], query: str) -> List[Product]:
        """Simple fallback ranking when LLM is not available."""
        def ranking_score(product):
            rating_score = (product.rating or 3.0) / 5.0  # Normalize rating
            price_score = max(0, 1 - (product.price / 1000))  # Lower price = higher score
            return (rating_score * 0.7) + (price_score * 0.3)
        
        return sorted(products, key=ranking_score, reverse=True)

contract_workflow = ContractWorkflow()
