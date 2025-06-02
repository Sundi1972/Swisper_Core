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

# Initialize OpenAI client
client = OpenAI(
    api_key=api_key,
    project=project_id
)

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

def analyze_product_differences(product_list: list) -> str:
    prompt = (
        "Analyze the following product search results and summarize key differences in terms "
        "of price, brand, cooling system, size, and performance characteristics. "
        "Return a concise summary that could help a user decide what to prioritize.\n\n"
        f"{json.dumps(product_list, indent=2)}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        timeout=30
    )

    return response.choices[0].message.content

def analyze_user_preferences(user_input: str, product_search_results: list) -> dict:
    prompt = (
        "You are an assistant that extracts structured product preferences and compatibility constraints "
        "from user input.\n\n"
        "User said:\n"
        f"{user_input}\n\n"
        "Here is a representative sample of available products:\n"
        f"{json.dumps(product_search_results, indent=2)}\n\n"
        "Please return a JSON object with two keys:\n"
        "- preferences: A list of inferred user preferences (e.g. 'low noise', 'energy efficiency')\n"
        "- constraints: A dictionary of technical constraints (e.g. motherboard compatibility, width, voltage)\n"
        "Return only valid JSON. Do not include markdown or explanations. Do not wrap the JSON in triple backticks."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )

        raw_output = response.choices[0].message.content.strip()
        print("📎 Raw output:\n", raw_output)

        # 🔧 Strip markdown code block formatting if present
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
            raw_output = re.sub(r"\s*```$", "", raw_output)

        return json.loads(raw_output)

    except Exception as e:
        print("❌ Failed to parse LLM response:", str(e))
        return {"preferences": [], "constraints": {}}

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
        "Return a JSON list where each item includes the product name and compatibility flag."
        "Return only valid JSON. Do not include markdown or explanations. Do not wrap the JSON in triple backticks."    )

    try:
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

def filter_products_with_llm(product_list: list, preferences: list) -> list:
    prompt = (
        "You are an intelligent shopping assistant.\n"
        f"The user has the following preferences:\n{json.dumps(preferences)}\n\n"
        f"Here are the products to evaluate:\n{json.dumps(product_list, indent=2)}\n\n"
        "Please filter the products based on how well they align with the user's preferences. "
        "Return a JSON list of the best-matching products (including all their attributes)."
        "Return only valid JSON. Do not include markdown or explanations. Do not wrap the JSON in triple backticks."
    )

    try:
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

        return json.loads(raw_output)

    except Exception as e:
        print("❌ Failed to filter products:", str(e))
        return []
