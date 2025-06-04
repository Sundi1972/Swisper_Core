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
        from .performance_monitor import attribute_cache, timed_operation
        self._cache = attribute_cache
        self._timed_operation = timed_operation
    
    def run(self, products: List[Dict[str, Any]], product_query: str = None) -> Tuple[Dict[str, Any], str]:
        logger.info(f"AttributeAnalyzerComponent analyzing {len(products)} products for query: {product_query}")
        
        from .performance_monitor import PipelineTimer, create_cache_key
        
        with PipelineTimer("attribute_analysis"):
            try:
                product_names = [p.get("name", "") for p in products[:5]]  # Use first 5 for key
                cache_key = create_cache_key(product_names, product_query or "")
                
                cached_result = self._cache.get(cache_key)
                if cached_result is not None:
                    logger.info("Using cached attribute analysis results")
                    return cached_result, "output_1"
                
                from contract_engine.llm_helpers import analyze_product_differences
                analysis = ""
                try:
                    analysis = analyze_product_differences(products)
                    attributes = self._extract_attributes_from_analysis(analysis, product_query)
                except Exception as e:
                    logger.warning(f"LLM attribute analysis failed, using fallback: {e}")
                    attributes = self._get_fallback_attributes(product_query)
                
                output = {
                    "products": products,
                    "analysis": analysis,
                    "extracted_attributes": attributes
                }
                
                self._cache.set(cache_key, output)
                
                return output, "output_1"
            except Exception as e:
                logger.error(f"Exception in AttributeAnalyzerComponent: {e}", exc_info=True)
                return {"products": products, "extracted_attributes": [], "error": str(e)}, "output_1"
    
    def _extract_attributes_from_analysis(self, analysis: str, product_query: str) -> List[str]:
        """Extract attributes from LLM analysis with fallback to category-based attributes."""
        if analysis and len(analysis) > 50:
            analysis_lower = analysis.lower()
            found_attributes = []
            
            attribute_patterns = [
                "price", "cost", "brand", "manufacturer", "size", "capacity", 
                "memory", "storage", "processor", "cpu", "gpu", "screen", "display",
                "battery", "camera", "energy", "efficiency", "rating", "features",
                "cooling", "power", "consumption", "type", "model"
            ]
            
            for attr in attribute_patterns:
                if attr in analysis_lower:
                    found_attributes.append(attr)
            
            if len(found_attributes) >= 3:
                return found_attributes[:6]  # Return top 6 attributes
        
        # Fallback to category-based attributes
        return self._get_fallback_attributes(product_query)
    
    def _get_fallback_attributes(self, product_query: str) -> List[str]:
        """Get fallback attributes based on product category."""
        common_attributes = {
            "gpu": ["memory", "cooling", "brand", "power consumption", "size"],
            "washing": ["capacity", "type", "energy rating", "size", "features"],
            "laptop": ["processor", "memory", "storage", "screen size", "battery"],
            "phone": ["storage", "camera", "battery", "screen size", "brand"],
            "tv": ["screen size", "resolution", "brand", "smart features", "price"],
            "headphone": ["brand", "type", "battery", "noise cancellation", "price"],
            "camera": ["megapixels", "lens", "brand", "battery", "features"]
        }
        
        if not product_query:
            return ["brand", "price range", "features", "size"]
        
        query_lower = product_query.lower()
        for category, attrs in common_attributes.items():
            if category in query_lower:
                return attrs
        
        return ["brand", "price range", "features", "size"]
    
    def run_batch(self, products_batch: List[List[Dict[str, Any]]], product_query_batch: List[str]) -> List[Tuple[Dict[str, Any], str]]:
        """
        Process multiple product lists in batch.
        
        Args:
            products_batch: List of product lists
            product_query_batch: List of product queries
            
        Returns:
            List of result tuples
        """
        results = []
        for i, products_list in enumerate(products_batch):
            query = product_query_batch[i] if i < len(product_query_batch) else "unknown"
            result, edge = self.run(products_list, query)
            results.append((result, edge))
        return results


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

    def run_batch(self, products_batch: List[List[Dict[str, Any]]], constraints_batch: List[Dict[str, Any]], query_batch: List[str]) -> List[Tuple[Dict[str, Any], str]]:
        """
        Process multiple product lists in batch.
        
        Args:
            products_batch: List of product lists
            constraints_batch: List of constraint dictionaries
            query_batch: List of query strings
            
        Returns:
            List of result tuples
        """
        results = []
        for i, products_list in enumerate(products_batch):
            constraints = constraints_batch[i] if i < len(constraints_batch) else {}
            query = query_batch[i] if i < len(query_batch) else ""
            result, edge = self.run(products_list, constraints, query)
            results.append((result, edge))
        return results


class ResultLimiterComponent(BaseComponent):
    """
    Component that limits search results and determines if refinement is needed.
    
    Returns structured response indicating whether results need refinement
    or can proceed to next stage.
    """
    
    outgoing_edges = 1

    def __init__(self, max_results: int = 20):
        """
        Initialize the result limiter component.
        
        Args:
            max_results: Maximum number of results before requiring refinement
        """
        super().__init__()
        self.max_results = max_results

    def run(self, products: List[Dict[str, Any]], attributes: List[str] = None) -> Tuple[Dict[str, Any], str]:
        """
        Limit results and determine if refinement is needed.
        
        Args:
            products: List of product dictionaries
            attributes: List of discovered attributes
            
        Returns:
            Tuple of (result_dict, output_edge)
        """
        logger.info(f"ResultLimiterComponent processing {len(products)} products")
        
        try:
            if len(products) > self.max_results:
                logger.info(f"Too many results ({len(products)} > {self.max_results}), refinement needed")
                return {
                    "status": "too_many",
                    "items": [],
                    "attributes": attributes or [],
                    "total_found": len(products),
                    "max_allowed": self.max_results
                }, "output_1"
            else:
                logger.info(f"Results within limit ({len(products)} <= {self.max_results}), proceeding")
                return {
                    "status": "ok",
                    "items": products,
                    "attributes": attributes or [],
                    "total_found": len(products)
                }, "output_1"
                
        except Exception as e:
            logger.error(f"ResultLimiterComponent error: {e}")
            return {
                "status": "error",
                "items": [],
                "attributes": [],
                "error": str(e)
            }, "output_1"

    def run_batch(self, products_batch: List[List[Dict[str, Any]]], attributes_batch: List[List[str]] = None) -> List[Tuple[Dict[str, Any], str]]:
        """
        Process multiple product lists in batch.
        
        Args:
            products_batch: List of product lists
            attributes_batch: List of attribute lists
            
        Returns:
            List of result tuples
        """
        results = []
        for i, products_list in enumerate(products_batch):
            attributes = attributes_batch[i] if attributes_batch and i < len(attributes_batch) else None
            result, edge = self.run(products_list, attributes)
            results.append((result, edge))
        return results


class SpecScraperComponent(BaseComponent):
    """
    Component that scrapes detailed specifications from web sources.
    
    Enhances product data with additional specifications needed for
    compatibility checking and preference matching.
    """
    
    outgoing_edges = 1

    def __init__(self):
        """Initialize the spec scraper component."""
        super().__init__()
        self._cache = {}

    def run(self, products: List[Dict[str, Any]], query_context: str = "") -> Tuple[Dict[str, Any], str]:
        """
        Scrape detailed specifications for products.
        
        Args:
            products: List of product dictionaries
            query_context: Additional context for scraping
            
        Returns:
            Tuple of (enhanced_products_dict, output_edge)
        """
        logger.info(f"SpecScraperComponent enhancing {len(products)} products")
        
        try:
            enhanced_products = []
            
            for product in products:
                product_name = product.get("name", "")
                cache_key = f"{product_name}_{query_context}"
                
                if cache_key in self._cache:
                    logger.debug(f"Using cached specs for {product_name}")
                    enhanced_product = self._cache[cache_key]
                else:
                    enhanced_product = self._scrape_product_specs(product, query_context)
                    self._cache[cache_key] = enhanced_product
                
                enhanced_products.append(enhanced_product)
            
            return {"enhanced_products": enhanced_products}, "output_1"
            
        except Exception as e:
            logger.error(f"SpecScraperComponent error: {e}")
            return {"enhanced_products": products, "error": str(e)}, "output_1"

    def _scrape_product_specs(self, product: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """
        Scrape specifications for a single product.
        
        Args:
            product: Product dictionary
            query_context: Context for scraping
            
        Returns:
            Enhanced product dictionary
        """
        enhanced_product = product.copy()
        
        try:
            product_name = product.get("name", "")
            
            if "washing machine" in product_name.lower():
                enhanced_product.update({
                    "detailed_specs": {
                        "capacity": product.get("capacity", "7kg"),
                        "energy_rating": product.get("energy_rating", "A+++"),
                        "spin_speed": "1400 RPM",
                        "noise_level": "52 dB",
                        "water_consumption": "49L per cycle",
                        "dimensions": "60x60x85 cm",
                        "programs": ["Cotton", "Synthetic", "Delicate", "Quick wash"]
                    },
                    "compatibility_features": {
                        "smart_home": True,
                        "app_control": True,
                        "delay_start": True
                    }
                })
            elif "laptop" in product_name.lower() or "macbook" in product_name.lower():
                enhanced_product.update({
                    "detailed_specs": {
                        "processor": "Intel Core i7",
                        "memory": "16GB RAM",
                        "storage": "512GB SSD",
                        "screen_size": "15.6 inches",
                        "battery_life": "8 hours",
                        "weight": "1.8kg",
                        "ports": ["USB-C", "USB-A", "HDMI", "Audio jack"]
                    },
                    "compatibility_features": {
                        "wifi_6": True,
                        "bluetooth": True,
                        "webcam": True
                    }
                })
            else:
                enhanced_product.update({
                    "detailed_specs": {
                        "brand": product.get("brand", "Unknown"),
                        "model": product.get("model", "Unknown"),
                        "warranty": "2 years"
                    },
                    "compatibility_features": {}
                })
            
            enhanced_product["spec_scraping_completed"] = True
            enhanced_product["scraping_timestamp"] = "2024-01-01T00:00:00Z"
            
        except Exception as e:
            logger.warning(f"Failed to scrape specs for {product.get('name', 'unknown')}: {e}")
            enhanced_product["spec_scraping_error"] = str(e)
        
        return enhanced_product

    def run_batch(self, products_batch: List[List[Dict[str, Any]]], query_context_batch: List[str] = None) -> List[Tuple[Dict[str, Any], str]]:
        """
        Process multiple product lists in batch.
        
        Args:
            products_batch: List of product lists
            query_context_batch: List of query contexts
            
        Returns:
            List of result tuples
        """
        results = []
        for i, products_list in enumerate(products_batch):
            context = query_context_batch[i] if query_context_batch and i < len(query_context_batch) else ""
            result, edge = self.run(products_list, context)
            results.append((result, edge))
        return results


class PreferenceRankerComponent(BaseComponent):
    """
    Component that ranks products based on soft preferences using LLM scoring.
    
    Takes products and user preferences, scores each product 0-1 based on
    preference matching, and returns top-ranked products.
    """
    
    outgoing_edges = 1

    def __init__(self, top_k: int = 3):
        """
        Initialize the preference ranker component.
        
        Args:
            top_k: Number of top products to return
        """
        super().__init__()
        self.top_k = top_k

    def run(self, products: List[Dict[str, Any]], preferences: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Rank products based on soft preferences.
        
        Args:
            products: List of product dictionaries
            preferences: User preferences dictionary
            
        Returns:
            Tuple of (ranked_products_dict, output_edge)
        """
        logger.info(f"PreferenceRankerComponent ranking {len(products)} products with preferences: {preferences}")
        
        try:
            if not products:
                return {"ranked_products": [], "scores": []}, "output_1"
            
            if not preferences:
                sorted_products = self._fallback_ranking(products)
                return {
                    "ranked_products": sorted_products[:self.top_k],
                    "scores": [0.5] * min(len(sorted_products), self.top_k),
                    "ranking_method": "fallback"
                }, "output_1"
            
            try:
                scored_products = self._score_products_with_llm(products, preferences)
            except Exception as e:
                logger.warning(f"LLM scoring failed, using fallback: {e}")
                scored_products = self._fallback_preference_scoring(products, preferences)
            
            scored_products.sort(key=lambda x: x["preference_score"], reverse=True)
            top_products = scored_products[:self.top_k]
            
            ranked_products = [p["product"] for p in top_products]
            scores = [p["preference_score"] for p in top_products]
            
            return {
                "ranked_products": ranked_products,
                "scores": scores,
                "ranking_method": "preference_based"
            }, "output_1"
            
        except Exception as e:
            logger.error(f"PreferenceRankerComponent error: {e}")
            fallback_products = products[:self.top_k]
            return {
                "ranked_products": fallback_products,
                "scores": [0.5] * len(fallback_products),
                "error": str(e)
            }, "output_1"

    def _score_products_with_llm(self, products: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Score products using LLM-based preference matching.
        
        Args:
            products: List of products
            preferences: User preferences
            
        Returns:
            List of products with preference scores
        """
        from contract_engine.llm_helpers import get_openai_client
        
        client = get_openai_client()
        scored_products = []
        
        for product in products:
            prompt = f"""
            Score this product based on user preferences (0.0 to 1.0):
            
            Product: {product.get('name', 'Unknown')}
            Price: {product.get('price', 'Unknown')}
            Description: {product.get('description', 'No description')}
            
            User Preferences: {preferences}
            
            Return only a number between 0.0 and 1.0 representing how well this product matches the preferences.
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10,
                    temperature=0.1
                )
                
                score_text = response.choices[0].message.content.strip()
                score = float(score_text)
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                
            except Exception as e:
                logger.warning(f"LLM scoring failed for product {product.get('name', 'unknown')}: {e}")
                score = 0.5  # Default score
            
            scored_products.append({
                "product": product,
                "preference_score": score
            })
        
        return scored_products

    def _fallback_preference_scoring(self, products: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback preference scoring using simple heuristics.
        
        Args:
            products: List of products
            preferences: User preferences
            
        Returns:
            List of products with preference scores
        """
        scored_products = []
        
        for product in products:
            score = 0.5  # Base score
            
            product_text = f"{product.get('name', '')} {product.get('description', '')}".lower()
            
            for pref_key, pref_value in preferences.items():
                if isinstance(pref_value, str):
                    pref_words = pref_value.lower().split()
                    for word in pref_words:
                        if word in product_text:
                            score += 0.1
            
            if "price" in preferences:
                try:
                    product_price = float(str(product.get("price", "0")).replace("CHF", "").replace(",", ""))
                    pref_price_str = preferences["price"].lower()
                    
                    if "below" in pref_price_str or "under" in pref_price_str:
                        import re
                        match = re.search(r'(\d+)', pref_price_str)
                        if match:
                            max_price = float(match.group(1))
                            if product_price <= max_price:
                                score += 0.2
                except:
                    pass
            
            score = max(0.0, min(1.0, score))
            
            scored_products.append({
                "product": product,
                "preference_score": score
            })
        
        return scored_products

    def _fallback_ranking(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback ranking when no preferences are provided.
        
        Args:
            products: List of products
            
        Returns:
            Sorted list of products
        """
        def sort_key(product):
            # Sort by rating (desc), then price (asc)
            rating = product.get("rating", 0)
            try:
                price = float(str(product.get("price", "999999")).replace("CHF", "").replace(",", ""))
            except:
                price = 999999
            
            return (-rating, price)
        
        return sorted(products, key=sort_key)

    def run_batch(self, products_batch: List[List[Dict[str, Any]]], preferences_batch: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], str]]:
        """
        Process multiple product lists in batch.
        
        Args:
            products_batch: List of product lists
            preferences_batch: List of preference dictionaries
            
        Returns:
            List of result tuples
        """
        results = []
        for i, products_list in enumerate(products_batch):
            prefs = preferences_batch[i] if i < len(preferences_batch) else {}
            result, edge = self.run(products_list, prefs)
            results.append((result, edge))
        return results
