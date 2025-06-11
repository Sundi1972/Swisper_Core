import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from orchestrator.volatility_classifier import classify_entity_category
from orchestrator.prompt_preprocessor import has_temporal_cue
from orchestrator.intent_extractor import extract_user_intent

class TestVolatilityClassification:
    """Test volatility classification system"""
    
    def test_volatile_classification(self):
        """Test volatile keyword detection"""
        volatile_cases = [
            "Who are the current ministers of German government",
            "Latest news about German politics", 
            "Price of Bitcoin today",
            "Who is the CEO of UBS?",
            "Breaking news about ministers"
        ]
        
        for case in volatile_cases:
            result = classify_entity_category(case)
            assert result["volatility"] == "volatile", f"Failed volatile classification for: {case}"
    
    def test_static_classification(self):
        """Test static keyword detection"""
        static_cases = [
            "Who was Napoleon Bonaparte?",
            "What is the capital of Germany",
            "Explain quantum computing",
            "Who was the first chancellor of Germany",
            "What is the population of Berlin"
        ]
        
        for case in static_cases:
            result = classify_entity_category(case)
            assert result["volatility"] == "static", f"Failed static classification for: {case}"
    
    def test_semi_static_classification(self):
        """Test semi-static keyword detection"""
        semi_static_cases = [
            "What are the specs of iPhone 15?",
            "Features of the new model",
            "Company specifications"
        ]
        
        for case in semi_static_cases:
            result = classify_entity_category(case)
            assert result["volatility"] == "semi_static", f"Failed semi-static classification for: {case}"
    
    def test_temporal_cue_detection(self):
        """Test temporal cue detection"""
        temporal_cases = [
            "Who are the ministers today",
            "Current situation in Germany",
            "Latest developments in 2025"
        ]
        
        non_temporal_cases = [
            "Who is Angela Merkel",
            "History of Germany",
            "Explain the concept"
        ]
        
        for case in temporal_cases:
            assert has_temporal_cue(case), f"Failed to detect temporal cue in: {case}"
            
        for case in non_temporal_cases:
            assert not has_temporal_cue(case), f"False positive temporal cue in: {case}"

class TestEnhancedIntentExtraction:
    """Test enhanced intent extraction with volatility context"""
    
    def test_websearch_vs_chat_distinction(self):
        """Test the core issue: websearch vs chat routing"""
        websearch_cases = [
            "Who are the ministers of German government",
            "Who are the current ministers of German government", 
            "What are the latest news about German politics",
            "Current cabinet members of Germany",
            "Recent developments in German politics"
        ]
        
        chat_cases = [
            "Who is Angela Merkel",
            "What is the capital of Germany",
            "Who was the first chancellor of Germany",
            "What is the population of Berlin",
            "Explain German political system"
        ]
        
        for message in websearch_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "websearch", f"Failed websearch routing for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence for websearch: {message}"
            
        for message in chat_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "chat", f"Failed chat routing for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence for chat: {message}"
