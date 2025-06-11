#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/home/ubuntu/repos/Swisper_Core')

from orchestrator.session_store import generate_session_title

async def test_session_title_generation():
    """Test session title generation with sample conversation"""
    
    test_messages = [
        {"role": "user", "content": "I want to buy a washing machine"},
        {"role": "assistant", "content": "I'll help you find a washing machine. What's your budget and preferred features?"},
        {"role": "user", "content": "My budget is around $800 and I need energy efficient models"},
        {"role": "assistant", "content": "Great! Let me search for energy efficient washing machines in your budget range."}
    ]
    
    print("🧪 Testing session title generation...")
    print(f"📝 Sample conversation: {len(test_messages)} messages")
    
    try:
        title = await generate_session_title(test_messages)
        print(f"✅ Generated title: '{title}'")
        
        if title and title != "Untitled Session":
            print("🎯 SUCCESS: Title generation working correctly!")
            return True
        else:
            print("❌ FAILED: Title generation returned default/empty title")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Title generation failed with exception: {e}")
        return False

async def test_weather_conversation():
    """Test title generation for weather conversation"""
    
    weather_messages = [
        {"role": "user", "content": "what is the weather like today in zurich"},
        {"role": "assistant", "content": "To provide current weather conditions in Zurich, I will perform a web search for up-to-date weather information."}
    ]
    
    print("\n🌤️ Testing weather conversation title generation...")
    
    try:
        title = await generate_session_title(weather_messages)
        print(f"✅ Generated title: '{title}'")
        
        if title and title != "Untitled Session":
            print("🎯 SUCCESS: Weather conversation title generated!")
            return True
        else:
            print("❌ FAILED: Weather conversation title generation failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Weather title generation failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Session Title Generation Test")
    print("=" * 50)
    
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        print(f"🔑 OpenAI API Key: Available (length: {len(openai_key)})")
    else:
        print("⚠️ OpenAI API Key: Not available - titles may default to 'Untitled Session'")
    
    print()
    
    loop = asyncio.get_event_loop()
    
    test1_result = loop.run_until_complete(test_session_title_generation())
    test2_result = loop.run_until_complete(test_weather_conversation())
    
    print("\n" + "=" * 50)
    if test1_result and test2_result:
        print("🎉 ALL TESTS PASSED: Session title generation is working!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED: Session title generation needs investigation")
        sys.exit(1)
