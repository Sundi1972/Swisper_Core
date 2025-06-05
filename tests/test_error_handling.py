"""
Test suite for error handling and resilience mechanisms.

Tests fallback modes, graceful degradation, and user-friendly error messages.
"""
import pytest
from unittest.mock import patch, MagicMock
from swisper_core.errors import (
    PipelineError, ErrorSeverity, OperationMode,
    create_user_friendly_error_message, handle_pipeline_error,
    get_degraded_operation_message
)
from swisper_core.monitoring import SystemHealthMonitor, health_monitor

from swisper_core.errors import (
    create_fallback_product_search, create_fallback_preference_ranking
)


class TestSystemHealthMonitor:
    """Test system health monitoring and operation mode management"""
    
    def test_initial_state(self):
        """Test health monitor starts in full operation mode"""
        monitor = SystemHealthMonitor()
        assert monitor.get_operation_mode() == OperationMode.FULL
        assert monitor.is_service_available("openai_api")
        assert monitor.is_service_available("web_scraping")
    
    def test_service_error_reporting(self):
        """Test service error reporting and mode degradation"""
        monitor = SystemHealthMonitor()
        
        for i in range(3):
            mode = monitor.report_service_error("openai_api", Exception("API error"))
        
        assert mode == OperationMode.DEGRADED
        assert not monitor.is_service_available("openai_api")
    
    def test_service_recovery(self):
        """Test service recovery"""
        monitor = SystemHealthMonitor()
        
        for i in range(3):
            monitor.report_service_error("openai_api", Exception("API error"))
        
        monitor.report_service_recovery("openai_api")
        
        assert monitor.is_service_available("openai_api")
        assert monitor.get_operation_mode() == OperationMode.FULL
    
    def test_multiple_service_failures(self):
        """Test operation mode with multiple service failures"""
        monitor = SystemHealthMonitor()
        
        for service in ["openai_api", "web_scraping", "product_search"]:
            for i in range(3):
                monitor.report_service_error(service, Exception(f"{service} error"))
        
        assert monitor.get_operation_mode() == OperationMode.MINIMAL


class TestErrorMessages:
    """Test user-friendly error message generation"""
    
    def test_openai_error_message(self):
        """Test OpenAI API error message"""
        error = Exception("OpenAI API rate limit exceeded")
        message = create_user_friendly_error_message(error)
        
        assert "AI analysis" in message
        assert "basic search" in message
        assert "trouble" in message
    
    def test_web_scraping_error_message(self):
        """Test web scraping error message"""
        error = Exception("Web scraping timeout")
        message = create_user_friendly_error_message(error)
        
        assert "specifications" in message
        assert "basic product information" in message
    
    def test_generic_error_message(self):
        """Test generic error message for unknown errors"""
        error = Exception("Unknown database error")
        message = create_user_friendly_error_message(error)
        
        assert "technical difficulties" in message
        assert "still here to help" in message
    
    def test_error_message_with_context(self):
        """Test error message with additional context"""
        error = Exception("Service unavailable")
        context = "Please try again later."
        message = create_user_friendly_error_message(error, context)
        
        assert context in message


class TestPipelineErrorHandling:
    """Test pipeline error handling mechanisms"""
    
    def test_handle_pipeline_error_without_fallback(self):
        """Test pipeline error handling without fallback function"""
        error = Exception("Pipeline failed")
        result = handle_pipeline_error(error, "product_search_pipeline")
        
        assert result["status"] == "error"
        assert "user_message" in result
        assert result["pipeline"] == "product_search_pipeline"
        assert not result["fallback_attempted"]
    
    def test_handle_pipeline_error_with_fallback(self):
        """Test pipeline error handling with successful fallback"""
        error = Exception("Pipeline failed")
        
        def mock_fallback():
            return {"status": "success", "data": "fallback_data"}
        
        result = handle_pipeline_error(error, "product_search_pipeline", mock_fallback)
        
        assert result["status"] == "fallback"
        assert result["data"] == "fallback_data"
        assert "user_message" in result
    
    def test_handle_pipeline_error_with_failing_fallback(self):
        """Test pipeline error handling when fallback also fails"""
        error = Exception("Pipeline failed")
        
        def failing_fallback():
            raise Exception("Fallback also failed")
        
        result = handle_pipeline_error(error, "product_search_pipeline", failing_fallback)
        
        assert result["status"] == "error"
        assert result["fallback_attempted"]


class TestFallbackMechanisms:
    """Test fallback mechanisms for core functionality"""
    
    def test_fallback_product_search(self):
        """Test fallback product search"""
        result = create_fallback_product_search("laptop", max_results=2)
        
        assert result["status"] == "fallback"
        assert len(result["items"]) == 2
        assert all("laptop" in item["name"].lower() for item in result["items"])
        assert "attributes" in result
        assert "message" in result
    
    def test_fallback_product_search_empty_query(self):
        """Test fallback product search with empty query"""
        result = create_fallback_product_search("", max_results=3)
        
        assert result["status"] == "fallback"
        assert len(result["items"]) <= 3
    
    def test_fallback_preference_ranking_empty_products(self):
        """Test fallback preference ranking with empty product list"""
        result = create_fallback_preference_ranking([])
        
        assert result["status"] == "no_products"
        assert result["ranked_products"] == []
        assert result["scores"] == []
    
    def test_fallback_preference_ranking_with_products(self):
        """Test fallback preference ranking with valid products"""
        products = [
            {"name": "Product A", "price": "100 CHF", "rating": "4.5"},
            {"name": "Product B", "price": "200 CHF", "rating": "3.0"},
            {"name": "Product C", "price": "150 CHF", "rating": "4.0"}
        ]
        
        result = create_fallback_preference_ranking(products)
        
        assert result["status"] == "fallback"
        assert len(result["ranked_products"]) <= 3
        assert len(result["scores"]) == len(result["ranked_products"])
        assert result["ranking_method"] == "simple_fallback"
        
        scores = result["scores"]
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    def test_fallback_preference_ranking_with_invalid_data(self):
        """Test fallback preference ranking with invalid product data"""
        products = [
            {"name": "Product A", "price": "invalid", "rating": "not_a_number"},
            {"name": "Product B", "price": "", "rating": ""},
            {"name": "Product C"}  # Missing fields
        ]
        
        result = create_fallback_preference_ranking(products)
        
        assert result["status"] == "fallback"
        assert len(result["ranked_products"]) == 3
        assert len(result["scores"]) == 3


class TestOperationModeMessages:
    """Test operation mode user messages"""
    
    def test_full_operation_message(self):
        """Test message for full operation mode"""
        message = get_degraded_operation_message(OperationMode.FULL)
        assert message == ""
    
    def test_degraded_operation_message(self):
        """Test message for degraded operation mode"""
        message = get_degraded_operation_message(OperationMode.DEGRADED)
        assert "advanced features" in message
        assert "temporarily unavailable" in message
    
    def test_minimal_operation_message(self):
        """Test message for minimal operation mode"""
        message = get_degraded_operation_message(OperationMode.MINIMAL)
        assert "basic mode" in message
        assert "simple product searches" in message


class TestIntegrationScenarios:
    """Test complete error handling scenarios"""
    
    def test_complete_service_failure_scenario(self):
        """Test complete service failure and recovery scenario"""
        monitor = SystemHealthMonitor()
        
        services = ["openai_api", "web_scraping", "product_search"]
        for service in services:
            for i in range(3):
                monitor.report_service_error(service, Exception(f"{service} failed"))
        
        assert monitor.get_operation_mode() == OperationMode.MINIMAL
        
        search_result = create_fallback_product_search("test product")
        assert search_result["status"] == "fallback"
        
        ranking_result = create_fallback_preference_ranking(search_result["items"])
        assert ranking_result["status"] == "fallback"
        
        for service in services:
            monitor.report_service_recovery(service)
        
        assert monitor.get_operation_mode() == OperationMode.FULL
    
    def test_pipeline_error_with_health_monitoring(self):
        """Test pipeline error handling integrates with health monitoring"""
        from swisper_core.monitoring import health_monitor
        
        health_monitor.__init__()
        
        initial_mode = health_monitor.get_operation_mode()
        assert initial_mode == OperationMode.FULL
        
        for i in range(3):
            error = Exception("OpenAI API error")
            result = handle_pipeline_error(error, "preference_match_pipeline")
        
        current_mode = health_monitor.get_operation_mode()
        assert current_mode == OperationMode.DEGRADED
        assert not health_monitor.is_service_available("openai_api")
