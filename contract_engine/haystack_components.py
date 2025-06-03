from haystack.nodes import BaseComponent
from typing import List, Dict, Any, Optional, Tuple
import logging

# Assuming tool_adapter is in PYTHONPATH.
# If repository root is in PYTHONPATH:
from tool_adapter.mock_google import google_shopping_search as search_fn

logger = logging.getLogger(__name__)

class MockGoogleShoppingComponent(BaseComponent):
    outgoing_edges = 1 # Number of output connections

    def __init__(self):
        super().__init__()
        # Any specific initialization if needed

    def run(self, query: str) -> Tuple[Dict[str, Any], str]:
        logger.info("🛍️ Product search initiated", extra={"query": query})
        try:
            products = search_fn(q=query)
            # Handle cases where search_fn might return error dicts
            if isinstance(products, list) and products and isinstance(products[0], dict) and "error" in products[0]:
                logger.warning("🚫 Product search error", extra={"query": query, "error": products[0]['error']})
                output = {"products": []}
            else:
                logger.info("✅ Products found", extra={"query": query, "count": len(products)})
                output = {"products": products}
            return output, "output_1" # Standard Haystack component output format
        except Exception as e:
            logger.error(f"Exception in MockGoogleShoppingComponent for query '{query}': {e}", exc_info=True)
            # Return empty list or error structure
            return {"products": [], "error": str(e)}, "output_1"

    def run_batch(self, queries: List[str]) -> Tuple[Dict[str, Any], str]:
        # Optional: implement batch processing if needed
        results = []
        for query in queries:
            result, _ = self.run(query=query)
            results.append(result)
        # Consolidate results: {"products": [[products_for_q1], [products_for_q2], ...]}
        # Or, if component is meant to output a flat list of all products from all queries, adjust accordingly.
        # For now, let's assume batch output mirrors multiple single runs.
        return {"results_batch": results}, "output_1"


class SimplePythonRankingComponent(BaseComponent):
    outgoing_edges = 1

    def __init__(self):
        super().__init__()

    def _score(self, product: Dict[str, Any]) -> tuple:
        # Default to 0 for rating and infinity for price if not present or not a number
        try:
            rating = float(product.get("rating", 0.0))
        except (ValueError, TypeError):
            rating = 0.0
        try:
            price = float(product.get("price", float("inf")))
        except (ValueError, TypeError):
            price = float("inf")
        return (rating, -price) # Sort by rating (desc), then price (asc)

    def run(self, products: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
        logger.info("📊 Ranking products", extra={"product_count": len(products)})
        if not products or not isinstance(products, list):
            logger.warning("No products provided to rank or input is not a list.")
            return {"ranked_products": []}, "output_1"
        
        try:
            # Filter out any non-dictionary items just in case
            valid_products = [p for p in products if isinstance(p, dict)]
            ranked_list = sorted(valid_products, key=self._score, reverse=True)
            output = {"ranked_products": ranked_list}
            return output, "output_1"
        except Exception as e:
            logger.error(f"Exception in SimplePythonRankingComponent: {e}", exc_info=True)
            return {"ranked_products": [], "error": str(e)}, "output_1"
    
    def run_batch(self, products_batch: List[List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], str]:
        results = []
        # The input here is expected to be a list of lists of products,
        # e.g., products_batch = [ [{"products": results_from_run1}], [{"products": results_from_run2}] ]
        # However, the component's run method expects a direct list of products.
        # This means the pipeline definition needs to ensure correct data flow (e.g. using `inputs` in `Pipeline.add_node`).
        # If `products_batch` is truly `List[List[Dict[str, Any]]]`, where each inner list is a list of products:
        for products_list in products_batch:
            result, _ = self.run(products=products_list) # Pass the inner list to run()
            results.append(result) # result is {"ranked_products": ...}
        return {"ranked_products_batch": results}, "output_1"


class ProductSelectorComponent(BaseComponent):
    outgoing_edges = 1

    def __init__(self):
        super().__init__()

    def run(self, ranked_products: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
        logger.info("🎯 Selecting top product", extra={"ranked_count": len(ranked_products)})
        if not ranked_products or not isinstance(ranked_products, list):
            logger.warning("No ranked products provided to select from or input is not a list.")
            output = {"selected_product": None}
        else:
            # Filter out non-dict items just in case
            valid_products = [p for p in ranked_products if isinstance(p, dict)]
            if not valid_products:
                logger.warning("Product list became empty after filtering non-dict items.")
                output = {"selected_product": None}
            else:
                top_product = valid_products[0]
                logger.info("🏆 Product selected", extra={"product": top_product.get('name', 'Unknown name'), "price": top_product.get('price', 'N/A')})
                output = {"selected_product": top_product}
        
        return output, "output_1"

    def run_batch(self, ranked_products_batch: List[List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], str]:
        results = []
        # Similar to SimplePythonRankingComponent, this expects a list of lists of ranked products.
        for ranked_products_list in ranked_products_batch:
            result, _ = self.run(ranked_products=ranked_products_list)
            results.append(result) # result is {"selected_product": ...}
        return {"selected_products_batch": results}, "output_1"


class AttributeAnalyzerComponent(BaseComponent):
    outgoing_edges = 1
    
    def __init__(self):
        super().__init__()
    
    def run(self, products: List[Dict[str, Any]], product_query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"AttributeAnalyzerComponent analyzing {len(products)} products for query: {product_query}")
        try:
            from contract_engine.llm_helpers import analyze_product_differences
            analysis = analyze_product_differences(products)
            
            attributes = self._extract_attributes_from_analysis(analysis, product_query)
            
            output = {
                "products": products,
                "analysis": analysis,
                "extracted_attributes": attributes
            }
            return output, "output_1"
        except Exception as e:
            logger.error(f"Exception in AttributeAnalyzerComponent: {e}", exc_info=True)
            return {"products": products, "extracted_attributes": [], "error": str(e)}, "output_1"
    
    def _extract_attributes_from_analysis(self, analysis: str, product_query: str) -> List[str]:
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


class ClarificationAskerComponent(BaseComponent):
    outgoing_edges = 1
    
    def __init__(self):
        super().__init__()
    
    def run(self, products: List[Dict[str, Any]], extracted_attributes: List[str], product_query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"ClarificationAskerComponent generating clarification for {len(products)} products")
        
        attribute_examples = ", ".join(extracted_attributes[:3])
        clarification_message = (
            f"I found {len(products)} results for '{product_query}'. "
            f"To help you choose the best option, could you provide more criteria? "
            f"For example: {attribute_examples}, or any specific requirements you have."
        )
        
        output = {
            "products": products,
            "extracted_attributes": extracted_attributes,
            "clarification_message": clarification_message,
            "needs_clarification": True
        }
        return output, "output_1"


class ProductFilterComponent(BaseComponent):
    outgoing_edges = 1
    
    def __init__(self):
        super().__init__()
    
    def run(self, products: List[Dict[str, Any]], user_preferences: List[str]) -> Tuple[Dict[str, Any], str]:
        logger.info(f"ProductFilterComponent filtering {len(products)} products with preferences: {user_preferences}")
        try:
            if not user_preferences:
                return {"filtered_products": products}, "output_1"
            
            from contract_engine.llm_helpers import filter_products_with_llm
            filtered_products = filter_products_with_llm(products, user_preferences, [])
            
            output = {"filtered_products": filtered_products}
            return output, "output_1"
        except Exception as e:
            logger.error(f"Exception in ProductFilterComponent: {e}", exc_info=True)
            return {"filtered_products": products, "error": str(e)}, "output_1"


class CompatibilityCheckerComponent(BaseComponent):
    outgoing_edges = 1
    
    def __init__(self):
        super().__init__()
        self._cache = {}
    
    def run(self, products: List[Dict[str, Any]], constraints: Dict[str, Any], product_query: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"CompatibilityCheckerComponent checking {len(products)} products for constraints: {constraints}")
        try:
            if not constraints:
                return {"compatible_products": products}, "output_1"
            
            cache_key = f"{product_query}_{hash(str(constraints))}"
            if cache_key in self._cache:
                logger.info("Using cached compatibility results")
                compatibility_results = self._cache[cache_key]
            else:
                enhanced_products = self._enhance_with_web_search(products, constraints, product_query)
                
                from contract_engine.llm_helpers import check_product_compatibility
                compatibility_results = check_product_compatibility(enhanced_products, constraints, product_query)
                self._cache[cache_key] = compatibility_results
            
            compatible_products = []
            for i, result in enumerate(compatibility_results):
                if result.get("compatible", False) and i < len(products):
                    compatible_products.append(products[i])
            
            output = {
                "compatible_products": compatible_products,
                "compatibility_results": compatibility_results
            }
            return output, "output_1"
        except Exception as e:
            logger.error(f"Exception in CompatibilityCheckerComponent: {e}", exc_info=True)
            return {"compatible_products": products, "error": str(e)}, "output_1"
    
    def _enhance_with_web_search(self, products: List[Dict[str, Any]], constraints: Dict[str, Any], product_query: str) -> List[Dict[str, Any]]:
        try:
            from tool_adapter.mock_google import google_shopping_search
            
            constraint_text = " ".join([f"{k} {v}" for k, v in constraints.items()])
            search_query = f"{product_query} {constraint_text} compatibility specifications"
            
            web_results = google_shopping_search(search_query)
            
            enhanced_products = products.copy()
            for product in enhanced_products:
                product["web_search_enhanced"] = True
                product["search_query_used"] = search_query
            
            return enhanced_products
        except Exception as e:
            logger.error(f"Web search enhancement failed: {e}")
            return products
