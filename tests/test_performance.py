"""
Performance tests for Swisper Core pipeline optimization.

Tests caching, timing, and performance monitoring functionality.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from contract_engine.performance_monitor import (
    PerformanceCache, PipelineTimer, PerformanceMonitor,
    create_cache_key, timed_operation, cached_operation
)
from contract_engine.haystack_components import AttributeAnalyzerComponent


class TestPerformanceCache:
    """Test performance caching functionality"""
    
    def test_cache_basic_operations(self):
        """Test basic cache set/get operations"""
        cache = PerformanceCache(default_ttl_minutes=1)
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        assert cache.size() == 1
        
        assert cache.get("nonexistent_key") is None
    
    def test_cache_expiration(self):
        """Test cache TTL expiration"""
        cache = PerformanceCache(default_ttl_minutes=0.01)  # 0.6 seconds
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        time.sleep(0.7)
        assert cache.get("test_key") is None
        assert cache.size() == 0
    
    def test_cache_clear(self):
        """Test cache clearing"""
        cache = PerformanceCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestPipelineTimer:
    """Test pipeline timing functionality"""
    
    def test_timer_context_manager(self):
        """Test timer as context manager"""
        with PipelineTimer("test_operation") as timer:
            time.sleep(0.1)
        
        assert timer.duration >= 0.1
        assert timer.duration < 0.2  # Should be close to 0.1
    
    def test_timer_records_metrics(self):
        """Test timer records performance metrics"""
        PerformanceMonitor.clear_metrics()
        
        with PipelineTimer("test_metric"):
            time.sleep(0.05)
        
        stats = PerformanceMonitor.get_stats("test_metric")
        assert stats["count"] == 1
        assert stats["avg_duration"] >= 0.05


class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def test_record_operation(self):
        """Test operation recording"""
        PerformanceMonitor.clear_metrics()
        
        PerformanceMonitor.record_operation("test_op", 1.5)
        PerformanceMonitor.record_operation("test_op", 2.0)
        
        stats = PerformanceMonitor.get_stats("test_op")
        assert stats["count"] == 2
        assert stats["total_count"] == 2
        assert stats["avg_duration"] == 1.75
        assert stats["min_duration"] == 1.5
        assert stats["max_duration"] == 2.0
    
    def test_get_all_stats(self):
        """Test getting all performance statistics"""
        PerformanceMonitor.clear_metrics()
        
        PerformanceMonitor.record_operation("op1", 1.0)
        PerformanceMonitor.record_operation("op2", 2.0)
        
        all_stats = PerformanceMonitor.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert all_stats["op1"]["avg_duration"] == 1.0
        assert all_stats["op2"]["avg_duration"] == 2.0
    
    def test_metrics_limit(self):
        """Test metrics are limited to last 100 measurements"""
        PerformanceMonitor.clear_metrics()
        
        for i in range(150):
            PerformanceMonitor.record_operation("test_limit", i * 0.01)
        
        stats = PerformanceMonitor.get_stats("test_limit")
        assert stats["count"] == 100  # Should be limited to 100
        assert stats["total_count"] == 150  # But total count should be accurate


class TestCacheKeyGeneration:
    """Test cache key generation"""
    
    def test_create_cache_key_consistency(self):
        """Test cache key generation is consistent"""
        key1 = create_cache_key("arg1", "arg2", kwarg1="value1")
        key2 = create_cache_key("arg1", "arg2", kwarg1="value1")
        assert key1 == key2
    
    def test_create_cache_key_different_args(self):
        """Test different arguments produce different keys"""
        key1 = create_cache_key("arg1", "arg2")
        key2 = create_cache_key("arg1", "arg3")
        assert key1 != key2
    
    def test_create_cache_key_kwargs_order(self):
        """Test kwargs order doesn't affect key"""
        key1 = create_cache_key(a="1", b="2")
        key2 = create_cache_key(b="2", a="1")
        assert key1 == key2


class TestTimedOperationDecorator:
    """Test timed operation decorator"""
    
    def test_timed_operation_decorator(self):
        """Test timed operation decorator works"""
        PerformanceMonitor.clear_metrics()
        
        @timed_operation("decorated_test")
        def test_function():
            time.sleep(0.05)
            return "result"
        
        result = test_function()
        assert result == "result"
        
        stats = PerformanceMonitor.get_stats("decorated_test")
        assert stats["count"] == 1
        assert stats["avg_duration"] >= 0.05


class TestCachedOperationDecorator:
    """Test cached operation decorator"""
    
    def test_cached_operation_decorator(self):
        """Test cached operation decorator works"""
        cache = PerformanceCache()
        call_count = 0
        
        @cached_operation(cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again
        
        result3 = expensive_function(6)
        assert result3 == 12
        assert call_count == 2


class TestAttributeAnalyzerPerformance:
    """Test AttributeAnalyzerComponent performance optimizations"""
    
    def test_attribute_analyzer_caching(self):
        """Test AttributeAnalyzerComponent uses caching"""
        component = AttributeAnalyzerComponent()
        
        products = [
            {"name": "Test Laptop 1", "price": "1000 CHF"},
            {"name": "Test Laptop 2", "price": "1200 CHF"}
        ]
        
        with patch('contract_engine.llm_helpers.analyze_product_differences') as mock_analyze:
            mock_analyze.return_value = "Analysis of laptop features including processor, memory, storage"
            
            result1, _ = component.run(products, "laptop")
            assert mock_analyze.call_count == 1
            assert "processor" in result1["extracted_attributes"]
            
            result2, _ = component.run(products, "laptop")
            assert mock_analyze.call_count == 1  # No additional LLM call
            assert result1["extracted_attributes"] == result2["extracted_attributes"]
    
    def test_attribute_analyzer_fallback_attributes(self):
        """Test fallback attribute extraction"""
        component = AttributeAnalyzerComponent()
        
        attrs_laptop = component._get_fallback_attributes("gaming laptop")
        assert "processor" in attrs_laptop
        assert "memory" in attrs_laptop
        
        attrs_phone = component._get_fallback_attributes("smartphone")
        assert "camera" in attrs_phone
        assert "battery" in attrs_phone
        
        attrs_default = component._get_fallback_attributes("unknown product")
        assert "brand" in attrs_default
        assert "price range" in attrs_default
    
    def test_attribute_analyzer_timing(self):
        """Test AttributeAnalyzerComponent records timing metrics"""
        PerformanceMonitor.clear_metrics()
        component = AttributeAnalyzerComponent()
        
        products = [{"name": "Test Product", "price": "100 CHF"}]
        
        with patch('contract_engine.llm_helpers.analyze_product_differences') as mock_analyze:
            mock_analyze.return_value = "Test analysis"
            
            component.run(products, "test query")
        
        stats = PerformanceMonitor.get_stats("attribute_analysis")
        assert stats["count"] == 1
        assert stats["avg_duration"] > 0
    
    def test_enhanced_attribute_extraction(self):
        """Test enhanced attribute extraction from analysis"""
        component = AttributeAnalyzerComponent()
        
        analysis = "The laptops differ in processor speed, memory capacity, storage type, and screen size"
        attrs = component._extract_attributes_from_analysis(analysis, "laptop")
        
        assert "processor" in attrs
        assert "memory" in attrs
        assert "storage" in attrs
        assert "screen" in attrs
        
        short_analysis = "Brief"
        attrs_fallback = component._extract_attributes_from_analysis(short_analysis, "laptop")
        assert "processor" in attrs_fallback  # Should use category fallback


class TestPipelinePerformanceIntegration:
    """Test performance monitoring integration with pipelines"""
    
    def test_pipeline_performance_tracking(self):
        """Test end-to-end pipeline performance tracking"""
        PerformanceMonitor.clear_metrics()
        
        with PipelineTimer("product_search"):
            time.sleep(0.02)
        
        with PipelineTimer("attribute_analysis"):
            time.sleep(0.03)
        
        with PipelineTimer("preference_matching"):
            time.sleep(0.04)
        
        all_stats = PerformanceMonitor.get_all_stats()
        assert "product_search" in all_stats
        assert "attribute_analysis" in all_stats
        assert "preference_matching" in all_stats
        
        assert all_stats["product_search"]["avg_duration"] >= 0.02
        assert all_stats["attribute_analysis"]["avg_duration"] >= 0.03
        assert all_stats["preference_matching"]["avg_duration"] >= 0.04
    
    def test_cache_performance_improvement(self):
        """Test caching provides performance improvement"""
        cache = PerformanceCache()
        
        @cached_operation(cache)
        def slow_operation(x):
            time.sleep(0.1)  # Simulate slow operation
            return x * 2
        
        start_time = time.time()
        result1 = slow_operation(5)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        result2 = slow_operation(5)
        second_call_time = time.time() - start_time
        
        assert result1 == result2 == 10
        assert second_call_time < first_call_time / 2  # Should be much faster
