#!/usr/bin/env python3
"""
Debug script to test preference extraction for various product scenarios
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contract_engine.llm_helpers import analyze_user_preferences

def test_washing_machine_scenario():
    print("🧪 Testing washing machine preference extraction...")
    user_input = "Price should be below 1600 chf it should be energy efficient below B, and it should take at least 6kg of laundry"
    
    sample_products = [
        {"name": "Bauknecht BW 719 A", "brand": "galaxus.ch", "price": 397, "rating": 4.6, "reviews": 180},
        {"name": "Samsung WW80CGC04AAEWS Waschmaschine", "brand": "MediaMarkt Suisse", "price": 499, "rating": 3.6, "reviews": 22},
        {"name": "Bosch Waschmaschine WGB256A5CH", "brand": "hornbach.ch", "price": 1280.4, "rating": 5, "reviews": 1}
    ]
    
    print(f"User input: {user_input}")
    print(f"Sample products: {len(sample_products)} items")
    print()
    
    result = analyze_user_preferences(user_input, sample_products)
    print("✅ Extraction result:")
    print(f"Preferences: {result.get('preferences', [])}")
    print(f"Constraints: {result.get('constraints', {})}")
    print()
    
    expected_constraints = {'price': 'below 1600 CHF', 'energy_efficiency': 'B or better', 'capacity': 'at least 6kg'}
    print(f"🎯 Expected constraints: {expected_constraints}")
    return result

def test_gpu_scenario():
    print("\n🧪 Testing GPU preference extraction...")
    user_input = "I need a high performance GPU under $2000 that's quiet and fits in a mid-tower case"
    
    sample_products = [
        {"name": "RTX 4090", "price": 1599, "rating": 4.8},
        {"name": "RTX 4080", "price": 1199, "rating": 4.6}
    ]
    
    result = analyze_user_preferences(user_input, sample_products)
    print("✅ GPU extraction result:")
    print(f"Preferences: {result.get('preferences', [])}")
    print(f"Constraints: {result.get('constraints', {})}")
    return result

def test_laptop_scenario():
    print("\n🧪 Testing laptop preference extraction...")
    user_input = "I want a lightweight laptop under $1500 with long battery life and 13-15 inch screen"
    
    sample_products = [
        {"name": "MacBook Air", "price": 1299, "rating": 4.7},
        {"name": "Dell XPS 13", "price": 1199, "rating": 4.5}
    ]
    
    result = analyze_user_preferences(user_input, sample_products)
    print("✅ Laptop extraction result:")
    print(f"Preferences: {result.get('preferences', [])}")
    print(f"Constraints: {result.get('constraints', {})}")
    return result

if __name__ == "__main__":
    try:
        washing_result = test_washing_machine_scenario()
        gpu_result = test_gpu_scenario()
        laptop_result = test_laptop_scenario()
        
        print("\n📊 Summary:")
        print(f"Washing machine constraints extracted: {len(washing_result.get('constraints', {}))}")
        print(f"GPU constraints extracted: {len(gpu_result.get('constraints', {}))}")
        print(f"Laptop constraints extracted: {len(laptop_result.get('constraints', {}))}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
