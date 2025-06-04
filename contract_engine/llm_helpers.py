import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Retrieve API key and project ID from environment
api_key = os.getenv("OPENAI_API_KEY")
project_id = os.getenv("OPENAI_PROJECT_ID")

# Debug: Show if key and project are set
print("🔑 Detected API Key:", "SET" if api_key else "NOT SET")
print("🧭 Project ID:", project_id if project_id else "NOT SET")

# Initialize OpenAI client lazily
_client = None

def get_openai_client():
    global _client
    if _client is None:
        if not api_key:
            raise ValueError("OpenAI API key not available")
        _client = OpenAI(
            api_key=api_key,
            project=project_id
        )
    return _client

def extract_initial_criteria(user_prompt: str) -> dict:
    """Extract product criteria and specifications from initial user prompt"""
    prompt = (
        "You are an expert at parsing product purchase requests to extract specific criteria and specifications.\n\n"
        "User prompt:\n"
        f"{user_prompt}\n\n"
        "Please extract and return a JSON object with the following structure:\n"
        "{\n"
        '  "base_product": "the main product type (e.g., graphics card, laptop, smartphone)",\n'
        '  "specifications": {\n'
        '    "chip_model": "specific chip/processor model if mentioned",\n'
        '    "memory": "memory/RAM specifications if mentioned",\n'
        '    "storage": "storage specifications if mentioned",\n'
        '    "brand": "specific brand if mentioned",\n'
        '    "price_limit": "price constraints if mentioned",\n'
        '    "other": "any other specific technical requirements"\n'
        '  },\n'
        '  "search_keywords": ["list", "of", "key", "search", "terms"],\n'
        '  "enhanced_query": "optimized search query combining product type and key specifications"\n'
        "}\n\n"
        "Examples:\n"
        "- 'graphics card with RTX 4070 chip and min 12GB RAM' → chip_model: 'RTX 4070', memory: '12GB'\n"
        "- 'gaming laptop under 2000 CHF with 16GB RAM' → memory: '16GB', price_limit: 'under 2000 CHF'\n"
        "- 'iPhone 15 Pro with 256GB storage' → brand: 'iPhone', storage: '256GB'\n\n"
        "Return only valid JSON. Do not include markdown or explanations."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print("📎 Criteria extraction output:\n", raw_output)

        # Strip markdown code block formatting if present
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        return json.loads(raw_output)

    except Exception as e:
        print("❌ Failed to extract criteria:", str(e))
        return _fallback_criteria_extraction(user_prompt)

def _fallback_criteria_extraction(user_prompt: str) -> dict:
    """Fallback criteria extraction using regex patterns"""
    base_product = "product"
    specifications = {}
    search_keywords = []
    
    product_patterns = {
        r'\b(graphics?\s*cards?|gpu)\b': 'graphics card',
        r'\b(laptops?|notebooks?)\b': 'laptop',
        r'\b(smartphones?|phones?|iphones?)\b': 'smartphone',
        r'\b(washing\s*machines?)\b': 'washing machine',
        r'\b(processors?|cpus?)\b': 'processor'
    }
    
    for pattern, product_type in product_patterns.items():
        if re.search(pattern, user_prompt, re.IGNORECASE):
            base_product = product_type
            break
    
    spec_patterns = {
        'chip_model': r'\b(rtx\s*\d+|gtx\s*\d+|rx\s*\d+|intel\s*\w+|amd\s*\w+)\b',
        'memory': r'\b(\d+\s*gb\s*ram|\d+gb\s*memory|\d+\s*gb)\b',
        'storage': r'\b(\d+\s*gb\s*storage|\d+\s*tb|\d+gb\s*ssd)\b',
        'price_limit': r'\b(under\s*\d+|below\s*\d+|max\s*\d+|\d+\s*chf)\b'
    }
    
    for spec_key, pattern in spec_patterns.items():
        match = re.search(pattern, user_prompt, re.IGNORECASE)
        if match:
            specifications[spec_key] = match.group(1)
            search_keywords.append(match.group(1))
    
    enhanced_query = base_product
    if search_keywords:
        enhanced_query += " " + " ".join(search_keywords)
    
    return {
        "base_product": base_product,
        "specifications": specifications,
        "search_keywords": search_keywords,
        "enhanced_query": enhanced_query
    }

def is_cancel_request(user_input: str) -> bool:
    """Check if user input contains cancellation keywords"""
    cancel_keywords = ["cancel", "exit", "stop", "quit", "abort", "nevermind"]
    return any(keyword in user_input.lower() for keyword in cancel_keywords)

def is_response_relevant(user_response: str, expected_context: str, product_context: str) -> dict:
    """
    Use LLM to determine if user response is relevant to expected context
    
    Args:
        user_response: What the user actually said
        expected_context: What we were expecting (e.g., "product criteria", "yes/no confirmation")
        product_context: Current product being discussed (e.g., "graphics card RTX 4070")
    
    Returns:
        {
            "is_relevant": bool,
            "confidence": float,
            "reason": str,
            "detected_intent": str
        }
    """
    prompt = (
        "You are an expert at analyzing user responses in the context of product purchase conversations.\n\n"
        f"CONTEXT: We are discussing purchasing a {product_context}\n"
        f"EXPECTED RESPONSE TYPE: {expected_context}\n"
        f"USER'S ACTUAL RESPONSE: {user_response}\n\n"
        "Please analyze if the user's response is relevant to what we were expecting.\n\n"
        "Examples of RELEVANT responses:\n"
        "- When asking for product criteria: 'I need 16GB RAM', 'under 2000 CHF', 'any brand is fine'\n"
        "- When asking for yes/no confirmation: 'yes', 'no', 'confirm', 'I'm not sure about the price'\n\n"
        "Examples of IRRELEVANT responses:\n"
        "- When asking for product criteria: 'Who was Gerhard Schroeder?', 'What's the weather?'\n"
        "- When asking for yes/no confirmation: 'Tell me about quantum physics', 'I want a different product'\n"
        "- When discussing graphics cards: 'I want to buy a washing machine instead'\n\n"
        "Return a JSON object with this structure:\n"
        "{\n"
        '  "is_relevant": true/false,\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reason": "brief explanation of why relevant or not",\n'
        '  "detected_intent": "what the user seems to be trying to do"\n'
        "}\n\n"
        "Be conservative - if there's any reasonable connection to the product or purchase context, consider it relevant.\n"
        "Only mark as irrelevant if the response is clearly unrelated to the purchase discussion.\n\n"
        "Return only valid JSON. Do not include markdown or explanations."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print(f"📎 Relevance check output:\n{raw_output}")

        # Strip markdown code block formatting if present
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        return json.loads(raw_output)

    except Exception as e:
        print(f"❌ Failed to check response relevance: {str(e)}")
        return _fallback_relevance_check(user_response, expected_context, product_context)

def _fallback_relevance_check(user_response: str, expected_context: str, product_context: str) -> dict:
    """Fallback relevance check using keyword matching"""
    user_lower = user_response.lower()
    
    irrelevant_patterns = [
        r'\b(who|what|when|where|why)\s+(is|was|are|were)',  # Questions about people/facts
        r'\b(weather|temperature|climate)\b',  # Weather questions
        r'\b(politics|politician|president|chancellor)\b',  # Political questions
        r'\b(quantum|physics|chemistry|biology)\b',  # Science questions
        r'\b(recipe|cooking|food)\b',  # Cooking questions
    ]
    
    for pattern in irrelevant_patterns:
        if re.search(pattern, user_lower):
            return {
                "is_relevant": False,
                "confidence": 0.8,
                "reason": "Response appears to be about unrelated topics",
                "detected_intent": "asking about unrelated topic"
            }
    
    if "graphics card" in product_context.lower():
        other_products = ["washing machine", "laptop", "smartphone", "phone", "tablet", "monitor"]
        for product in other_products:
            if product in user_lower and "buy" in user_lower:
                return {
                    "is_relevant": False,
                    "confidence": 0.9,
                    "reason": f"User wants to buy {product} instead of {product_context}",
                    "detected_intent": f"wants to purchase {product}"
                }
    
    return {
        "is_relevant": True,
        "confidence": 0.6,
        "reason": "No clear irrelevant patterns detected",
        "detected_intent": "likely relevant to purchase context"
    }

def analyze_product_differences(product_list: list) -> list:
    prompt = (
        "Analyze the following product search results and identify the key differentiating attributes "
        "that would help a user make a decision. Focus on the most important distinguishing factors.\n\n"
        f"{json.dumps(product_list, indent=2)}\n\n"
        "Return a JSON list of the top 5-7 most important attributes that differentiate these products. "
        "Use simple, clear attribute names like: ['price', 'brand', 'capacity', 'energy_efficiency', 'size', 'features']\n\n"
        "Return only a valid JSON list of strings. Do not include markdown or explanations."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        attributes = json.loads(raw_output)
        
        if isinstance(attributes, list) and all(isinstance(attr, str) for attr in attributes):
            return attributes
        else:
            return ["price", "brand", "capacity", "energy_efficiency", "size", "features"]
            
    except Exception as e:
        print(f"❌ Failed to analyze product differences: {e}")
        return ["price", "brand", "capacity", "energy_efficiency", "size", "features"]

def analyze_user_preferences(user_input: str, product_search_results: list) -> dict:
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 Starting preference extraction for input: '{user_input[:100]}...'")
    logger.info(f"📦 Analyzing {len(product_search_results)} sample products")
    
    prompt = (
        "You are an assistant that extracts structured product preferences and compatibility constraints "
        "from user input.\n\n"
        "User said:\n"
        f"{user_input}\n\n"
        "Here is a representative sample of available products:\n"
        f"{json.dumps(product_search_results, indent=2)}\n\n"
        "Please extract:\n"
        "1. PREFERENCES: Specific measurable requirements as key-value pairs for filtering\n"
        "   - These are quantifiable limits or technical specifications\n"
        "   - Examples: price limits, capacity requirements, size constraints, energy efficiency ratings\n\n"
        "2. CONSTRAINTS: Complex qualitative requirements as a list\n"
        "   - These are general desires or complex requirements\n"
        "   - Examples: 'quiet operation', 'energy efficient', 'reliable brand', 'compatible with product X'\n\n"
        "For preferences (key-value pairs), use these patterns:\n"
        "- price: 'below X CHF' or 'under X' or 'max X'\n"
        "- capacity: 'at least Xkg' or 'minimum X liters' or 'Xkg or more'\n"
        "- energy_efficiency: 'A or better' or 'minimum B' or 'B or higher'\n"
        "- size: 'fits in X' or 'maximum X cm' or 'compact'\n"
        "- power: 'under X watts' or 'low power consumption'\n"
        "- screen_size: 'X inches' or 'X-Y inch range'\n"
        "- weight: 'under X lbs' or 'lightweight'\n\n"
        "Return a JSON object with exactly these two keys:\n"
        "{\n"
        "  \"preferences\": {\"key\": \"specific requirement value\"},\n"
        "  \"constraints\": [\"list of qualitative requirements\"]\n"
        "}\n\n"
        "Return only valid JSON. Do not include markdown or explanations."
    )
    
    logger.debug(f"📝 LLM prompt length: {len(prompt)} characters")

    try:
        logger.info("🤖 Sending request to OpenAI GPT-4o...")
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        logger.info(f"📎 Raw LLM output ({len(raw_output)} chars):\n{raw_output}")

        if raw_output.startswith("```"):
            logger.debug("🧹 Removing markdown code block formatting")
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)
            logger.debug(f"🧹 Cleaned output: {raw_output}")

        logger.info("🔧 Parsing JSON response...")
        parsed_result = json.loads(raw_output)
        
        if not isinstance(parsed_result.get("preferences"), dict):
            logger.warning(f"⚠️ Invalid preferences type: {type(parsed_result.get('preferences'))}, converting to dict")
            parsed_result["preferences"] = {}
        if not isinstance(parsed_result.get("constraints"), list):
            logger.warning(f"⚠️ Invalid constraints type: {type(parsed_result.get('constraints'))}, converting to list")
            parsed_result["constraints"] = []
            
        logger.info(f"✅ Successfully extracted {len(parsed_result['preferences'])} preferences")
        logger.info(f"✅ Successfully extracted {len(parsed_result['constraints'])} constraints")
        logger.info(f"📋 Preferences: {parsed_result['preferences']}")
        logger.info(f"🔒 Constraints: {parsed_result['constraints']}")
        
        return parsed_result

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing failed: {e}")
        logger.error(f"🔍 Raw output that failed to parse: '{raw_output}'")
        logger.error(f"🔍 Error position: line {e.lineno}, column {e.colno}")
        return {"preferences": {}, "constraints": []}
    except Exception as e:
        logger.error(f"❌ Failed to analyze preferences: {str(e)}")
        logger.error(f"🔍 Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
        return {"preferences": {}, "constraints": []}

def check_product_compatibility(product_list: list, user_constraints: dict, product_type: str = None) -> list:
    constraint_text = json.dumps(user_constraints)

    prompt = (
        "You are a compatibility expert assistant.\n\n"
        f"The user is searching for a {product_type or 'product'} with this constraint:\n"
        f"{constraint_text}\n\n"
        "Here is a list of products with their attributes:\n"
        f"{json.dumps(product_list, indent=2)}\n\n"
        "Your task:\n"
        "1. Analyze which product attributes matter for compatibility.\n"
        "2. Search the web and see whether you find additional attributes for the products that would determine compatiblity.For example a graphics card would have a pCI slot and a length"
        "3. For each product, return whether it is 'compatible': true or false.\n\n"
        "Return a JSON list where each item includes the product name and compatibility flag. "
        "Return only valid JSON. Do not include markdown or explanations. Do not wrap the JSON in triple backticks."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print("📎 Compatibility Output:\n", raw_output)

        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        return json.loads(raw_output)

    except Exception as e:
        print("❌ Compatibility check failed:", str(e))
        return []

def filter_products_with_llm(product_list: list, preferences: dict, constraints: list = None) -> list:
    constraints = constraints or []
    
    prompt = (
        "You are an intelligent shopping assistant.\n"
        f"The user has the following PREFERENCES (specific requirements): {json.dumps(preferences)}\n"
        f"The user has the following CONSTRAINTS (qualitative desires): {json.dumps(constraints)}\n\n"
        f"Here are the products to evaluate:\n{json.dumps(product_list, indent=2)}\n\n"
        "Please filter the products based on how well they align with the user's preferences AND constraints. "
        "Be REASONABLE and FLEXIBLE when interpreting user requirements: "
        "- For price limits like 'below 1400 CHF', include products up to that limit or slightly above if they offer exceptional value "
        "- For capacity like '6kg', include products with 6kg or higher capacity "
        "- For energy efficiency like 'B or better', include A+++, A++, A+, A, B rated products "
        "- If exact specifications aren't available, use reasonable approximations based on product descriptions "
        "- Aim to return 5-15 products that reasonably match the criteria rather than being overly strict "
        "Return a JSON list of the qualifying products (including all their attributes). "
        "Return only valid JSON. Do not include markdown or explanations. Do not wrap the JSON in triple backticks."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print("📎 Filter Output:\n", raw_output)

        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        filtered_products = json.loads(raw_output)
        
        if len(filtered_products) < 5 and len(product_list) >= 5:
            print(f"⚠️ Filter returned only {len(filtered_products)} products, using top {min(10, len(product_list))} from original list")
            return product_list[:10]
            
        return filtered_products

    except Exception as e:
        print("❌ Failed to filter products:", str(e))
        return product_list[:10]

def generate_product_recommendation(products: list, user_preferences: list, user_constraints: dict) -> dict:
    """
    Generate LLM-powered recommendation for top 5 products based on user preferences.
    
    Args:
        products: List of top 5 products to analyze
        user_preferences: User preferences extracted from input
        user_constraints: User constraints/requirements
        
    Returns:
        Dict with recommendation analysis and suggested choice
    """
    if not products or len(products) == 0:
        return {
            "numbered_products": [],
            "recommendation": {
                "choice": None,
                "reasoning": "No products available for recommendation"
            }
        }
    
    top_5_products = products[:5]
    
    prompt = f"""
    You are an expert product recommendation assistant. Analyze these {len(top_5_products)} products based on the user's preferences and constraints.

    User Preferences: {json.dumps(user_preferences)}
    User Constraints: {json.dumps(user_constraints)}

    Products to analyze:
    {json.dumps(top_5_products, indent=2)}

    Please provide:
    1. A numbered list (1-{len(top_5_products)}) of the products with key specs and prices
    2. Your top recommendation (1-{len(top_5_products)}) with detailed reasoning considering:
       - How well each product matches user preferences
       - Price-to-value ratio
       - Reviews and ratings
       - Technical specifications alignment

    Return a JSON object with this structure:
    {{
        "numbered_products": [
            {{"number": 1, "name": "Product Name", "price": "Price", "key_specs": "Brief specs"}},
            ...
        ],
        "recommendation": {{
            "choice": 1,
            "reasoning": "Detailed explanation of why this is the best choice"
        }}
    }}

    Return only valid JSON. Do not include markdown or explanations.
    """

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print("📎 Recommendation Output:\n", raw_output)

        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        recommendation_data = json.loads(raw_output)
        
        if "numbered_products" not in recommendation_data or "recommendation" not in recommendation_data:
            raise ValueError("Invalid recommendation structure")
            
        return recommendation_data

    except Exception as e:
        print("❌ Failed to generate recommendation:", str(e))
        numbered_products = []
        for i, product in enumerate(top_5_products, 1):
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

def generate_preference_refinement_message(products: list, attributes: list, product_query: str) -> str:
    """
    Generate LLM-powered preference refinement message with product table and attribute ranges.
    
    Args:
        products: List of search result products
        attributes: List of key attributes discovered for this product category
        product_query: The original search query
        
    Returns:
        String message with formatted product table and attribute ranges
    """
    if not products or len(products) == 0:
        return f"I found many results for '{product_query}'. Could you provide more specific criteria like brand, price range, features, or other requirements to help narrow down the options?"
    
    display_products = products[:10]
    
    prompt = f"""
You are a helpful shopping assistant. The user searched for "{product_query}" and we found {len(products)} results, which is too many to review easily.

Create a user-friendly message that:
1. Explains we found many results and need to narrow them down
2. Shows a nicely formatted table of the first 10 products with key information (name, price, key specs)
3. Lists the key attributes for this product category with their value ranges found in the search results
4. Asks the user to provide more specific preferences

Here are the products to display:
{json.dumps(display_products, indent=2)}

Here are the key attributes we identified:
{json.dumps(attributes, indent=2)}

Format your response as a clear, helpful message. Use markdown table format for the products. After the table, show the attribute ranges in a user-friendly way.

Example format:
"I found {len(products)} results for '{product_query}'. Here are some of the options:

| Product | Price | Key Features |
|---------|-------|--------------|
| ... | ... | ... |

To help narrow down your choices, here are the key attributes and their ranges in these results:
- Price: CHF X - CHF Y
- Brand: A, B, C, etc.
- [other attributes with ranges]

Could you please tell me your preferences for any of these attributes?"

Return only the formatted message text. Do not include markdown code blocks or explanations.
"""
    
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Failed to generate preference refinement message: {e}")
        attribute_examples = ", ".join(attributes[:3]) if attributes else "brand, price range, features"
        return (
            f"I found {len(products)} results for '{product_query}'. "
            f"To help narrow down the options, could you provide more specific criteria? "
            f"For example: {attribute_examples}, or any other requirements you have."
        )
